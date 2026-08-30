"""調教師の実績による機械的判断ルール。

キャリア判定（開業年数で評価可否を先に決める）:
  開業 5年未満                           → 判定不可  サンプル不足
  開業 5年 かつ 重賞勝利なし（DB 2024+）  → 判定不可  実績不十分
  上記以外                               → 以下のグレード判定へ

グレード基準:
  ◎ : 直近3年でリーディング上位10位入りあり かつ 5年平均勝利数 ≥ 37
  ◯ : 5年平均勝利数 ≥ 15 かつ 重賞勝利あり（DB 2024年以降分）
  ▲ : 5年平均勝利数 ≥ 8（◯の条件未達）
  × : 重賞勝利なし かつ 5年平均勝利数 < 8
  △ : 上記以外（重賞実績あるが平均勝利数が低い稀なケース）

閾値は config.yaml の mechanical_judgment.trainer で管理。
重賞勝利数は RACE DataSpec（2024年以降のデータ）からの集計のため過去分は不足する。
"""
from __future__ import annotations
from datetime import datetime
from app.scoring.result import RuleResult
from app.scoring.rules.base_rule import BaseRule
from app.scoring.context import ScoringContext

_GRADE_SCORES = {"◎": 100.0, "◯": 75.0, "▲": 50.0, "△": 25.0, "×": 0.0, "判定不可": 50.0}


class MJTrainerRule(BaseRule):
    name = "mj_trainer"
    label = "調教師（機械的判断）"
    description = "リーディング順位・平均勝利数・重賞勝利数で◎/◯/▲/△/×判定。"

    def score(self, horse: dict, context: ScoringContext) -> RuleResult:
        cfg = context.config.get("mechanical_judgment", {}).get("trainer", {})
        raw_name = str(horse.get("trainer_name_matched") or horse.get("trainer_name", ""))
        # DB は「姓　名」（全角スペース区切り）、CSV は「姓名」の場合があるため両側を正規化して比較
        trainer_key = raw_name.replace("　", "").replace(" ", "")

        df = context.trainer_mj_stats
        df_norm = df["trainer_name"].str.replace("　", "", regex=False).str.replace(" ", "", regex=False)
        row = df[df_norm == trainer_key]
        trainer_name = raw_name

        if row.empty:
            return RuleResult(
                score=50.0,
                details={"grade": "判定不可", "note": "DBにデータなし"},
                data_available=False,
            )

        r = row.iloc[0]
        license_date = str(r.get("license_date", "") or "")
        career_years = _career_years(license_date)
        min_years = cfg.get("min_career_years", 5)

        avg_wins       = float(r.get("avg_wins", 0) or 0)
        graded_wins    = int(r.get("graded_wins", 0) or 0)

        # 開業年数によるキャリア判定:
        # - 5年未満: 実績判定に必要なデータが揃っていない（重賞実績があっても同様）
        # - 5年のみ: 重賞実績なしなら判定不可（実績があれば評価可能）
        strict_min = 5
        if career_years is not None:
            if career_years < strict_min:
                return RuleResult(
                    score=_GRADE_SCORES["判定不可"],
                    data_available=True,
                    details={
                        "grade": "判定不可",
                        "note": f"開業後{career_years}年（{strict_min}年未満）",
                        "career_years": career_years,
                    },
                )
            elif career_years < min_years and graded_wins == 0:
                return RuleResult(
                    score=_GRADE_SCORES["判定不可"],
                    data_available=True,
                    details={
                        "grade": "判定不可",
                        "note": f"開業後{career_years}年・重賞勝利なし（評価不足）",
                        "career_years": career_years,
                    },
                )
        top10_3y       = int(r.get("top10_count_3y", 0) or 0)

        top10_for_good   = cfg.get("top10_for_good", 1)    # top10回数がN以上で◎候補
        avg_wins_good    = cfg.get("avg_wins_good", 37)    # ◎の平均勝利数下限
        avg_wins_ok      = cfg.get("avg_wins_ok", 15)      # ◯の平均勝利数下限
        avg_wins_try     = cfg.get("avg_wins_try", 8)      # ▲の平均勝利数下限
        gw_for_ok        = cfg.get("graded_wins_for_ok", 1)

        # ◎: 直近3年でリーディングtop10 かつ高い平均勝利数
        if top10_3y >= top10_for_good and avg_wins >= avg_wins_good:
            grade = "◎"
            note = f"直近3年top10: {top10_3y}回、5年平均{avg_wins:.1f}勝"
        # ◯: 平均勝利数が一定以上 かつ重賞勝ちあり（DBカバレッジ限定だが必須）
        elif avg_wins >= avg_wins_ok and graded_wins >= gw_for_ok:
            grade = "◯"
            note = f"5年平均{avg_wins:.1f}勝・重賞{graded_wins}勝"
        # ▲: 平均勝利数はそこそこあるが◯には届かない
        elif avg_wins >= avg_wins_try:
            grade = "▲"
            note = f"5年平均{avg_wins:.1f}勝・重賞{graded_wins}勝"
        # ×: 重賞勝ちなしかつ勝利数も低い
        elif graded_wins == 0 and avg_wins < avg_wins_try:
            grade = "×"
            note = f"5年平均{avg_wins:.1f}勝・重賞勝利なし"
        else:
            grade = "△"
            note = f"5年平均{avg_wins:.1f}勝・重賞{graded_wins}勝"

        return RuleResult(
            score=_GRADE_SCORES[grade],
            data_available=True,
            details={
                "grade":        grade,
                "note":         note,
                "top10_3y":     top10_3y,
                "avg_wins":     round(avg_wins, 1),
                "graded_wins":  graded_wins,
                "career_years": career_years,
            },
        )


def _career_years(license_date: str) -> int | None:
    """'YYYYMMDD' 形式から現在までの年数を計算。"""
    s = license_date.replace("-", "").replace("/", "").strip()
    if len(s) >= 4 and s[:4].isdigit():
        try:
            year = int(s[:4])
            return datetime.now().year - year
        except ValueError:
            pass
    return None

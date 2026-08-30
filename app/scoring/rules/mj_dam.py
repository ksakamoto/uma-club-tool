"""母馬年齢 × 産駒の競走成績による機械的判断ルール。

判定ツリー（dam_age = 馬出生年 − 母出生年）:
  < 6歳                    → ×  産駒が少なすぎて実績評価が困難
  6-9歳                    → ◎  繁殖黄金期・産駒成績によらず無条件OK
  10歳 + 重賞2着以上産駒あり → ◎
  10歳 + オープン勝ち産駒あり → ◯
  10歳 それ以外             → ▲
  11-14歳 + 重賞勝ち産駒あり → ◎
  11-14歳 + 重賞2着以上     → ▲  ※勝ちなしは年齢リスクを相殺できない
  11-14歳 + オープン勝ち    → ▲
  11-14歳 それ以外          → ×
  15歳以上 + 重賞勝ち産駒あり → ★  高齢だが実績あり（見送り推奨）
  15歳以上 それ以外         → ×

閾値は config.yaml の mechanical_judgment.dam で管理。
"""
from __future__ import annotations
from app.scoring.result import RuleResult
from app.scoring.rules.base_rule import BaseRule
from app.scoring.context import ScoringContext

_GRADE_SCORES = {"◎": 100.0, "◯": 75.0, "▲": 50.0, "△": 25.0, "×": 0.0}


class MJDamRule(BaseRule):
    name = "mj_dam"
    label = "母馬（機械的判断）"
    description = "母馬の出生時年齢と産駒の重賞成績の組み合わせで◎/◯/▲/△/×判定。"

    def score(self, horse: dict, context: ScoringContext) -> RuleResult:
        cfg = context.config.get("mechanical_judgment", {}).get("dam", {})

        dam_name = str(horse.get("dam_name_matched") or horse.get("dam_name", ""))
        birth_date = str(horse.get("birth_date", ""))
        horse_birth_year = _extract_year(birth_date)

        # birth_date が月/日のみ（例: '4/30'）の場合は birth_year / year で補完
        if horse_birth_year is None:
            fallback = horse.get("birth_year") or horse.get("year")
            if fallback is not None:
                try:
                    horse_birth_year = int(fallback)
                except (TypeError, ValueError):
                    pass

        dam_birth_year = context.get_dam_birth_year(dam_name)

        if dam_birth_year is None or horse_birth_year is None:
            return RuleResult(
                score=50.0,
                details={"grade": "判定不可", "note": "母馬の生年またはこの馬の生年が不明"},
                data_available=False,
            )

        dam_age = horse_birth_year - dam_birth_year
        grade_info = context.get_dam_offspring_grade_info(dam_name)

        age_unc_min     = cfg.get("age_unconditional_min", 6)
        age_unc_max     = cfg.get("age_unconditional_max", 9)
        age_placed_max  = cfg.get("age_graded_placed_max", 10)
        age_win_max     = cfg.get("age_graded_win_max", 14)
        age_ng_min      = cfg.get("age_ng_min", 15)

        has_graded_win     = grade_info["has_graded_win"]
        has_graded_placed  = grade_info["has_graded_placed"]
        has_open_win       = grade_info["has_open_win"]
        sibling_count      = grade_info["sibling_count"]

        if dam_age >= age_ng_min:
            if has_graded_win:
                grade = "★"
                note = f"母{dam_age}歳（{age_ng_min}歳以上）だが産駒に重賞勝ちあり"
            else:
                grade = "×"
                note = f"母{dam_age}歳（{age_ng_min}歳以上）"
            return RuleResult(
                score=0.0,
                data_available=True,
                details={"grade": grade, "dam_age": dam_age, "note": note,
                         "sibling_count": sibling_count, **grade_info},
            )

        if dam_age < age_unc_min:
            grade = "×"
            note = f"母{dam_age}歳（{age_unc_min}歳未満は産駒実績なし）"
        elif dam_age <= age_unc_max:
            grade = "◎"
            note = f"母{dam_age}歳（{age_unc_min}〜{age_unc_max}歳は無条件OK）"
        elif dam_age == age_placed_max:
            if has_graded_placed:
                grade = "◎"
                note = f"母{dam_age}歳・産駒に重賞2着以上あり"
            elif has_open_win:
                grade = "◯"
                note = f"母{dam_age}歳・産駒にオープン勝ちあり（重賞2着以上なし）"
            else:
                grade = "▲"
                note = f"母{dam_age}歳だが産駒に重賞2着以上なし"
        elif age_placed_max < dam_age <= age_win_max:
            if has_graded_win:
                grade = "◎"
                note = f"母{dam_age}歳・産駒に重賞勝ちあり"
            elif has_graded_placed:
                grade = "▲"
                note = f"母{dam_age}歳・産駒に重賞2着以上あるが勝ちなし"
            elif has_open_win:
                grade = "▲"
                note = f"母{dam_age}歳・産駒にオープン勝ちあり（重賞なし）"
            else:
                grade = "×"
                note = f"母{dam_age}歳だが産駒に重賞勝ちなし"
        else:
            grade = "△"
            note = f"母{dam_age}歳（想定外の年齢範囲）"

        score = _GRADE_SCORES.get(grade, 25.0)
        return RuleResult(
            score=score,
            data_available=True,
            details={"grade": grade, "dam_age": dam_age, "note": note,
                     "sibling_count": sibling_count, **grade_info},
        )


def _extract_year(birth_date: str) -> int | None:
    """'2026-03-15' / '2026/03/15' / '20260315' / '2026' から年を抽出。"""
    s = birth_date.replace("-", "").replace("/", "").strip()
    if len(s) >= 4 and s[:4].isdigit():
        return int(s[:4])
    return None

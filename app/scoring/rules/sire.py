from __future__ import annotations
from app.scoring.result import RuleResult
from app.scoring.rules.base_rule import BaseRule
from app.scoring.context import ScoringContext


class SireRule(BaseRule):
    name = "sire"
    label = "種牡馬スコア"
    description = "産駒の勝率・連対率・平均獲得賞金（horsesテーブルから集計）をスコア化。"

    def score(self, horse: dict, context: ScoringContext) -> RuleResult:
        sire_name = horse.get("sire_name_matched") or horse.get("sire_name", "")
        df = context.sire_stats
        row = df[df["sire_name"] == sire_name]

        if row.empty:
            return RuleResult(score=50.0, details={"note": "DBにデータなし"}, data_available=False)

        r = row.iloc[0]
        win_score   = context.normalize(df["win_rate"],   r["win_rate"])
        top3_score  = context.normalize(df["top3_rate"],  r["top3_rate"])
        prize_score = context.normalize(df["avg_prize"],  r["avg_prize"])

        score = win_score * 0.40 + top3_score * 0.30 + prize_score * 0.30

        return RuleResult(
            score=score,
            data_available=True,
            details={
                "win_rate_pct":     round(float(r["win_rate"])  * 100, 1),
                "top3_rate_pct":    round(float(r["top3_rate"]) * 100, 1),
                "avg_prize_man":    round(float(r["avg_prize"]), 0),
                "offspring_count":  int(r.get("offspring_count", 0) or 0),
                "win_score":        round(win_score,   1),
                "top3_score":       round(top3_score,  1),
                "prize_score":      round(prize_score, 1),
            },
        )

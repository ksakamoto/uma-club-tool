from __future__ import annotations
from app.scoring.result import RuleResult
from app.scoring.rules.base_rule import BaseRule
from app.scoring.context import ScoringContext


class FarmRule(BaseRule):
    name = "farm"
    label = "牧場スコア"
    description = "直近N年の勝率・連対率・1レース平均賞金で牧場の育成力をスコア化。"

    def score(self, horse: dict, context: ScoringContext) -> RuleResult:
        farm_name = horse.get("farm_name_matched") or horse.get("farm_name", "")
        df = context.farm_stats
        row = df[df["farm_name"] == farm_name]

        if row.empty:
            return RuleResult(score=50.0, details={"note": "DBにデータなし"}, data_available=False)

        r = row.iloc[0]
        win_score   = context.normalize(df["win_rate"],  r["win_rate"])
        top3_score  = context.normalize(df["top3_rate"], r["top3_rate"])
        prize_score = context.normalize(df["avg_prize"], r["avg_prize"])

        score = win_score * 0.40 + top3_score * 0.35 + prize_score * 0.25

        return RuleResult(
            score=score,
            data_available=True,
            details={
                "win_rate_pct":  round(float(r["win_rate"])  * 100, 1),
                "top3_rate_pct": round(float(r["top3_rate"]) * 100, 1),
                "avg_prize_man": round(float(r["avg_prize"]), 0),
                "runs_total":    int(r.get("runs_total", 0) or 0),
                "win_score":     round(win_score,   1),
                "top3_score":    round(top3_score,  1),
                "prize_score":   round(prize_score, 1),
            },
        )

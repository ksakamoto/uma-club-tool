from __future__ import annotations
from app.scoring.result import RuleResult
from app.scoring.rules.base_rule import BaseRule
from app.scoring.context import ScoringContext


class SiblingsRule(BaseRule):
    name = "siblings"
    label = "兄弟馬スコア"
    description = "同じ母馬の兄弟馬の最高獲得賞金・平均勝率からポテンシャルを推定。"

    def score(self, horse: dict, context: ScoringContext) -> RuleResult:
        dam_name = horse.get("dam_name_matched") or horse.get("dam_name", "")
        siblings = context.get_siblings(dam_name)

        if siblings.empty:
            return RuleResult(
                score=50.0,
                details={"note": "兄弟馬データなし（初仔等）"},
                data_available=False,
                confidence=0.3,
            )

        runners = len(siblings)
        max_prize    = float(siblings["total_prize"].max())
        avg_win_rate = float(siblings["win_rate"].fillna(0.0).mean())

        # 10,000万（1億）で満点100
        prize_score = min(100.0, max_prize / 100.0)
        # 20% 勝率で満点100
        win_score = min(100.0, avg_win_rate * 500.0)

        confidence = min(1.0, runners / 3)
        score = prize_score * 0.65 + win_score * 0.35

        return RuleResult(
            score=score,
            data_available=True,
            confidence=confidence,
            details={
                "siblings_count":   runners,
                "max_prize_man":    round(max_prize, 0),
                "avg_win_rate_pct": round(avg_win_rate * 100, 1),
                "prize_score":      round(prize_score, 1),
                "win_score":        round(win_score, 1),
            },
        )

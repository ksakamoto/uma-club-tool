from __future__ import annotations
import pandas as pd

from app.scoring.context import ScoringContext
from app.scoring.registry import discover_rules
from app.scoring.result import RuleResult, ScoringResult


class ScoringEngine:
    def __init__(
        self,
        weights: dict[str, float],
        context: ScoringContext,
        enabled_rules: list[str] | None = None,
    ):
        all_rule_classes = discover_rules()
        self.rules = [
            cls()
            for cls in all_rule_classes
            if enabled_rules is None or cls.name in enabled_rules
        ]
        self.weights = weights
        self.context = context

    @property
    def available_rules(self) -> list[dict]:
        """UIでルール一覧を表示するためのメタデータを返す。"""
        all_rules = discover_rules()
        return [{"name": cls.name, "label": cls.label, "description": cls.description} for cls in all_rules]

    def score_horse(self, horse: dict) -> ScoringResult:
        breakdown: dict[str, RuleResult] = {}
        for rule in self.rules:
            try:
                breakdown[rule.name] = rule.score(horse, self.context)
            except Exception:
                breakdown[rule.name] = RuleResult(score=0.0, details={}, data_available=False)

        active_weights = {name: w for name, w in self.weights.items() if name in breakdown}
        weight_sum = sum(active_weights.values())

        if weight_sum > 0:
            total = sum(
                breakdown[name].score * w
                for name, w in active_weights.items()
            ) / weight_sum
        else:
            total = 0.0

        return ScoringResult(horse=horse, total_score=total, breakdown=breakdown)

    def score_all(self, horses: list[dict]) -> pd.DataFrame:
        results = [self.score_horse(h) for h in horses]
        rows = [r.to_row() for r in results]
        df = pd.DataFrame(rows)
        return df.sort_values("total_score", ascending=False).reset_index(drop=True)

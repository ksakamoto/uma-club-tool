from __future__ import annotations
import math
from app.scoring.rules.physical import _range_score, _RANGES
from app.scoring.result import RuleResult
from app.scoring.rules.base_rule import BaseRule
from app.scoring.context import ScoringContext


class PhysicalLatestRule(BaseRule):
    name = "physical_latest"
    label = "直近馬体重スコア"
    description = "直近馬体重を使った馬体スコア（発表後に有効化）"

    def score(self, horse: dict, context: ScoringContext) -> RuleResult:
        weight = horse.get("weight_kg_latest")
        if weight is None:
            return RuleResult(score=50.0, details={"note": "直近馬体重データなし"}, data_available=False)
        try:
            weight = float(weight)
        except (ValueError, TypeError):
            return RuleResult(score=50.0, details={"note": "直近馬体重データなし"}, data_available=False)
        if math.isnan(weight):
            return RuleResult(score=50.0, details={"note": "直近馬体重データなし"}, data_available=False)

        # 体重のみ直近値、他（体高・胸囲・管囲）は基準値を流用
        scores: dict[str, float] = {
            "weight_kg": _range_score(weight, _RANGES["weight_kg"])
        }
        for field in ("height_cm", "chest_cm", "cannon_cm"):
            val = horse.get(field)
            if val is not None:
                try:
                    scores[field] = _range_score(float(val), _RANGES[field])
                except (ValueError, TypeError):
                    pass

        final = sum(scores.values()) / len(scores)
        return RuleResult(
            score=final,
            data_available=True,
            details={"weight_kg_latest": weight} | {f: round(v, 1) for f, v in scores.items()},
        )

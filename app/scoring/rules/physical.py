from __future__ import annotations
from app.scoring.result import RuleResult
from app.scoring.rules.base_rule import BaseRule
from app.scoring.context import ScoringContext

# 理想レンジ（min, ideal_center, max）。中心に近いほど高得点。
_RANGES = {
    "weight_kg": (440, 490, 545),
    "height_cm": (158, 163, 170),
    "chest_cm":  (180, 188, 200),
    "cannon_cm": (19.0, 21.0, 23.0),
}


def _range_score(value: float, rng: tuple[float, float, float]) -> float:
    lo, center, hi = rng
    if value < lo or value > hi:
        distance = min(abs(value - lo), abs(value - hi))
        return max(0.0, 50.0 - distance * 5)
    if value <= center:
        return 50.0 + (value - lo) / (center - lo) * 50
    else:
        return 50.0 + (hi - value) / (hi - center) * 50


class PhysicalRule(BaseRule):
    name = "physical"
    label = "馬体スコア"
    description = "体重・体高・胸囲・管囲が理想レンジからの乖離でスコア化（CSVの入力値を使用）。"

    def score(self, horse: dict, context: ScoringContext) -> RuleResult:
        scores = {}
        available_fields = []

        for field, rng in _RANGES.items():
            val = horse.get(field)
            if val is None:
                continue
            try:
                v = float(val)
                scores[field] = _range_score(v, rng)
                available_fields.append(field)
            except (ValueError, TypeError):
                pass

        if not scores:
            return RuleResult(score=50.0, details={"note": "馬体データなし"}, data_available=False)

        final_score = sum(scores.values()) / len(scores)

        return RuleResult(
            score=final_score,
            data_available=True,
            details={f: round(scores[f], 1) for f in available_fields}
            | {"available_fields": available_fields},
        )

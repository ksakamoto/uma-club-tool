from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class RuleResult:
    score: float            # 0〜100点
    details: dict           # スコア内訳（UI表示用）
    data_available: bool    # DBにマッチするデータがあったか
    confidence: float = 1.0 # サンプル数等による信頼度（0〜1）


@dataclass
class ScoringResult:
    horse: dict
    total_score: float
    breakdown: dict[str, RuleResult]   # rule.name → RuleResult

    @property
    def horse_name(self) -> str:
        return self.horse.get("horse_name", "")

    # horse dict からそのまま scored_df に引き継ぐ列
    _PASSTHROUGH_FIELDS = (
        "horse_name", "recruit_no", "sire_name", "dam_name", "broodmare_sire_name",
        "trainer_name", "farm_name", "price_total", "sex", "stable",
        "birth_date",
        "weight_kg", "weight_kg_latest", "height_cm", "chest_cm", "cannon_cm",
    )

    def to_row(self) -> dict:
        row: dict = {"total_score": round(self.total_score, 1)}
        for field in self._PASSTHROUGH_FIELDS:
            row[field] = self.horse.get(field)
        for rule_name, result in self.breakdown.items():
            row[f"score_{rule_name}"] = round(result.score, 1)
            row[f"avail_{rule_name}"] = result.data_available
            if "grade" in result.details:
                row[f"grade_{rule_name}"] = result.details["grade"]
        return row

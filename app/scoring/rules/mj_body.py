"""馬体（体重・管囲・体高）の機械的判断ルール。

グレード基準（体重・管囲・体高の3指標のうち範囲外になった数で決定）:
  ◎ : 3指標すべて基準範囲内
  ◯ : 1指標のみ範囲外
  ▲ : 2指標が範囲外
  × : 3指標すべて範囲外

閾値は config.yaml の mechanical_judgment.body.[male|female] で管理。
"""
from __future__ import annotations
import math
from app.scoring.result import RuleResult
from app.scoring.rules.base_rule import BaseRule
from app.scoring.context import ScoringContext

_GRADE_SCORES = {"◎": 100.0, "◯": 75.0, "▲": 50.0, "×": 0.0}


class MJBodyRule(BaseRule):
    name = "mj_body"
    label = "馬体（機械的判断）"
    description = "体重・管囲・体高を機械的判断条件の閾値で◎/◯/▲/×判定。"

    def score(self, horse: dict, context: ScoringContext) -> RuleResult:
        cfg = context.config.get("mechanical_judgment", {}).get("body", {})
        sex = str(horse.get("sex", ""))
        sex_key = "male" if "牡" in sex or "セン" in sex else "female"
        t = cfg.get(sex_key, {})

        checks: list[tuple[str, bool]] = []

        weight = _float(horse.get("weight_kg"))
        if weight is not None:
            ok = t.get("weight_min", 0) <= weight <= t.get("weight_max", 9999)
            checks.append((f"体重 {weight:.0f}kg（基準: {t.get('weight_min')}-{t.get('weight_max')}）", ok))

        cannon = _float(horse.get("cannon_cm"))
        if cannon is not None:
            ok = t.get("cannon_min", 0) <= cannon <= t.get("cannon_max", 99)
            checks.append((f"管囲 {cannon:.1f}cm（基準: {t.get('cannon_min')}-{t.get('cannon_max')}）", ok))

        height = _float(horse.get("height_cm"))
        if height is not None:
            ok = t.get("height_min", 0) <= height <= t.get("height_max", 9999)
            checks.append((f"体高 {height:.1f}cm（基準: {t.get('height_min')}-{t.get('height_max')}）", ok))

        if not checks:
            return RuleResult(
                score=50.0,
                details={"grade": "判定不可", "note": "測尺データなし"},
                data_available=False,
            )

        fail_count = sum(1 for _, ok in checks if not ok)
        if fail_count == 0:
            grade = "◎"
        elif fail_count == 1:
            grade = "◯"
        elif fail_count == 2:
            grade = "▲"
        else:
            grade = "×"

        return RuleResult(
            score=_GRADE_SCORES[grade],
            data_available=True,
            details={
                "grade": grade,
                "checks": [{"label": label, "ok": ok} for label, ok in checks],
            },
        )


def _float(v) -> float | None:
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None

from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
import pandas as pd
import yaml

from app.core.db_reader import DBReader

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


class ScoringContext:
    """DBデータの遅延ロードキャッシュ＋正規化ヘルパー。"""

    def __init__(self, db: DBReader, years: int = 3):
        self.db = db
        self.years = years
        self._cache: dict[str, Any] = {}
        self._config: dict | None = None

    def _lazy(self, key: str, loader: Callable) -> Any:
        if key not in self._cache:
            self._cache[key] = loader()
        return self._cache[key]

    @property
    def config(self) -> dict:
        if self._config is None:
            if _CONFIG_PATH.exists():
                self._config = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
            else:
                self._config = {}
        return self._config

    @property
    def trainer_mj_stats(self) -> pd.DataFrame:
        mj_years = self.config.get("mechanical_judgment", {}).get("trainer", {}).get("recent_years", 5)
        return self._lazy("trainer_mj_stats", lambda: self.db.get_trainer_mj_stats(years=mj_years))

    def get_dam_offspring_grade_info(self, dam_name: str) -> dict:
        return self._lazy(
            f"dam_grades::{dam_name}",
            lambda: self.db.get_dam_offspring_grade_info(dam_name),
        )

    @property
    def sire_stats(self) -> pd.DataFrame:
        return self._lazy("sire_stats", lambda: self.db.get_sire_stats_avg(self.years))

    @property
    def trainer_stats(self) -> pd.DataFrame:
        return self._lazy("trainer_stats", lambda: self.db.get_trainer_stats_avg(self.years))

    @property
    def farm_stats(self) -> pd.DataFrame:
        return self._lazy("farm_stats", lambda: self.db.get_farm_stats_avg(self.years))

    def get_siblings(self, dam_name: str) -> pd.DataFrame:
        return self._lazy(f"siblings::{dam_name}", lambda: self.db.get_siblings(dam_name))

    def get_dam_birth_year(self, dam_name: str) -> int | None:
        return self._lazy(f"dam_birth::{dam_name}", lambda: self.db.get_dam_birth_year(dam_name))

    def normalize(self, series: pd.Series, value: float) -> float:
        """全レコードを母集団にしたmin-max正規化（0〜100）。"""
        if series.empty:
            return 50.0
        mn, mx = series.min(), series.max()
        if mx <= mn:
            return 50.0
        return float(max(0.0, min(100.0, (value - mn) / (mx - mn) * 100)))

    def invalidate(self) -> None:
        """キャッシュをクリア（DB更新後などに呼ぶ）。"""
        self._cache.clear()

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.scoring.result import RuleResult

if TYPE_CHECKING:
    from app.scoring.context import ScoringContext


class BaseRule(ABC):
    name: str        # ルール識別子（weights.yaml のキーと一致させる）
    label: str       # UI表示名
    description: str # 説明文

    @abstractmethod
    def score(self, horse: dict, context: "ScoringContext") -> RuleResult:
        """
        Parameters
        ----------
        horse : dict
            募集馬1頭分のデータ（CSVから）
        context : ScoringContext
            DBデータのキャッシュ・正規化ヘルパー

        Returns
        -------
        RuleResult
        """

"""Strategy interface."""

from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


class BaseStrategy(ABC):
    name = "base"
    max_score = 0.0

    @abstractmethod
    def calculate_score(self, stock: dict[str, Any], history: pd.DataFrame, context: dict[str, Any]) -> tuple[float, list[str]]:
        """Return a bounded score and evidence notes."""


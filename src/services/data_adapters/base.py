from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd

class BaseDataAdapter(ABC):
    """Base class for all data adapters"""

    @abstractmethod
    def get_historical_data(self, symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        pass

    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
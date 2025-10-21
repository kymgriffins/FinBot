from dataclasses import dataclass
from datetime import datetime


@dataclass
class Summary:
    symbol: str
    symbol_name: str
    symbol_emoji: str
    records: int
    week_range: str
    current_price: float
    week_high: float
    week_low: float
    week_change: float
    total_volume: int
    data_period: str



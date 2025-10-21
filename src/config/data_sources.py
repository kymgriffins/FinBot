import os
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class DataSourceConfig:
    name: str
    enabled: bool
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    priority: int = 1

class DataSourceManager:
    def __init__(self):
        self.sources = {
            'yfinance': DataSourceConfig(
                name='Yahoo Finance',
                enabled=True,
                priority=1
            ),
            'polygon': DataSourceConfig(
                name='Polygon.io',
                enabled=bool(os.getenv('POLYGON_API_KEY')),
                api_key=os.getenv('POLYGON_API_KEY'),
                base_url='https://api.polygon.io',
                priority=2
            ),
            'alphavantage': DataSourceConfig(
                name='Alpha Vantage',
                enabled=bool(os.getenv('ALPHAVANTAGE_API_KEY')),
                api_key=os.getenv('ALPHAVANTAGE_API_KEY'),
                base_url='https://www.alphavantage.co',
                priority=3
            ),
            'mt5': DataSourceConfig(
                name='MetaTrader 5',
                enabled=bool(os.getenv('MT5_ENABLED')),
                priority=4
            ),# Add FMP to your data sources
'fmp': DataSourceConfig(
    name='Financial Modeling Prep',
    enabled=bool(os.getenv('FMP_API_KEY')),
    api_key=os.getenv('FMP_API_KEY'),
    base_url='https://financialmodelingprep.com/api/v3',
    priority=2  # Higher priority than yfinance
)
        }

    def get_active_sources(self):
        """Get enabled data sources sorted by priority"""
        return sorted(
            [source for source in self.sources.values() if source.enabled],
            key=lambda x: x.priority
        )

    def toggle_source(self, source_name: str, enabled: bool):
        """Toggle data source on/off"""
        if source_name in self.sources:
            self.sources[source_name].enabled = enabled

    def get_source(self, source_name: str) -> Optional[DataSourceConfig]:
        """Get specific source configuration"""
        return self.sources.get(source_name)

# Global instance
data_source_manager = DataSourceManager()
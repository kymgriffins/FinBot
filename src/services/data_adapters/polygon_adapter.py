import requests
import pandas as pd
from typing import Dict, List, Optional
from .base import BaseDataAdapter
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PolygonAdapter(BaseDataAdapter):
    def __init__(self):
        self._name = "Polygon.io"
        self.api_key = os.getenv('POLYGON_API_KEY')
        self.base_url = "https://api.polygon.io"

    @property
    def name(self) -> str:
        return self._name

    def get_historical_data(self, symbol: str, period: str = '1wk', interval: str = '1m') -> Optional[pd.DataFrame]:
        if not self.api_key:
            return None

        try:
            # Convert period to days
            period_days = {
                '1d': 1, '1wk': 7, '1mo': 30
            }.get(period, 7)

            # Polygon uses different interval format
            interval_map = {
                '1m': 'minute', '5m': '5minute', '15m': '15minute',
                '1h': 'hour', '1d': 'day'
            }

            polygon_interval = interval_map.get(interval, 'minute')

            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)

            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/{polygon_interval}/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"

            response = requests.get(url, params={
                'apiKey': self.api_key,
                'adjusted': 'true',
                'sort': 'asc'
            })

            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    df = pd.DataFrame(data['results'])
                    df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
                    df = df.rename(columns={
                        'o': 'open', 'h': 'high', 'l': 'low',
                        'c': 'close', 'v': 'volume'
                    })
                    df['data_source'] = self.name
                    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'data_source']]

            return None

        except Exception as e:
            logger.error(f"Polygon error for {symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        if not self.api_key:
            return None

        try:
            url = f"{self.base_url}/v2/last/trade/{symbol}"
            response = requests.get(url, params={'apiKey': self.api_key})

            if response.status_code == 200:
                data = response.json()
                return data['results']['p']
            return None
        except Exception as e:
            logger.error(f"Polygon current price error for {symbol}: {e}")
            return None

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        if not self.api_key:
            return None

        try:
            url = f"{self.base_url}/v3/reference/tickers/{symbol}"
            response = requests.get(url, params={'apiKey': self.api_key})

            if response.status_code == 200:
                data = response.json()
                return {
                    'name': data['results'].get('name', symbol),
                    'currency': data['results'].get('currency_name', 'USD'),
                    'exchange': data['results'].get('exchange', 'N/A'),
                    'sector': data['results'].get('sic_description', 'N/A')
                }
            return None
        except Exception as e:
            logger.error(f"Polygon symbol info error for {symbol}: {e}")
            return None

    def is_available(self) -> bool:
        if not self.api_key:
            return False

        try:
            test_price = self.get_current_price('AAPL')
            return test_price is not None
        except:
            return False
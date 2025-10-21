import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional
from .base import BaseDataAdapter
import logging

logger = logging.getLogger(__name__)

class YFinanceAdapter(BaseDataAdapter):
    def __init__(self):
        self._name = "Yahoo Finance"

    @property
    def name(self) -> str:
        return self._name

    def get_historical_data(self, symbol: str, period: str = '1wk', interval: str = '1m') -> Optional[pd.DataFrame]:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)

            if data.empty:
                return None

            data = data.reset_index()
            data = data.rename(columns={'Datetime': 'timestamp'})
            data['data_source'] = self.name

            return data
        except Exception as e:
            logger.error(f"YFinance error for {symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            return data['Close'].iloc[-1] if not data.empty else None
        except Exception as e:
            logger.error(f"YFinance current price error for {symbol}: {e}")
            return None

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                'name': info.get('longName', symbol),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', 'N/A'),
                'sector': info.get('sector', 'N/A')
            }
        except Exception as e:
            logger.error(f"YFinance symbol info error for {symbol}: {e}")
            return None

    def is_available(self) -> bool:
        try:
            # Test with a known symbol
            test_data = self.get_current_price('AAPL')
            return test_data is not None
        except:
            return False
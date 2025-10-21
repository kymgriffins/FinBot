import requests
import pandas as pd
import logging
import time
from typing import Dict, List, Optional, Any
from .base import BaseDataAdapter
from datetime import datetime, timedelta
import os
from threading import Lock

logger = logging.getLogger(__name__)

class FMPAdapter(BaseDataAdapter):
    def __init__(self):
        self._name = "Financial Modeling Prep"
        self.api_key = os.getenv('FMP_API_KEY')
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.base_url_v4 = "https://financialmodelingprep.com/api/v4"

        # Rate limiting
        self.request_timestamps = []
        self.rate_limit_lock = Lock()
        self.max_requests_per_minute = 5  # FMP free tier limit
        self.max_requests_per_day = 250   # FMP free tier limit

        # Cache to avoid duplicate requests
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    @property
    def name(self) -> str:
        return self._name

    def _check_rate_limit(self):
        """Implement rate limiting for FMP API"""
        with self.rate_limit_lock:
            now = time.time()

            # Remove requests older than 1 minute
            self.request_timestamps = [
                ts for ts in self.request_timestamps
                if now - ts < 60
            ]

            # Remove requests older than 24 hours for daily limit
            daily_requests = [
                ts for ts in self.request_timestamps
                if now - ts < 86400
            ]

            if len(self.request_timestamps) >= self.max_requests_per_minute:
                sleep_time = 60 - (now - self.request_timestamps[0])
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.1f} seconds")
                time.sleep(max(sleep_time, 1))
                self.request_timestamps = []

            if len(daily_requests) >= self.max_requests_per_day:
                raise Exception("Daily API limit reached")

            self.request_timestamps.append(now)

    def _make_request(self, endpoint: str, params: Dict = None, use_v4: bool = False) -> Optional[Any]:
        """Make API request with rate limiting and error handling"""
        if not self.api_key:
            logger.error("FMP API key not configured")
            return None

        try:
            self._check_rate_limit()

            base_url = self.base_url_v4 if use_v4 else self.base_url
            url = f"{base_url}/{endpoint}"

            if params is None:
                params = {}

            params['apikey'] = self.api_key

            # Create cache key
            cache_key = f"{url}?{sorted(params.items())}"

            # Check cache
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    return cached_data

            logger.info(f"FMP API Request: {endpoint}")
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 429:
                logger.warning("FMP rate limit hit, waiting 60 seconds")
                time.sleep(60)
                return self._make_request(endpoint, params, use_v4)

            if response.status_code != 200:
                logger.error(f"FMP API error {response.status_code}: {response.text}")
                return None

            data = response.json()

            # Cache successful response
            self.cache[cache_key] = (data, time.time())

            return data

        except Exception as e:
            logger.error(f"FMP request failed for {endpoint}: {e}")
            return None

    def get_historical_data(self, symbol: str, period: str = '1mo', interval: str = '1d') -> Optional[pd.DataFrame]:
        """Get historical price data"""
        # Map period to FMP format
        period_map = {
            '1d': '1',
            '1wk': '5',
            '1mo': '1',
            '3mo': '3',
            '6mo': '6',
            '1y': '1',
            '5y': '5'
        }

        # Map interval to FMP format
        interval_map = {
            '1m': '1min',
            '5m': '5min',
            '15m': '15min',
            '30m': '30min',
            '1h': '1hour',
            '1d': '1day'
        }

        fmp_interval = interval_map.get(interval, '1day')

        try:
            if fmp_interval.endswith('min') or fmp_interval.endswith('hour'):
                # Intraday data
                endpoint = f"historical-chart/{fmp_interval}/{symbol}"
                data = self._make_request(endpoint)
            else:
                # Daily data
                years = period_map.get(period, '1')
                endpoint = f"historical-price-full/{symbol}"
                params = {'timeseries': years}
                data = self._make_request(endpoint, params)

            if not data:
                return None

            # Parse response
            if isinstance(data, list):
                df = pd.DataFrame(data)
                if 'date' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['date'])
                    df.set_index('timestamp', inplace=True)
                elif 't' in df.columns:  # Unix timestamp
                    df['timestamp'] = pd.to_datetime(df['t'], unit='s')
                    df.set_index('timestamp', inplace=True)
            elif isinstance(data, dict) and 'historical' in data:
                df = pd.DataFrame(data['historical'])
                df['timestamp'] = pd.to_datetime(df['date'])
                df.set_index('timestamp', inplace=True)
            else:
                return None

            # Standardize column names
            column_map = {
                'open': 'open', 'high': 'high', 'low': 'low',
                'close': 'close', 'volume': 'volume',
                'adjClose': 'adj_close', 'adjClose': 'adjusted_close'
            }

            df = df.rename(columns={v: k for k, v in column_map.items() if v in df.columns})
            df['data_source'] = self.name

            return df[['open', 'high', 'low', 'close', 'volume', 'data_source']].dropna()

        except Exception as e:
            logger.error(f"FMP historical data error for {symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current stock price"""
        try:
            endpoint = f"quote/{symbol}"
            data = self._make_request(endpoint)

            if data and isinstance(data, list) and len(data) > 0:
                return data[0].get('price')
            return None
        except Exception as e:
            logger.error(f"FMP current price error for {symbol}: {e}")
            return None

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get comprehensive symbol information"""
        try:
            # Get profile
            endpoint = f"profile/{symbol}"
            profile_data = self._make_request(endpoint)

            if not profile_data or not isinstance(profile_data, list):
                return None

            profile = profile_data[0]

            # Get quote for additional data
            quote_data = self._make_request(f"quote/{symbol}")
            quote = quote_data[0] if quote_data and isinstance(quote_data, list) else {}

            return {
                'name': profile.get('companyName', symbol),
                'sector': profile.get('sector', 'N/A'),
                'industry': profile.get('industry', 'N/A'),
                'market_cap': profile.get('mktCap'),
                'exchange': profile.get('exchange', 'N/A'),
                'currency': profile.get('currency', 'USD'),
                'description': profile.get('description', ''),
                'website': profile.get('website', ''),
                'ceo': profile.get('ceo', ''),
                'employees': profile.get('fullTimeEmployees'),
                'price': quote.get('price'),
                'changes': quote.get('changes'),
                'changes_percentage': quote.get('changesPercentage')
            }
        except Exception as e:
            logger.error(f"FMP symbol info error for {symbol}: {e}")
            return None

    def get_financial_statements(self, symbol: str, statement_type: str = 'income') -> Optional[pd.DataFrame]:
        """Get financial statements"""
        try:
            endpoint = f"{statement_type}-statement/{symbol}"
            params = {'limit': 5}  # Last 5 periods

            data = self._make_request(endpoint, params)

            if data and isinstance(data, list):
                df = pd.DataFrame(data)
                return df
            return None
        except Exception as e:
            logger.error(f"FMP financial statements error for {symbol}: {e}")
            return None

    def get_market_news(self, limit: int = 10) -> Optional[List[Dict]]:
        """Get market news"""
        try:
            endpoint = "stock_news"
            params = {'limit': limit}

            data = self._make_request(endpoint, params)
            return data if isinstance(data, list) else None
        except Exception as e:
            logger.error(f"FMP market news error: {e}")
            return None

    def get_stock_screener(self, filters: Dict = None) -> Optional[pd.DataFrame]:
        """Stock screener with various filters"""
        try:
            endpoint = "stock-screener"
            params = filters or {
                'marketCapMoreThan': 1000000000,  # $1B+ market cap
                'volumeMoreThan': 100000,         # 100k+ volume
                'limit': 50
            }

            data = self._make_request(endpoint, params)

            if data and isinstance(data, list):
                return pd.DataFrame(data)
            return None
        except Exception as e:
            logger.error(f"FMP stock screener error: {e}")
            return None

    def get_technical_indicators(self, symbol: str, indicator: str = 'sma', period: int = 50) -> Optional[pd.DataFrame]:
        """Get technical indicators"""
        try:
            endpoint = f"technical_indicator/daily/{symbol}"
            params = {
                'type': indicator.upper(),
                'period': period
            }

            data = self._make_request(endpoint, params)

            if data and isinstance(data, list):
                df = pd.DataFrame(data)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                return df
            return None
        except Exception as e:
            logger.error(f"FMP technical indicators error for {symbol}: {e}")
            return None

    def get_earnings_calendar(self, from_date: str = None, to_date: str = None) -> Optional[pd.DataFrame]:
        """Get earnings calendar"""
        try:
            endpoint = "earning_calendar"
            params = {}

            if from_date:
                params['from'] = from_date
            if to_date:
                params['to'] = to_date

            data = self._make_request(endpoint, params)

            if data and isinstance(data, list):
                df = pd.DataFrame(data)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                return df
            return None
        except Exception as e:
            logger.error(f"FMP earnings calendar error: {e}")
            return None

    def get_forex_rates(self, base_currency: str = 'USD') -> Optional[Dict]:
        """Get forex exchange rates"""
        try:
            endpoint = f"fx/{base_currency}"
            data = self._make_request(endpoint)
            return data if isinstance(data, list) else None
        except Exception as e:
            logger.error(f"FMP forex rates error: {e}")
            return None

    def get_crypto_prices(self, symbol: str = 'BTCUSD') -> Optional[float]:
        """Get cryptocurrency prices"""
        try:
            endpoint = f"quote/{symbol}"
            data = self._make_request(endpoint)

            if data and isinstance(data, list) and len(data) > 0:
                return data[0].get('price')
            return None
        except Exception as e:
            logger.error(f"FMP crypto price error for {symbol}: {e}")
            return None

    def get_api_usage(self) -> Optional[Dict]:
        """Check API usage and limits"""
        try:
            # FMP doesn't have a direct usage endpoint, but we can track locally
            now = time.time()
            requests_last_hour = len([ts for ts in self.request_timestamps if now - ts < 3600])
            requests_today = len([ts for ts in self.request_timestamps if now - ts < 86400])

            return {
                'requests_last_hour': requests_last_hour,
                'requests_today': requests_today,
                'daily_limit': self.max_requests_per_day,
                'hourly_limit': self.max_requests_per_minute * 60
            }
        except Exception as e:
            logger.error(f"FMP API usage error: {e}")
            return None

    def is_available(self) -> bool:
        """Check if FMP API is available"""
        try:
            test_price = self.get_current_price('AAPL')
            return test_price is not None
        except Exception as e:
            logger.error(f"FMP availability check failed: {e}")
            return False
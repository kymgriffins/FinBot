"""
Alpha Vantage Data Adapter for Gr8 Agent
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import time
from .base_adapter import BaseDataAdapter, DataSourceInfo, DataQuality

logger = logging.getLogger(__name__)

class AlphaVantageAdapter(BaseDataAdapter):
    """Alpha Vantage data adapter with comprehensive market data"""

    def __init__(self, api_key: str):
        super().__init__(api_key=api_key, rate_limit=5)  # Alpha Vantage has strict limits
        self.base_url = "https://www.alphavantage.co/query"
        self.session = requests.Session()

    def _get_source_info(self) -> DataSourceInfo:
        """Get Alpha Vantage source information"""
        return DataSourceInfo(
            name="Alpha Vantage",
            reliability_score=0.90,  # High reliability
            rate_limit=5,  # requests per minute (free tier)
            cost_per_request=0.0,  # Free tier
            supported_symbols=[],  # Supports most symbols
            supported_intervals=['1min', '5min', '15min', '30min', '60min', 'daily', 'weekly', 'monthly'],
            data_delay=0,  # Real-time data
            last_updated=datetime.now()
        )

    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime,
                   interval: str = 'daily') -> pd.DataFrame:
        """Fetch data from Alpha Vantage"""
        try:
            # Check rate limiting
            if not self.rate_limiter.can_make_request():
                logger.warning(f"Rate limit exceeded for Alpha Vantage. Waiting...")
                return pd.DataFrame()

            # Check cache first
            cache_key = self.get_cache_key(symbol, start_date, end_date, interval)
            cached_data = self.get_cached_data(cache_key)
            if cached_data is not None:
                logger.info(f"Using cached data for {symbol}")
                return cached_data

            # Record request
            self.rate_limiter.record_request()

            # Map interval to Alpha Vantage format
            av_interval = self._map_interval(interval)

            # Make API request
            params = {
                'function': 'TIME_SERIES_DAILY' if av_interval == 'daily' else 'TIME_SERIES_INTRADAY',
                'symbol': symbol,
                'apikey': self.api_key,
                'outputsize': 'full',
                'datatype': 'json'
            }

            if av_interval != 'daily':
                params['interval'] = av_interval

            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if 'Error Message' in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return pd.DataFrame()

            if 'Note' in data:
                logger.warning(f"Alpha Vantage API note: {data['Note']}")
                return pd.DataFrame()

            # Parse the data
            df = self._parse_response(data, av_interval)

            if df.empty:
                logger.warning(f"No data returned from Alpha Vantage for {symbol}")
                return pd.DataFrame()

            # Filter by date range
            df = df[(df.index >= start_date) & (df.index <= end_date)]

            # Clean and standardize data
            df = self._clean_data(df)

            # Cache the data
            self.cache_data(cache_key, df)

            logger.info(f"Successfully fetched {len(df)} records for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Alpha Vantage error for {symbol}: {e}")
            return pd.DataFrame()

    def _map_interval(self, interval: str) -> str:
        """Map standard interval to Alpha Vantage format"""
        mapping = {
            '1m': '1min',
            '5m': '5min',
            '15m': '15min',
            '30m': '30min',
            '1h': '60min',
            '1d': 'daily',
            '1wk': 'weekly',
            '1mo': 'monthly'
        }
        return mapping.get(interval, 'daily')

    def _parse_response(self, data: dict, interval: str) -> pd.DataFrame:
        """Parse Alpha Vantage API response"""
        try:
            # Get the time series key
            if interval == 'daily':
                time_series_key = 'Time Series (Daily)'
            elif interval == 'weekly':
                time_series_key = 'Weekly Time Series'
            elif interval == 'monthly':
                time_series_key = 'Monthly Time Series'
            else:
                time_series_key = f'Time Series ({interval})'

            if time_series_key not in data:
                logger.error(f"Expected key '{time_series_key}' not found in response")
                return pd.DataFrame()

            time_series = data[time_series_key]

            # Convert to DataFrame
            df = pd.DataFrame.from_dict(time_series, orient='index')
            df.index = pd.to_datetime(df.index)

            # Rename columns to standard format
            column_mapping = {
                '1. open': 'Open',
                '2. high': 'High',
                '3. low': 'Low',
                '4. close': 'Close',
                '5. volume': 'Volume'
            }

            df = df.rename(columns=column_mapping)

            # Convert to numeric
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            return df.sort_index()

        except Exception as e:
            logger.error(f"Error parsing Alpha Vantage response: {e}")
            return pd.DataFrame()

    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize Alpha Vantage data"""
        if data.empty:
            return data

        # Remove any rows with all NaN values
        data = data.dropna(how='all')

        # Remove rows with invalid prices
        if 'Close' in data.columns:
            data = data[data['Close'] > 0]

        # Ensure high >= low
        if all(col in data.columns for col in ['High', 'Low']):
            data = data[data['High'] >= data['Low']]

        return data.sort_index()

    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """Get company overview information"""
        try:
            if not self.rate_limiter.can_make_request():
                return {}

            self.rate_limiter.record_request()

            params = {
                'function': 'OVERVIEW',
                'symbol': symbol,
                'apikey': self.api_key
            }

            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'Error Message' in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return {}

            return data

        except Exception as e:
            logger.error(f"Error getting company overview for {symbol}: {e}")
            return {}

    def get_earnings_calendar(self, symbol: str) -> pd.DataFrame:
        """Get earnings calendar data"""
        try:
            if not self.rate_limiter.can_make_request():
                return pd.DataFrame()

            self.rate_limiter.record_request()

            params = {
                'function': 'EARNINGS_CALENDAR',
                'symbol': symbol,
                'horizon': '3month',
                'apikey': self.api_key
            }

            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            # Alpha Vantage returns CSV for earnings calendar
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))

            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')

            return df

        except Exception as e:
            logger.error(f"Error getting earnings calendar for {symbol}: {e}")
            return pd.DataFrame()

    def get_technical_indicators(self, symbol: str, function: str = 'SMA',
                                interval: str = 'daily', time_period: int = 20) -> pd.DataFrame:
        """Get technical indicators"""
        try:
            if not self.rate_limiter.can_make_request():
                return pd.DataFrame()

            self.rate_limiter.record_request()

            params = {
                'function': function,
                'symbol': symbol,
                'interval': interval,
                'time_period': time_period,
                'series_type': 'close',
                'apikey': self.api_key
            }

            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'Error Message' in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return pd.DataFrame()

            # Parse technical indicator data
            indicator_key = f'Technical Analysis: {function}'
            if indicator_key not in data:
                return pd.DataFrame()

            df = pd.DataFrame.from_dict(data[indicator_key], orient='index')
            df.index = pd.to_datetime(df.index)

            # Convert to numeric
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            return df.sort_index()

        except Exception as e:
            logger.error(f"Error getting technical indicators for {symbol}: {e}")
            return pd.DataFrame()

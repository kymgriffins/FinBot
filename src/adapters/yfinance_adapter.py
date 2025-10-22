"""
Enhanced YFinance Data Adapter for Gr8 Agent
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
import logging
from .base_adapter import BaseDataAdapter, DataSourceInfo, DataQuality

logger = logging.getLogger(__name__)

class YFinanceAdapter(BaseDataAdapter):
    """Enhanced YFinance data adapter with improved error handling and validation"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, rate_limit=100)  # YFinance is more lenient
        self.session = None
    
    def _get_source_info(self) -> DataSourceInfo:
        """Get YFinance source information"""
        return DataSourceInfo(
            name="Yahoo Finance",
            reliability_score=0.85,  # Good reliability
            rate_limit=100,  # requests per minute
            cost_per_request=0.0,  # Free
            supported_symbols=[],  # Supports most symbols
            supported_intervals=['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'],
            data_delay=15,  # 15 minutes delay
            last_updated=datetime.now()
        )
    
    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime, 
                   interval: str = '1d') -> pd.DataFrame:
        """Fetch data from YFinance with enhanced error handling"""
        try:
            # Check rate limiting
            if not self.rate_limiter.can_make_request():
                logger.warning(f"Rate limit exceeded for YFinance. Waiting...")
                return pd.DataFrame()
            
            # Check cache first
            cache_key = self.get_cache_key(symbol, start_date, end_date, interval)
            cached_data = self.get_cached_data(cache_key)
            if cached_data is not None:
                logger.info(f"Using cached data for {symbol}")
                return cached_data
            
            # Record request
            self.rate_limiter.record_request()
            
            # Create ticker object
            ticker = yf.Ticker(symbol)
            
            # Fetch data
            data = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=True,
                prepost=True,
                threads=True
            )
            
            if data.empty:
                logger.warning(f"No data returned from YFinance for {symbol}")
                return pd.DataFrame()
            
            # Clean and standardize data
            data = self._clean_data(data)
            
            # Cache the data
            self.cache_data(cache_key, data)
            
            logger.info(f"Successfully fetched {len(data)} records for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"YFinance error for {symbol}: {e}")
            return pd.DataFrame()
    
    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize YFinance data"""
        if data.empty:
            return data
        
        # Ensure timezone-naive index
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)
        
        # Standardize column names
        column_mapping = {
            'Open': 'Open',
            'High': 'High', 
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume',
            'Adj Close': 'Adj_Close'
        }
        
        # Keep only the columns we need
        available_columns = [col for col in column_mapping.keys() if col in data.columns]
        data = data[available_columns]
        
        # Rename columns to standard format
        data = data.rename(columns=column_mapping)
        
        # Remove any rows with all NaN values
        data = data.dropna(how='all')
        
        # Ensure numeric types
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_columns:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # Remove rows with invalid prices
        if 'Close' in data.columns:
            data = data[data['Close'] > 0]
        
        # Sort by date
        data = data.sort_index()
        
        return data
    
    def get_company_info(self, symbol: str) -> dict:
        """Get company information"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', ''),
                'country': info.get('country', ''),
                'website': info.get('website', ''),
                'description': info.get('longBusinessSummary', '')
            }
        except Exception as e:
            logger.error(f"Error getting company info for {symbol}: {e}")
            return {}
    
    def get_dividends(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get dividend data"""
        try:
            ticker = yf.Ticker(symbol)
            dividends = ticker.dividends.loc[start_date:end_date]
            return dividends
        except Exception as e:
            logger.error(f"Error getting dividends for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_splits(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get stock split data"""
        try:
            ticker = yf.Ticker(symbol)
            splits = ticker.splits.loc[start_date:end_date]
            return splits
        except Exception as e:
            logger.error(f"Error getting splits for {symbol}: {e}")
            return pd.DataFrame()
    
    def search_symbols(self, query: str) -> List[dict]:
        """Search for symbols (basic implementation)"""
        # YFinance doesn't have a built-in search, so we'll return common symbols
        common_symbols = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'NASDAQ'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'exchange': 'NASDAQ'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'exchange': 'NASDAQ'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'exchange': 'NASDAQ'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'exchange': 'NASDAQ'},
            {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF', 'exchange': 'NYSE'},
            {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust', 'exchange': 'NASDAQ'},
            {'symbol': 'IWM', 'name': 'iShares Russell 2000 ETF', 'exchange': 'NYSE'}
        ]
        
        # Filter by query
        if query:
            query_lower = query.lower()
            return [s for s in common_symbols 
                   if query_lower in s['symbol'].lower() or query_lower in s['name'].lower()]
        
        return common_symbols

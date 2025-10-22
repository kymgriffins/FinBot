"""
Base Data Adapter for Gr8 Agent
Provides a standardized interface for all data sources
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DataQuality(Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    quality_score: float  # 0-1
    quality_level: DataQuality
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]

@dataclass
class DataSourceInfo:
    """Information about a data source"""
    name: str
    reliability_score: float  # 0-1
    rate_limit: int  # requests per minute
    cost_per_request: float
    supported_symbols: List[str]
    supported_intervals: List[str]
    data_delay: int  # seconds
    last_updated: datetime

class RateLimiter:
    """Rate limiting for API calls"""

    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    def can_make_request(self) -> bool:
        """Check if we can make a request"""
        now = datetime.now()
        # Remove old requests outside time window
        self.requests = [req_time for req_time in self.requests
                        if now - req_time < timedelta(seconds=self.time_window)]

        return len(self.requests) < self.max_requests

    def record_request(self):
        """Record a request"""
        self.requests.append(datetime.now())

class BaseDataAdapter(ABC):
    """Base class for all data adapters"""

    def __init__(self, api_key: Optional[str] = None, rate_limit: int = 60):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(max_requests=rate_limit)
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes
        self.source_info = self._get_source_info()

    @abstractmethod
    def _get_source_info(self) -> DataSourceInfo:
        """Get information about this data source"""
        pass

    @abstractmethod
    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime,
                   interval: str = '1d') -> pd.DataFrame:
        """Fetch data from the source"""
        pass

    def validate_data(self, data: pd.DataFrame) -> ValidationResult:
        """Validate data quality"""
        errors = []
        warnings = []
        quality_score = 1.0

        if data.empty:
            errors.append("No data returned")
            quality_score = 0.0
        else:
            # Check for missing values
            missing_pct = data.isnull().sum().sum() / (len(data) * len(data.columns))
            if missing_pct > 0.1:
                errors.append(f"High missing data percentage: {missing_pct:.2%}")
                quality_score -= 0.3
            elif missing_pct > 0.05:
                warnings.append(f"Some missing data: {missing_pct:.2%}")
                quality_score -= 0.1

            # Check for invalid prices
            if 'Close' in data.columns:
                invalid_prices = (data['Close'] <= 0).sum()
                if invalid_prices > 0:
                    errors.append(f"Invalid prices found: {invalid_prices}")
                    quality_score -= 0.4

            # Check for data consistency
            if all(col in data.columns for col in ['High', 'Low', 'Close']):
                inconsistent = (data['High'] < data['Low']).sum()
                if inconsistent > 0:
                    errors.append(f"Inconsistent high/low prices: {inconsistent}")
                    quality_score -= 0.5

            # Check for extreme outliers
            if 'Close' in data.columns:
                returns = data['Close'].pct_change().dropna()
                extreme_returns = (abs(returns) > 0.2).sum()
                if extreme_returns > len(returns) * 0.05:
                    warnings.append(f"Many extreme returns: {extreme_returns}")
                    quality_score -= 0.1

        # Determine quality level
        if quality_score >= 0.9:
            quality_level = DataQuality.EXCELLENT
        elif quality_score >= 0.7:
            quality_level = DataQuality.GOOD
        elif quality_score >= 0.5:
            quality_level = DataQuality.FAIR
        elif quality_score >= 0.3:
            quality_level = DataQuality.POOR
        else:
            quality_level = DataQuality.UNKNOWN

        return ValidationResult(
            is_valid=len(errors) == 0,
            quality_score=max(0.0, quality_score),
            quality_level=quality_level,
            errors=errors,
            warnings=warnings,
            metadata={
                'data_points': len(data),
                'columns': list(data.columns),
                'date_range': f"{data.index.min()} to {data.index.max()}" if not data.empty else None
            }
        )

    def get_cached_data(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get data from cache"""
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return data
            else:
                del self.cache[cache_key]
        return None

    def cache_data(self, cache_key: str, data: pd.DataFrame):
        """Cache data"""
        self.cache[cache_key] = (data, datetime.now())

    def get_cache_key(self, symbol: str, start_date: datetime, end_date: datetime, interval: str) -> str:
        """Generate cache key"""
        return f"{self.__class__.__name__}:{symbol}:{start_date.date()}:{end_date.date()}:{interval}"

    def get_source_reliability(self) -> float:
        """Get source reliability score"""
        return self.source_info.reliability_score

    def is_available(self) -> bool:
        """Check if the data source is available"""
        return self.rate_limiter.can_make_request()

    def get_supported_symbols(self) -> List[str]:
        """Get list of supported symbols"""
        return self.source_info.supported_symbols

    def get_supported_intervals(self) -> List[str]:
        """Get list of supported intervals"""
        return self.source_info.supported_intervals

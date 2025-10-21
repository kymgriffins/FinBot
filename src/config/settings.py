"""
FinBot Configuration Management
Centralized configuration for all environments
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    name: str = "finbot"
    user: str = "finbot_user"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20

@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    timeout: int = 300

@dataclass
class APIConfig:
    """API configuration"""
    rate_limit: int = 100  # requests per minute
    timeout: int = 30
    max_retries: int = 3
    cache_ttl: int = 300  # 5 minutes

@dataclass
class DataSourceConfig:
    """Data source configuration"""
    yfinance_enabled: bool = True
    fmp_enabled: bool = True
    twelvedata_enabled: bool = True
    fmp_api_key: Optional[str] = None
    twelvedata_api_key: Optional[str] = None

@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str = "your-secret-key-here"
    jwt_secret: str = "your-jwt-secret-here"
    cors_origins: List[str] = None
    max_login_attempts: int = 5
    session_timeout: int = 3600  # 1 hour

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

class Config:
    """Main configuration class"""

    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        self.environment = environment
        self.debug = environment == Environment.DEVELOPMENT

        # Load environment variables
        self._load_from_env()

        # Initialize configurations
        self.database = DatabaseConfig()
        self.redis = RedisConfig()
        self.api = APIConfig()
        self.data_sources = DataSourceConfig()
        self.security = SecurityConfig()
        self.logging = LoggingConfig()

        # Environment-specific overrides
        self._apply_environment_overrides()

    def _load_from_env(self):
        """Load configuration from environment variables"""
        self.database_host = os.getenv('DATABASE_HOST', 'localhost')
        self.database_port = int(os.getenv('DATABASE_PORT', '5432'))
        self.database_name = os.getenv('DATABASE_NAME', 'finbot')
        self.database_user = os.getenv('DATABASE_USER', 'finbot_user')
        self.database_password = os.getenv('DATABASE_PASSWORD', '')

        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        self.redis_db = int(os.getenv('REDIS_DB', '0'))
        self.redis_password = os.getenv('REDIS_PASSWORD')

        self.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
        self.fmp_api_key = os.getenv('FMP_API_KEY')
        self.twelvedata_api_key = os.getenv('TWELVE_DATA_API_KEY')

        self.symbols = os.getenv('SYMBOLS', 'SPY,QQQ,AAPL,MSFT,TSLA').split(',')

    def _apply_environment_overrides(self):
        """Apply environment-specific configuration overrides"""
        if self.environment == Environment.PRODUCTION:
            self.debug = False
            self.api.rate_limit = 1000
            self.api.cache_ttl = 600  # 10 minutes
            self.logging.level = "WARNING"
        elif self.environment == Environment.STAGING:
            self.debug = True
            self.api.rate_limit = 500
            self.logging.level = "INFO"
        else:  # Development
            self.debug = True
            self.api.rate_limit = 100
            self.logging.level = "DEBUG"

    @property
    def database_url(self) -> str:
        """Get database URL"""
        return f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"

    @property
    def redis_url(self) -> str:
        """Get Redis URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins based on environment"""
        if self.environment == Environment.DEVELOPMENT:
            return ["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:5000"]
        elif self.environment == Environment.STAGING:
            return ["https://staging.finbot.ai"]
        else:  # Production
            return ["https://finbot.ai", "https://www.finbot.ai"]

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        feature_flags = {
            'ai_weekly_analysis': True,
            'traditional_weekly_analysis': True,
            'data_comparison': True,
            'real_time_data': self.environment != Environment.DEVELOPMENT,
            'advanced_analytics': self.environment == Environment.PRODUCTION,
            'user_authentication': self.environment != Environment.DEVELOPMENT,
        }
        return feature_flags.get(feature, False)

    def get_api_endpoints(self) -> Dict[str, str]:
        """Get available API endpoints"""
        base_url = "https://finbot.ai" if self.environment == Environment.PRODUCTION else "http://localhost:5000"

        return {
            'ai_weekly': f"{base_url}/ai-weekly",
            'weekly_analysis': f"{base_url}/api/weekly-analysis",
            'yfinance': f"{base_url}/api/yfinance",
            'fmp': f"{base_url}/api/fmp",
            'comparison': f"{base_url}/api/comparison",
            'health': f"{base_url}/health",
            'docs': f"{base_url}/docs"
        }

# Global configuration instance
config = Config(Environment(os.getenv('FLASK_ENV', 'development')))

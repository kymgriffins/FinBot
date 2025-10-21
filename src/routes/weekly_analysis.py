from flask import Blueprint, jsonify, current_app
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from functools import lru_cache
import requests
import os
import redis
import json
from typing import Dict, Optional, List
import logging

weekly_analysis_bp = Blueprint('weekly_analysis', __name__)

# Configure logging
logger = logging.getLogger(__name__)

class DataAdapter:
    """Base class for data adapters"""
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes

    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        raise NotImplementedError

class YFinanceAdapter(DataAdapter):
    """YFinance data adapter"""
    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval='1d')
            if data.empty:
                logger.warning(f"No data returned from YFinance for {symbol}")
                return pd.DataFrame()

            # Ensure timezone-naive index
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)

            return data[['Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception as e:
            logger.error(f"YFinance error for {symbol}: {e}")
            return pd.DataFrame()

class FMPAdapter(DataAdapter):
    """Financial Modeling Prep adapter"""
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('FMP_API_KEY')

    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        if not self.api_key:
            logger.warning("FMP API key not found, falling back to YFinance")
            return YFinanceAdapter().fetch_data(symbol, start_date, end_date)

        try:
            url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
            params = {
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'apikey': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'historical' not in data:
                    logger.warning(f"No historical data in FMP response for {symbol}")
                    return pd.DataFrame()

                df = pd.DataFrame(data['historical'])
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df = df.sort_index()

                # Ensure timezone-naive index
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)

                return df[['open', 'high', 'low', 'close', 'volume']].rename(
                    columns={'open': 'Open', 'high': 'High', 'low': 'Low',
                           'close': 'Close', 'volume': 'Volume'}
                )
            else:
                logger.error(f"FMP API error: {response.status_code}")
                return YFinanceAdapter().fetch_data(symbol, start_date, end_date)
        except Exception as e:
            logger.error(f"FMP error for {symbol}: {e}")
            return YFinanceAdapter().fetch_data(symbol, start_date, end_date)

class TwelveDataAdapter(DataAdapter):
    """Twelve Data adapter"""
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('TWELVE_DATA_API_KEY')

    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        if not self.api_key:
            logger.warning("TwelveData API key not found, falling back to YFinance")
            return YFinanceAdapter().fetch_data(symbol, start_date, end_date)

        try:
            url = "https://api.twelvedata.com/time_series"
            params = {
                'symbol': symbol,
                'interval': '1day',
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'apikey': self.api_key,
                'outputsize': 5000
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'values' not in data:
                    logger.warning(f"No values in TwelveData response for {symbol}")
                    return pd.DataFrame()

                df = pd.DataFrame(data['values'])
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)
                df = df.sort_index()

                # Ensure timezone-naive index
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)

                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                return df[numeric_cols].rename(
                    columns={'open': 'Open', 'high': 'High', 'low': 'Low',
                           'close': 'Close', 'volume': 'Volume'}
                )
            else:
                logger.error(f"TwelveData API error: {response.status_code}")
                return YFinanceAdapter().fetch_data(symbol, start_date, end_date)
        except Exception as e:
            logger.error(f"TwelveData error for {symbol}: {e}")
            return YFinanceAdapter().fetch_data(symbol, start_date, end_date)

class WeeklyMarketStructure:
    def __init__(self, data_adapter='yfinance'):
        self.data_adapter = data_adapter
        self.adapters = {
            'yfinance': YFinanceAdapter(),
            'fmp': FMPAdapter(),
            'twelvedata': TwelveDataAdapter()
        }
        self.redis_client = self._init_redis()

    def _init_redis(self):
        """Initialize Redis client for caching"""
        try:
            return redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=int(os.getenv('REDIS_DB', 0)),
                password=os.getenv('REDIS_PASSWORD'),
                decode_responses=True
            )
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}. Using memory cache only.")
            return None

    def _get_cache_key(self, symbol: str, adapter: str) -> str:
        """Generate cache key for symbol and adapter"""
        return f"weekly_analysis:{adapter}:{symbol}"

    def _get_cached_data(self, cache_key: str) -> Optional[dict]:
        """Get data from cache"""
        if not self.redis_client:
            return None

        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None

    def _set_cached_data(self, cache_key: str, data: dict, timeout: int = 300):
        """Set data in cache"""
        if not self.redis_client:
            return

        try:
            self.redis_client.setex(
                cache_key,
                timeout,
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def get_weekly_data(self, symbol: str, weeks_back: int = 2) -> Optional[dict]:
        """Get previous week's complete data and current week's partial data"""
        cache_key = self._get_cache_key(symbol, self.data_adapter)

        # Try to get from cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            logger.info(f"Using cached data for {symbol}")
            return cached_data

        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks_back + 1)

        # Get historical data
        historical_data = self._fetch_data(symbol, start_date, end_date)

        if historical_data.empty:
            logger.error(f"No historical data available for {symbol}")
            return None

        # Validate data quality
        if not self._validate_data_quality(historical_data):
            logger.warning(f"Data quality issues detected for {symbol}")

        # Resample to weekly data
        weekly_data = self._resample_to_weekly(historical_data)

        # Get current week's partial data
        current_week_data = self._get_current_week_partial_data(symbol, historical_data)

        result = {
            'previous_week': self._get_previous_week_data(weekly_data),
            'current_week': current_week_data,
            'symbol': symbol,
            'last_updated': datetime.now().isoformat(),
            'data_points': len(historical_data),
            'data_quality': self._assess_data_quality(historical_data)
        }

        # Cache the result
        self._set_cached_data(cache_key, result)

        return result

    def _validate_data_quality(self, data: pd.DataFrame) -> bool:
        """Validate the quality of the data"""
        if data.empty:
            return False

        # Check for missing values
        if data.isnull().any().any():
            logger.warning("Data contains missing values")
            return False

        # Check for zero or negative prices
        if (data[['Open', 'High', 'Low', 'Close']] <= 0).any().any():
            logger.warning("Data contains invalid price values")
            return False

        # Check for high-low consistency
        if not (data['High'] >= data['Low']).all():
            logger.warning("Data contains inconsistent high-low values")
            return False

        return True

    def _assess_data_quality(self, data: pd.DataFrame) -> dict:
        """Assess data quality metrics"""
        quality_metrics = {
            'total_records': len(data),
            'date_range_days': (data.index.max() - data.index.min()).days,
            'missing_values': data.isnull().sum().to_dict(),
            'price_consistency': {
                'high_low_valid': (data['High'] >= data['Low']).all(),
                'open_close_range': (data['Open'].between(data['Low'], data['High']).mean()),
                'volume_positive': (data['Volume'] >= 0).all()
            }
        }
        return quality_metrics

    def _fetch_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch data using selected adapter"""
        adapter = self.adapters.get(self.data_adapter, self.adapters['yfinance'])
        return adapter.fetch_data(symbol, start_date, end_date)

    def _resample_to_weekly(self, data: pd.DataFrame) -> pd.DataFrame:
        """Resample daily data to weekly with validation"""
        if data.empty:
            return data

        try:
            weekly = data.resample('W').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            })
            return weekly.dropna()
        except Exception as e:
            logger.error(f"Weekly resampling error: {e}")
            return pd.DataFrame()

    def _get_previous_week_data(self, weekly_data: pd.DataFrame) -> Optional[dict]:
        """Get complete previous week's data"""
        if len(weekly_data) < 2:
            return None

        try:
            prev_week = weekly_data.iloc[-2]
            return {
                'week_start': prev_week.name.strftime('%Y-%m-%d'),
                'open': float(prev_week['Open']),
                'high': float(prev_week['High']),
                'low': float(prev_week['Low']),
                'close': float(prev_week['Close']),
                'volume': int(prev_week['Volume']),
                'range': float(prev_week['High'] - prev_week['Low']),
                'body': float(abs(prev_week['Close'] - prev_week['Open'])),
                'body_percentage': float(abs(prev_week['Close'] - prev_week['Open']) / (prev_week['High'] - prev_week['Low']) if (prev_week['High'] - prev_week['Low']) > 0 else 0)
            }
        except Exception as e:
            logger.error(f"Error getting previous week data: {e}")
            return None

    def _get_current_week_partial_data(self, symbol: str, daily_data: pd.DataFrame) -> dict:
        """Get current week's partial data with predictive analysis"""
        today = datetime.now().date()
        current_week_start = today - timedelta(days=today.weekday())

        # Convert index to date for safe comparison (fixes timezone issues)
        daily_data_dates = daily_data.index.date

        # Filter current week data
        current_week_mask = daily_data_dates >= current_week_start
        current_week_daily = daily_data[current_week_mask].copy()

        if current_week_daily.empty:
            return self._create_empty_current_week()

        # Get completed days (Monday to today)
        completed_days_mask = daily_data_dates[current_week_mask] <= today
        completed_days = current_week_daily[completed_days_mask]

        # Calculate current week stats based on completed days
        if not completed_days.empty:
            week_open = float(completed_days.iloc[0]['Open'])
            week_high = float(completed_days['High'].max())
            week_low = float(completed_days['Low'].min())
            current_price = float(completed_days.iloc[-1]['Close'])

            # Predict remaining week
            predictions = self._predict_remaining_week(
                completed_days, week_open, week_high, week_low, current_price
            )

            return {
                'week_start': current_week_start.strftime('%Y-%m-%d'),
                'completed_days': len(completed_days),
                'current_data': {
                    'open': week_open,
                    'high': week_high,
                    'low': week_low,
                    'current_price': current_price,
                    'days_completed': len(completed_days),
                    'current_range': week_high - week_low,
                    'from_open_percent': ((current_price - week_open) / week_open) * 100
                },
                'predictions': predictions,
                'daily_breakdown': self._get_daily_breakdown(completed_days, predictions),
                'is_complete': len(completed_days) >= 5,
                'week_progress': f"{len(completed_days)}/5 days"
            }

        return self._create_empty_current_week()

    def _create_empty_current_week(self) -> dict:
        """Create empty current week structure"""
        return {
            'week_start': datetime.now().date().strftime('%Y-%m-%d'),
            'completed_days': 0,
            'current_data': None,
            'predictions': None,
            'daily_breakdown': {},
            'is_complete': False,
            'week_progress': "0/5 days"
        }

    def _predict_remaining_week(self, completed_days: pd.DataFrame, week_open: float,
                              week_high: float, week_low: float, current_price: float) -> dict:
        """Predict remaining week based on current data and patterns"""
        days_remaining = 5 - len(completed_days)

        if days_remaining <= 0:
            return {
                'predicted_high': week_high,
                'predicted_low': week_low,
                'predicted_close': current_price,
                'confidence': 1.0,
                'scenarios': [],
                'prediction_basis': 'week_complete'
            }

        # Calculate volatility and momentum metrics
        daily_ranges = completed_days['High'] - completed_days['Low']
        avg_daily_range = float(daily_ranges.mean())
        current_volatility = float(daily_ranges.std())

        # Calculate additional metrics
        price_changes = completed_days['Close'].pct_change().dropna()
        avg_daily_return = float(price_changes.mean())
        volatility_ratio = current_volatility / avg_daily_range if avg_daily_range > 0 else 1.0

        # Base predictions on current momentum
        latest_day = completed_days.iloc[-1]
        daily_momentum = (latest_day['Close'] - latest_day['Open']) / latest_day['Open']
        weekly_momentum = (current_price - week_open) / week_open

        # Create prediction scenarios
        scenarios = self._generate_prediction_scenarios(
            current_price, week_high, week_low, avg_daily_range,
            current_volatility, daily_momentum, weekly_momentum, days_remaining
        )

        # Enhanced prediction logic
        volatility_adjustment = 1 + (volatility_ratio - 1) * 0.5
        base_adjustment = avg_daily_range * days_remaining * 0.3 * volatility_adjustment

        predicted_high = max(week_high, current_price + base_adjustment)
        predicted_low = min(week_low, current_price - base_adjustment)

        # Close prediction with momentum weighting
        momentum_weight = weekly_momentum * 2  # Amplify weekly momentum
        predicted_close = current_price * (1 + momentum_weight * days_remaining * 0.1)

        confidence = max(0.1, min(0.8, 0.6 - (volatility_ratio - 1) * 0.2))

        return {
            'predicted_high': float(predicted_high),
            'predicted_low': float(predicted_low),
            'predicted_close': float(predicted_close),
            'confidence': confidence,
            'scenarios': scenarios,
            'days_remaining': days_remaining,
            'avg_daily_range': avg_daily_range,
            'current_volatility': current_volatility,
            'volatility_ratio': volatility_ratio,
            'prediction_basis': f'based_on_{len(completed_days)}_days',
            'momentum_indicators': {
                'daily': daily_momentum,
                'weekly': weekly_momentum,
                'avg_daily_return': avg_daily_return
            }
        }

    def _generate_prediction_scenarios(self, current_price: float, week_high: float, week_low: float,
                                    avg_range: float, volatility: float, daily_momentum: float,
                                    weekly_momentum: float, days_remaining: int) -> List[dict]:
        """Generate different prediction scenarios with enhanced logic"""
        scenarios = []

        # Bullish scenario
        bullish_prob = max(0.1, 0.25 + (weekly_momentum * 8) + (daily_momentum * 2))
        bullish_high = current_price + (avg_range * days_remaining * 0.6)
        bullish_low = max(week_low, current_price - (avg_range * 0.2))
        bullish_close = current_price + (avg_range * days_remaining * 0.25)

        scenarios.append({
            'type': 'bullish',
            'probability': bullish_prob,
            'high': float(bullish_high),
            'low': float(bullish_low),
            'close': float(bullish_close),
            'description': 'Strong bullish momentum continuation',
            'trigger': 'Break above current high with volume'
        })

        # Bearish scenario
        bearish_prob = max(0.1, 0.25 - (weekly_momentum * 8) - (daily_momentum * 2))
        bearish_high = min(week_high, current_price + (avg_range * 0.2))
        bearish_low = current_price - (avg_range * days_remaining * 0.6)
        bearish_close = current_price - (avg_range * days_remaining * 0.25)

        scenarios.append({
            'type': 'bearish',
            'probability': bearish_prob,
            'high': float(bearish_high),
            'low': float(bearish_low),
            'close': float(bearish_close),
            'description': 'Reversal and downward pressure',
            'trigger': 'Break below current low with momentum'
        })

        # Neutral/Consolidation scenario
        neutral_prob = 0.5  # Base probability
        neutral_high = current_price + (avg_range * 0.8)
        neutral_low = current_price - (avg_range * 0.8)
        neutral_close = current_price

        scenarios.append({
            'type': 'neutral',
            'probability': neutral_prob,
            'high': float(neutral_high),
            'low': float(neutral_low),
            'close': float(neutral_close),
            'description': 'Consolidation within current range',
            'trigger': 'Failure to break key levels'
        })

        # Normalize probabilities
        total_prob = sum(s['probability'] for s in scenarios)
        for scenario in scenarios:
            scenario['probability'] = scenario['probability'] / total_prob

        return scenarios

    def _get_daily_breakdown(self, completed_days: pd.DataFrame, predictions: dict) -> Dict[str, dict]:
        """Create daily breakdown with actual and predicted data"""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        breakdown = {}
        today_weekday = datetime.now().weekday()

        for i, day in enumerate(days):
            if i < len(completed_days):
                # Actual completed day
                day_data = completed_days.iloc[i]
                breakdown[day] = {
                    'type': 'actual',
                    'open': float(day_data['Open']),
                    'high': float(day_data['High']),
                    'low': float(day_data['Low']),
                    'close': float(day_data['Close']),
                    'volume': int(day_data['Volume']),
                    'range': float(day_data['High'] - day_data['Low']),
                    'body': float(abs(day_data['Close'] - day_data['Open'])),
                    'body_percentage': float(abs(day_data['Close'] - day_data['Open']) / (day_data['High'] - day_data['Low']) if (day_data['High'] - day_data['Low']) > 0 else 0)
                }
            elif i == today_weekday and len(completed_days) == today_weekday + 1:
                # Today's incomplete data (current day)
                latest = completed_days.iloc[-1]
                breakdown[day] = {
                    'type': 'in_progress',
                    'open': float(latest['Open']),
                    'high': float(latest['High']),
                    'low': float(latest['Low']),
                    'current': float(latest['Close']),
                    'volume': int(latest['Volume']),
                    'range': float(latest['High'] - latest['Low']),
                    'intraday_movement': float((latest['Close'] - latest['Open']) / latest['Open'] * 100)
                }
            elif i > today_weekday:
                # Future day - use predictions
                breakdown[day] = {
                    'type': 'predicted',
                    'open': float(predictions['predicted_close']),
                    'high': float(predictions['predicted_high']),
                    'low': float(predictions['predicted_low']),
                    'close': float(predictions['predicted_close']),
                    'range': float(predictions['predicted_high'] - predictions['predicted_low']),
                    'description': f'Projected based on {predictions["prediction_basis"]}',
                    'confidence': predictions['confidence']
                }
            else:
                # Day not yet reached or no data
                breakdown[day] = {
                    'type': 'pending',
                    'description': 'Data not available',
                    'expected': 'Market data pending'
                }

        return breakdown

# Cached analyzer instances with enhanced caching
@lru_cache(maxsize=20)
def get_analyzer(adapter: str) -> WeeklyMarketStructure:
    """Get analyzer instance with caching"""
    return WeeklyMarketStructure(data_adapter=adapter)

@weekly_analysis_bp.route('analyze/<symbol>')
@weekly_analysis_bp.route('analyze/<symbol>/<adapter>')
def analyze_weekly(symbol: str, adapter: str = 'yfinance'):
    """Analyze weekly market structure with predictive capabilities"""
    try:
        # Validate symbol
        if not symbol or len(symbol) > 10:
            return jsonify({
                'status': 'error',
                'error': 'Invalid symbol format'
            }), 400

        # Validate adapter
        valid_adapters = ['yfinance', 'fmp', 'twelvedata']
        if adapter not in valid_adapters:
            return jsonify({
                'status': 'error',
                'error': f'Invalid adapter. Must be one of: {", ".join(valid_adapters)}'
            }), 400

        analyzer = get_analyzer(adapter)
        weekly_data = analyzer.get_weekly_data(symbol)

        if not weekly_data:
            return jsonify({
                'status': 'error',
                'error': f'No data available for {symbol} using {adapter}'
            }), 404

        # Generate analysis
        analysis = generate_comprehensive_analysis(weekly_data)

        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'adapter': adapter,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'cache_info': {
                'cached': True,
                'data_points': weekly_data.get('data_points', 0),
                'data_quality': weekly_data.get('data_quality', {})
            }
        })

    except Exception as e:
        logger.error(f"Weekly analysis error for {symbol} with {adapter}: {e}")
        return jsonify({
            'status': 'error',
            'error': f'Analysis failed: {str(e)}'
        }), 500

@weekly_analysis_bp.route('/api/weekly-analysis/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test basic functionality
        analyzer = get_analyzer('yfinance')
        test_data = analyzer.get_weekly_data('SPY', weeks_back=1)

        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'cache_enabled': analyzer.redis_client is not None,
            'test_symbol_working': test_data is not None
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@weekly_analysis_bp.route('/api/weekly-analysis/adapters')
def list_adapters():
    """List available data adapters"""
    return jsonify({
        'adapters': [
            {
                'name': 'yfinance',
                'description': 'Yahoo Finance (free, no API key required)',
                'rate_limits': 'Moderate',
                'reliability': 'High'
            },
            {
                'name': 'fmp',
                'description': 'Financial Modeling Prep (requires API key)',
                'rate_limits': 'Generous',
                'reliability': 'High'
            },
            {
                'name': 'twelvedata',
                'description': 'Twelve Data (requires API key)',
                'rate_limits': 'Varies by plan',
                'reliability': 'High'
            }
        ]
    })

def generate_comprehensive_analysis(weekly_data: dict) -> dict:
    """Generate comprehensive market structure analysis"""
    prev_week = weekly_data['previous_week']
    curr_week = weekly_data['current_week']

    # Weekly levels with enhanced data
    weekly_levels = {
        'previous_week': prev_week,
        'current_week': {
            'open': curr_week['current_data']['open'] if curr_week['current_data'] else None,
            'high': curr_week['current_data']['high'] if curr_week['current_data'] else None,
            'low': curr_week['current_data']['low'] if curr_week['current_data'] else None,
            'current_price': curr_week['current_data']['current_price'] if curr_week['current_data'] else None,
            'range': curr_week['current_data']['current_range'] if curr_week['current_data'] else None,
            'from_open_percent': curr_week['current_data']['from_open_percent'] if curr_week['current_data'] else None
        } if curr_week['current_data'] else None,
        'predictions': curr_week['predictions'],
        'week_progress': curr_week['week_progress']
    }

    # Daily profiles with predictive elements
    daily_profiles = {}
    for day, data in curr_week['daily_breakdown'].items():
        if data['type'] == 'actual':
            daily_profiles[day] = analyze_daily_profile(data, 'actual')
        elif data['type'] == 'in_progress':
            daily_profiles[day] = analyze_daily_profile(data, 'in_progress')
        elif data['type'] == 'predicted':
            daily_profiles[day] = analyze_daily_profile(data, 'predicted')
        else:
            daily_profiles[day] = {
                'profile_type': 'Pending',
                'narrative': 'Awaiting market data',
                'key_levels': data
            }

    # Weekly narrative
    weekly_summary = generate_weekly_narrative(prev_week, curr_week)

    # Trading implications
    trading_implications = generate_trading_implications(prev_week, curr_week)

    return {
        'weekly_levels': weekly_levels,
        'daily_profiles': daily_profiles,
        'weekly_summary': weekly_summary,
        'trading_implications': trading_implications,
        'metadata': {
            'completed_days': curr_week['completed_days'],
            'days_remaining': 5 - curr_week['completed_days'],
            'is_week_complete': curr_week['is_complete'],
            'week_progress': curr_week['week_progress'],
            'last_updated': weekly_data['last_updated']
        }
    }

def analyze_daily_profile(day_data: dict, data_type: str) -> dict:
    """Analyze daily profile based on data type"""
    if data_type == 'actual':
        return analyze_completed_day(day_data)
    elif data_type == 'in_progress':
        return analyze_in_progress_day(day_data)
    elif data_type == 'predicted':
        return analyze_predicted_day(day_data)
    else:
        return {'profile_type': 'Unknown', 'narrative': 'No analysis available'}

def analyze_completed_day(day_data: dict) -> dict:
    """Analyze completed trading day with enhanced pattern recognition"""
    open_price = day_data['open']
    close = day_data['close']
    high = day_data['high']
    low = day_data['low']
    body = day_data.get('body', abs(close - open_price))
    range_total = day_data.get('range', high - low)

    # Enhanced pattern recognition
    body_to_range_ratio = body / range_total if range_total > 0 else 0

    if body_to_range_ratio < 0.1:
        profile_type = "Doji"
    elif body_to_range_ratio > 0.7 and close > open_price:
        profile_type = "Strong Bullish"
    elif body_to_range_ratio > 0.7 and close < open_price:
        profile_type = "Strong Bearish"
    elif close > open_price and high > day_data.get('prev_high', high):
        profile_type = "Bullish Engulfing"
    elif close < open_price and low < day_data.get('prev_low', low):
        profile_type = "Bearish Engulfing"
    elif range_total < day_data.get('prev_range', range_total) * 0.7:
        profile_type = "Inside Day"
    elif range_total > day_data.get('prev_range', range_total) * 1.3:
        profile_type = "Outside Day"
    else:
        profile_type = "Normal"

    return {
        'profile_type': profile_type,
        'key_levels': day_data,
        'narrative': generate_daily_narrative(day_data, profile_type),
        'metrics': {
            'body_to_range_ratio': body_to_range_ratio,
            'volume': day_data.get('volume', 0)
        }
    }

def analyze_in_progress_day(day_data: dict) -> dict:
    """Analyze current incomplete day"""
    current = day_data['current']
    open_price = day_data['open']
    high = day_data['high']
    low = day_data['low']

    momentum_percent = ((current - open_price) / open_price) * 100
    momentum = "bullish" if momentum_percent > 0.1 else "bearish" if momentum_percent < -0.1 else "neutral"

    profile_type = f"In Progress ({momentum})"

    return {
        'profile_type': profile_type,
        'key_levels': day_data,
        'narrative': f"Day in progress with {momentum} bias ({momentum_percent:+.2f}%). Current price: {current:.2f}",
        'intraday_metrics': {
            'momentum_percent': momentum_percent,
            'range_utilization': (high - low) / (day_data.get('avg_range', high - low)) if day_data.get('avg_range') else 1.0
        }
    }

def analyze_predicted_day(day_data: dict) -> dict:
    """Analyze predicted future day"""
    return {
        'profile_type': 'Projected',
        'key_levels': day_data,
        'narrative': f"Projected movement: {day_data.get('description', 'Based on current momentum')}",
        'confidence': day_data.get('confidence', 0.5)
    }

def generate_daily_narrative(day_data: dict, profile_type: str) -> str:
    """Generate narrative for daily profile"""
    templates = {
        'Strong Bullish': "Very strong buying pressure with minimal wicks, indicating conviction.",
        'Strong Bearish': "Very strong selling pressure with minimal wicks, indicating conviction.",
        'Bullish Engulfing': "Strong buying pressure overwhelmed sellers, suggesting potential continuation upward.",
        'Bearish Engulfing': "Sellers took control with aggressive selling, indicating potential downside follow-through.",
        'Inside Day': "Consolidation after previous movement, often precedes breakout.",
        'Outside Day': "Expansion of range with decisive movement in direction of close.",
        'Doji': "Indecision in the market, potential reversal signal depending on context.",
        'Normal': "Standard trading session within expected parameters."
    }
    return templates.get(profile_type, "Market activity observed.")

def generate_weekly_narrative(prev_week: dict, curr_week: dict) -> str:
    """Generate weekly market narrative with enhanced analysis"""
    if not prev_week or not curr_week['current_data']:
        return "Insufficient data for weekly narrative"

    prev_close = prev_week['close']
    curr_open = curr_week['current_data']['open']
    curr_price = curr_week['current_data']['current_price']
    curr_high = curr_week['current_data']['high']
    curr_low = curr_week['current_data']['low']

    # Weekly gap analysis
    gap_percent = ((curr_open - prev_close) / prev_close) * 100

    if gap_percent > 2:
        gap_narrative = f"Very strong bullish gap up {gap_percent:+.2f}% to start the week"
    elif gap_percent > 0.5:
        gap_narrative = f"Bullish gap up {gap_percent:+.2f}%"
    elif gap_percent < -2:
        gap_narrative = f"Very strong bearish gap down {gap_percent:+.2f}%"
    elif gap_percent < -0.5:
        gap_narrative = f"Bearish gap down {gap_percent:+.2f}%"
    else:
        gap_narrative = "Minimal gap at week open"

    # Current position analysis
    position_percent = ((curr_price - curr_open) / curr_open) * 100

    if position_percent > 2:
        position_narrative = "showing strong bullish momentum"
    elif position_percent > 0.5:
        position_narrative = "trading positively for the week"
    elif position_percent < -2:
        position_narrative = "under significant selling pressure"
    elif position_percent < -0.5:
        position_narrative = "facing bearish pressure"
    else:
        position_narrative = "consolidating near weekly open"

    return f"{gap_narrative}, with price {position_narrative}. {curr_week['completed_days']} days completed, {5 - curr_week['completed_days']} days remaining."

def generate_trading_implications(prev_week: dict, curr_week: dict) -> List[str]:
    """Generate trading implications based on weekly structure"""
    implications = []

    if not prev_week or not curr_week['current_data']:
        return ["Awaiting more data for trading implications"]

    curr_data = curr_week['current_data']
    predictions = curr_week.get('predictions', {})

    # Key level implications
    implications.append(f"Weekly open at {curr_data['open']:.2f} acts as primary reference")
    implications.append(f"Current week high {curr_data['high']:.2f} and low {curr_data['low']:.2f} define range boundaries")

    if predictions:
        conf = predictions.get('confidence', 0) * 100
        implications.append(f"Projected weekly range: {predictions.get('predicted_low', 0):.2f} - {predictions.get('predicted_high', 0):.2f} (confidence: {conf:.1f}%)")

    # Momentum implications
    if curr_data['current_price'] > curr_data['open']:
        implications.append("Bullish intra-week momentum suggests buying dips toward support")
    else:
        implications.append("Bearish pressure indicates selling rallies toward resistance")

    # Volume and volatility implications
    if predictions.get('current_volatility', 0) > predictions.get('avg_daily_range', 0):
        implications.append("Elevated volatility suggests wider stops and position sizing")
    else:
        implications.append("Normal volatility environment - standard risk parameters apply")

    return implications
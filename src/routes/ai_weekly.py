from flask import Blueprint, jsonify, render_template, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import requests
import os
import json
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
ai_weekly_bp = Blueprint('ai_weekly', __name__)

# Enhanced symbol universe
SYMBOL_UNIVERSE = {
    'stocks': [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V',
        'WMT', 'PG', 'DIS', 'NFLX', 'ADBE', 'PYPL', 'CRM', 'INTC', 'CSCO', 'AMD',
    ],
    'etfs': [
        'SPY', 'QQQ', 'IWM', 'DIA', 'VIXY', 'UVXY', 'TLT', 'GLD', 'SLV', 'USO',
    ],
    'futures': [
        'ES=F', 'NQ=F', 'YM=F', 'RTY=F', '6E=F', '6J=F', '6B=F',
        'CL=F', 'GC=F', 'SI=F', 'HG=F', 'NG=F',
    ],
    'forex': [
        'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X',
    ],
    'crypto': [
        'BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD',
    ]
}

# Flatten for easy access
ALL_SYMBOLS = [symbol for category in SYMBOL_UNIVERSE.values() for symbol in category]

class MarketPhase(Enum):
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    TREND = "trend"
    CONSOLIDATION = "consolidation"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"

class TimeFrame(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class SymbolType(Enum):
    STOCK = "stock"
    ETF = "etf"
    FUTURE = "future"
    FOREX = "forex"
    CRYPTO = "crypto"

@dataclass
class MarketLevel:
    """Represents a key market level"""
    price: float
    level_type: str  # 'support', 'resistance', 'pivot'
    strength: float  # 0-1 scale
    touches: int
    timeframe: str
    description: str

@dataclass
class DailyProfile:
    """Daily market profile data"""
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    range_size: float
    body_size: float
    upper_wick: float
    lower_wick: float
    profile_type: str
    market_phase: MarketPhase
    key_levels: List[MarketLevel]
    sentiment_score: float  # -1 to +1

class AIWeeklyAnalyzer:
    """Advanced AI-powered weekly market structure analyzer"""

    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.symbol_info_cache = {}

    def get_available_symbols(self) -> Dict[str, List[str]]:
        """Get categorized available symbols"""
        return SYMBOL_UNIVERSE

    def get_symbol_info(self, symbol: str) -> Dict:
        """Get detailed symbol information"""
        if symbol in self.symbol_info_cache:
            return self.symbol_info_cache[symbol]

        try:
            # Determine symbol type
            symbol_type = self._classify_symbol_type(symbol)

            # Get basic info from yfinance
            ticker = yf.Ticker(symbol)
            info = ticker.info

            symbol_info = {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'type': symbol_type.value,
                'exchange': info.get('exchange', 'Unknown'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'currency': info.get('currency', 'USD'),
                'description': self._get_symbol_description(symbol, symbol_type)
            }

            self.symbol_info_cache[symbol] = symbol_info
            return symbol_info

        except Exception as e:
            logger.warning(f"Could not get symbol info for {symbol}: {e}")
            return {
                'symbol': symbol,
                'name': symbol,
                'type': self._classify_symbol_type(symbol).value,
                'exchange': 'Unknown',
                'description': self._get_symbol_description(symbol, self._classify_symbol_type(symbol))
            }

    def _classify_symbol_type(self, symbol: str) -> SymbolType:
        """Classify symbol type"""
        if symbol in SYMBOL_UNIVERSE['stocks']:
            return SymbolType.STOCK
        elif symbol in SYMBOL_UNIVERSE['etfs']:
            return SymbolType.ETF
        elif symbol in SYMBOL_UNIVERSE['futures']:
            return SymbolType.FUTURE
        elif symbol in SYMBOL_UNIVERSE['forex']:
            return SymbolType.FOREX
        elif symbol in SYMBOL_UNIVERSE['crypto']:
            return SymbolType.CRYPTO
        elif '=F' in symbol:
            return SymbolType.FUTURE
        elif '=X' in symbol:
            return SymbolType.FOREX
        elif '-USD' in symbol:
            return SymbolType.CRYPTO
        else:
            return SymbolType.STOCK

    def _get_symbol_description(self, symbol: str, symbol_type: SymbolType) -> str:
        """Get human-readable symbol description"""
        descriptions = {
            'ES=F': 'S&P 500 E-mini Futures',
            'NQ=F': 'Nasdaq 100 E-mini Futures',
            'YM=F': 'Dow Jones E-mini Futures',
            'CL=F': 'Crude Oil WTI Futures',
            'GC=F': 'Gold Futures',
            'SI=F': 'Silver Futures',
            '6E=F': 'Euro FX Futures',
            'EURUSD=X': 'Euro/US Dollar',
            'GBPUSD=X': 'British Pound/US Dollar',
            'USDJPY=X': 'US Dollar/Japanese Yen',
            'BTC-USD': 'Bitcoin/US Dollar',
            'ETH-USD': 'Ethereum/US Dollar',
            'SPY': 'SPDR S&P 500 ETF',
            'QQQ': 'Invesco QQQ Trust (Nasdaq 100)',
            'IWM': 'iShares Russell 2000 ETF'
        }
        return descriptions.get(symbol, f"{symbol_type.value.title()} Instrument")

    def analyze_symbol(self, symbol: str, weeks_back: int = 4) -> Dict:
        """Main analysis function with enhanced error handling"""
        try:
            # Validate symbol
            if not self._validate_symbol(symbol):
                return self._create_error_response(f"Invalid or unsupported symbol: {symbol}")

            # Get symbol info
            symbol_info = self.get_symbol_info(symbol)

            # Get historical data
            data = self._fetch_market_data(symbol, weeks_back)
            if data.empty:
                return self._create_error_response(f"No market data available for {symbol}")

            # Analyze market structure
            market_structure = self._analyze_market_structure(data, symbol_info)

            # Generate daily profiles
            daily_profiles = self._generate_daily_profiles(data)

            # Create weekly narrative
            narrative = self._generate_weekly_narrative(market_structure, daily_profiles, symbol_info)

            # Generate trading insights
            insights = self._generate_trading_insights(market_structure, daily_profiles, symbol_info)

            # Predict next week
            predictions = self._predict_next_week(data, market_structure, symbol_info)

            # Calculate market sentiment
            sentiment = self._calculate_market_sentiment(market_structure, daily_profiles)

            return {
                'status': 'success',
                'symbol': symbol,
                'symbol_info': symbol_info,
                'timestamp': datetime.now().isoformat(),
                'market_structure': market_structure,
                'daily_profiles': daily_profiles[-5:],  # Last 5 days for efficiency
                'narrative': narrative,
                'insights': insights,
                'predictions': predictions,
                'sentiment': sentiment,
                'metadata': {
                    'data_points': len(data),
                    'weeks_analyzed': weeks_back,
                    'analysis_confidence': self._calculate_confidence(data),
                    'data_quality': self._assess_data_quality(data)
                }
            }

        except Exception as e:
            logger.error(f"Analysis error for {symbol}: {e}")
            return self._create_error_response(f"Analysis failed: {str(e)}")

    def _validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol is supported"""
        return symbol in ALL_SYMBOLS or any(symbol in category for category in SYMBOL_UNIVERSE.values())

    def _fetch_market_data(self, symbol: str, weeks_back: int) -> pd.DataFrame:
        """Fetch market data with enhanced error handling"""
        cache_key = f"{symbol}_{weeks_back}"
        current_time = datetime.now()

        # Check cache
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (current_time - timestamp).seconds < self.cache_timeout:
                logger.info(f"Using cached data for {symbol}")
                return cached_data

        # Fetch new data
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks_back)

        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval='1d')

            if not data.empty:
                # Clean and validate data
                data = self._clean_data(data)
                self.cache[cache_key] = (data, current_time)
                logger.info(f"Successfully fetched {len(data)} data points for {symbol}")
            else:
                logger.warning(f"No data returned for {symbol}")

            return data

        except Exception as e:
            logger.error(f"Data fetch error for {symbol}: {e}")
            return pd.DataFrame()

    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Enhanced data cleaning and validation"""
        if data.empty:
            return data

        # Remove any rows with NaN values in key columns
        data = data.dropna(subset=['Open', 'High', 'Low', 'Close'])

        # Ensure all price columns are positive and reasonable
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            data = data[data[col] > 0]
            # Remove extreme outliers (prices that are 10x median)
            median_price = data[col].median()
            data = data[data[col] < median_price * 10]
            data = data[data[col] > median_price / 10]

        # Validate high >= low >= close >= open relationships
        data = data[data['High'] >= data['Low']]
        data = data[data['High'] >= data['Close']]
        data = data[data['High'] >= data['Open']]
        data = data[data['Low'] <= data['Close']]
        data = data[data['Low'] <= data['Open']]

        # Remove zero-volume days for assets that should have volume
        if 'Volume' in data.columns:
            data = data[data['Volume'] > 0]

        return data

    def _analyze_market_structure(self, data: pd.DataFrame, symbol_info: Dict) -> Dict:
        """Enhanced market structure analysis"""
        if data.empty:
            return {}

        # Calculate key metrics
        current_price = data['Close'].iloc[-1]
        weekly_high = data['High'].max()
        weekly_low = data['Low'].min()
        weekly_range = weekly_high - weekly_low

        # Identify key levels across multiple timeframes
        key_levels = self._identify_key_levels(data)

        # Determine market phase
        market_phase = self._determine_market_phase(data)

        # Calculate volatility
        volatility = self._calculate_volatility(data)

        # Trend analysis
        trend = self._analyze_trend(data)

        # Volume analysis
        volume_analysis = self._analyze_volume(data)

        # Support/Resistance analysis
        sr_analysis = self._analyze_support_resistance(data, key_levels, current_price)

        return {
            'current_price': float(current_price),
            'weekly_high': float(weekly_high),
            'weekly_low': float(weekly_low),
            'weekly_range': float(weekly_range),
            'key_levels': key_levels,
            'market_phase': market_phase.value,
            'volatility': volatility,
            'trend': trend,
            'volume_analysis': volume_analysis,
            'support_resistance': sr_analysis,
            'range_percentage': float((current_price - weekly_low) / weekly_range * 100) if weekly_range > 0 else 50.0,
            'relative_strength': self._calculate_relative_strength(data)
        }

    def _identify_key_levels(self, data: pd.DataFrame) -> List[Dict]:
        """Enhanced key level identification"""
        levels = []

        # Multiple timeframe analysis
        timeframes = [5, 10, 20]  # days
        for tf in timeframes:
            if len(data) >= tf:
                # Resistance levels
                resistance = data['High'].rolling(window=tf).max()
                resistance_levels = data[data['High'] == resistance]['High'].dropna()

                for level in resistance_levels.unique():
                    touches = len(data[(data['High'] >= level * 0.995) & (data['High'] <= level * 1.005)])
                    if touches >= 2:
                        levels.append({
                            'price': float(level),
                            'type': 'resistance',
                            'strength': min(touches / 5, 1.0),
                            'touches': touches,
                            'timeframe': f'{tf}D',
                            'description': f'{tf}-day resistance'
                        })

                # Support levels
                support = data['Low'].rolling(window=tf).min()
                support_levels = data[data['Low'] == support]['Low'].dropna()

                for level in support_levels.unique():
                    touches = len(data[(data['Low'] <= level * 1.005) & (data['Low'] >= level * 0.995)])
                    if touches >= 2:
                        levels.append({
                            'price': float(level),
                            'type': 'support',
                            'strength': min(touches / 5, 1.0),
                            'touches': touches,
                            'timeframe': f'{tf}D',
                            'description': f'{tf}-day support'
                        })

        return sorted(levels, key=lambda x: x['price'])

    def _analyze_volume(self, data: pd.DataFrame) -> Dict:
        """Analyze volume patterns"""
        if len(data) < 5:
            return {}

        recent_volume = data['Volume'].tail(5)
        avg_volume = data['Volume'].mean()

        return {
            'current_volume': int(recent_volume.iloc[-1]),
            'volume_trend': float(recent_volume.pct_change().mean()),
            'volume_vs_average': float(recent_volume.mean() / avg_volume),
            'volume_spike': recent_volume.iloc[-1] > avg_volume * 1.5
        }

    def _analyze_support_resistance(self, data: pd.DataFrame, key_levels: List[Dict], current_price: float) -> Dict:
        """Analyze support/resistance structure"""
        nearby_levels = [level for level in key_levels if abs(level['price'] - current_price) / current_price < 0.05]

        support_levels = [level for level in nearby_levels if level['type'] == 'support']
        resistance_levels = [level for level in nearby_levels if level['type'] == 'resistance']

        return {
            'nearby_support': sorted(support_levels, key=lambda x: x['price'], reverse=True),
            'nearby_resistance': sorted(resistance_levels, key=lambda x: x['price']),
            'immediate_support': min([level['price'] for level in support_levels]) if support_levels else None,
            'immediate_resistance': max([level['price'] for level in resistance_levels]) if resistance_levels else None
        }

    def _calculate_relative_strength(self, data: pd.DataFrame) -> float:
        """Calculate relative strength index (simplified)"""
        if len(data) < 14:
            return 0.5

        gains = data['Close'].pct_change().apply(lambda x: x if x > 0 else 0)
        losses = data['Close'].pct_change().apply(lambda x: -x if x < 0 else 0)

        avg_gain = gains.rolling(14).mean().iloc[-1]
        avg_loss = losses.rolling(14).mean().iloc[-1]

        if avg_loss == 0:
            return 1.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi / 100)  # Normalize to 0-1

    def _calculate_market_sentiment(self, market_structure: Dict, daily_profiles: List[Dict]) -> Dict:
        """Calculate comprehensive market sentiment"""
        if not market_structure or not daily_profiles:
            return {'score': 0.5, 'bias': 'neutral'}

        # Multiple factors for sentiment
        trend_strength = market_structure['trend']['strength']
        trend_direction = 1 if market_structure['trend']['direction'] == 'bullish' else -1
        range_position = market_structure['range_percentage'] / 100  # 0-1 scale

        # Recent price action
        recent_profiles = daily_profiles[-3:]
        bullish_days = sum(1 for p in recent_profiles if p['close'] > p['open'])
        bearish_days = sum(1 for p in recent_profiles if p['close'] < p['open'])
        price_bias = (bullish_days - bearish_days) / 3

        # Volume confirmation
        volume_trend = market_structure['volume_analysis'].get('volume_trend', 0)

        # Calculate composite score
        sentiment_score = (
            trend_strength * trend_direction * 0.4 +
            (range_position - 0.5) * 2 * 0.3 +  # Center at 0.5
            price_bias * 0.2 +
            volume_trend * 0.1
        )

        # Normalize to -1 to +1
        sentiment_score = max(-1, min(1, sentiment_score))

        return {
            'score': float(sentiment_score),
            'bias': 'bullish' if sentiment_score > 0.1 else 'bearish' if sentiment_score < -0.1 else 'neutral',
            'strength': abs(sentiment_score)
        }

    def _assess_data_quality(self, data: pd.DataFrame) -> Dict:
        """Assess quality of market data"""
        if data.empty:
            return {'quality': 'poor', 'score': 0}

        checks = {
            'sufficient_data': len(data) >= 10,
            'no_nan_values': not data[['Open', 'High', 'Low', 'Close']].isnull().any().any(),
            'price_consistency': (data['High'] >= data['Low']).all(),
            'volume_present': 'Volume' not in data.columns or (data['Volume'] > 0).all(),
            'no_extreme_moves': data['Close'].pct_change().abs().max() < 0.5  # No 50% moves
        }

        quality_score = sum(checks.values()) / len(checks)

        return {
            'quality': 'excellent' if quality_score > 0.8 else 'good' if quality_score > 0.6 else 'fair',
            'score': float(quality_score),
            'checks_passed': sum(checks.values()),
            'total_checks': len(checks)
        }

    # Keep your existing methods for the other functionality...
    def _determine_market_phase(self, data: pd.DataFrame) -> MarketPhase:
        """Your existing implementation"""
        if len(data) < 10:
            return MarketPhase.CONSOLIDATION

        recent_close = data['Close'].iloc[-1]
        old_close = data['Close'].iloc[-10]
        momentum = (recent_close - old_close) / old_close

        returns = data['Close'].pct_change().dropna()
        volatility = returns.std()

        volume_trend = data['Volume'].rolling(5).mean().iloc[-1] / data['Volume'].rolling(10).mean().iloc[-1]

        if abs(momentum) > 0.05 and volume_trend > 1.2:
            return MarketPhase.TREND
        elif volatility < 0.02 and abs(momentum) < 0.02:
            return MarketPhase.CONSOLIDATION
        elif volume_trend > 1.5:
            return MarketPhase.ACCUMULATION if momentum > 0 else MarketPhase.DISTRIBUTION
        else:
            return MarketPhase.CONSOLIDATION

    def _calculate_volatility(self, data: pd.DataFrame) -> float:
        """Your existing implementation"""
        returns = data['Close'].pct_change().dropna()
        return float(returns.std() * np.sqrt(252))

    def _analyze_trend(self, data: pd.DataFrame) -> Dict:
        """Your existing implementation"""
        if len(data) < 20:
            return {'direction': 'neutral', 'strength': 0.5}

        sma_20 = data['Close'].rolling(20).mean().iloc[-1]
        sma_50 = data['Close'].rolling(min(50, len(data))).mean().iloc[-1]
        current_price = data['Close'].iloc[-1]

        if current_price > sma_20 > sma_50:
            direction = 'bullish'
        elif current_price < sma_20 < sma_50:
            direction = 'bearish'
        else:
            direction = 'neutral'

        price_vs_sma20 = abs(current_price - sma_20) / sma_20
        strength = min(price_vs_sma20 * 10, 1.0)

        return {
            'direction': direction,
            'strength': strength,
            'sma_20': float(sma_20),
            'sma_50': float(sma_50)
        }

    def _generate_daily_profiles(self, data: pd.DataFrame) -> List[Dict]:
        """Your existing implementation"""
        profiles = []
        for i, (date, row) in enumerate(data.iterrows()):
            range_size = row['High'] - row['Low']
            body_size = abs(row['Close'] - row['Open'])
            upper_wick = row['High'] - max(row['Open'], row['Close'])
            lower_wick = min(row['Open'], row['Close']) - row['Low']

            profile_type = self._classify_candle_pattern(row)
            market_phase = self._determine_daily_phase(row, data, i)

            profiles.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']),
                'range_size': float(range_size),
                'body_size': float(body_size),
                'upper_wick': float(upper_wick),
                'lower_wick': float(lower_wick),
                'profile_type': profile_type,
                'market_phase': market_phase.value,
                'body_percentage': float(body_size / range_size) if range_size > 0 else 0
            })
        return profiles

    def _classify_candle_pattern(self, row: pd.Series) -> str:
        """Your existing implementation"""
        open_price = row['Open']
        close = row['Close']
        high = row['High']
        low = row['Low']

        body_size = abs(close - open_price)
        range_size = high - low
        body_percentage = body_size / range_size if range_size > 0 else 0

        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low

        if body_percentage < 0.1:
            return "Doji"
        elif body_percentage > 0.8:
            if close > open_price:
                return "Strong Bullish"
            else:
                return "Strong Bearish"
        elif close > open_price:
            if upper_wick > body_size * 2:
                return "Hammer"
            else:
                return "Bullish"
        else:
            if lower_wick > body_size * 2:
                return "Shooting Star"
            else:
                return "Bearish"

    def _determine_daily_phase(self, row: pd.Series, data: pd.DataFrame, index: int) -> MarketPhase:
        """Your existing implementation"""
        if index < 5:
            return MarketPhase.CONSOLIDATION

        recent_data = data.iloc[max(0, index-5):index+1]
        price_change = (row['Close'] - recent_data['Close'].iloc[0]) / recent_data['Close'].iloc[0]
        volume_ratio = row['Volume'] / recent_data['Volume'].mean()

        if abs(price_change) > 0.03 and volume_ratio > 1.5:
            return MarketPhase.TREND
        elif volume_ratio > 2.0:
            return MarketPhase.ACCUMULATION if price_change > 0 else MarketPhase.DISTRIBUTION
        else:
            return MarketPhase.CONSOLIDATION

    def _generate_weekly_narrative(self, market_structure: Dict, daily_profiles: List[Dict], symbol_info: Dict) -> str:
        """Enhanced narrative with symbol context"""
        if not market_structure or not daily_profiles:
            return "Insufficient data for analysis"

        # Your existing narrative logic, enhanced with symbol context
        symbol_name = symbol_info.get('name', symbol_info['symbol'])

        current_price = market_structure['current_price']
        market_phase = market_structure['market_phase']
        trend = market_structure['trend']
        sentiment = market_structure.get('sentiment', {'bias': 'neutral'})

        narrative_parts = [f"{symbol_name} is currently in a {market_phase} phase."]

        # Add trend information
        if trend['direction'] != 'neutral':
            narrative_parts.append(f"The {trend['direction']} trend shows {trend['strength']:.1%} strength.")

        # Add sentiment context
        if sentiment['bias'] != 'neutral':
            narrative_parts.append(f"Market sentiment is {sentiment['bias']} with {sentiment.get('strength', 0.5):.1%} conviction.")

        # Add your existing range and level analysis
        range_position = market_structure['range_percentage']
        if range_position > 80:
            narrative_parts.append(f"Trading near weekly highs at {range_position:.1f}% of the range.")
        elif range_position < 20:
            narrative_parts.append(f"Near weekly lows at {range_position:.1f}% of the range.")

        return " ".join(narrative_parts)

    def _generate_trading_insights(self, market_structure: Dict, daily_profiles: List[Dict], symbol_info: Dict) -> List[str]:
        """Enhanced insights with symbol-specific context"""
        insights = []

        if not market_structure:
            return ["Insufficient data for trading insights"]

        # Your existing insight generation logic
        current_price = market_structure['current_price']
        market_phase = market_structure['market_phase']
        trend = market_structure['trend']
        key_levels = market_structure.get('key_levels', [])
        symbol_type = symbol_info.get('type', 'unknown')

        # Symbol-type specific insights
        if symbol_type == 'future':
            insights.append("Futures contract - monitor roll dates and contract specifications")
        elif symbol_type == 'forex':
            insights.append("Forex pair - consider correlation with related currency pairs")
        elif symbol_type == 'crypto':
            insights.append("Cryptocurrency - higher volatility expected, use appropriate position sizing")

        # Add your existing trend, phase, and level insights
        if trend['direction'] == 'bullish' and trend['strength'] > 0.7:
            insights.append("Strong bullish trend - consider long positions on pullbacks to support")
        elif trend['direction'] == 'bearish' and trend['strength'] > 0.7:
            insights.append("Strong bearish trend - consider short positions on rallies to resistance")

        if market_phase == 'accumulation':
            insights.append("Accumulation phase - watch for breakout above resistance levels")
        elif market_phase == 'distribution':
            insights.append("Distribution phase - be cautious of breakdown below support levels")

        # Key levels insights
        nearby_levels = [level for level in key_levels if abs(level['price'] - current_price) / current_price < 0.05]
        if nearby_levels:
            support_levels = [l for l in nearby_levels if l['type'] == 'support']
            resistance_levels = [l for l in nearby_levels if l['type'] == 'resistance']

            if support_levels:
                strongest_support = max(support_levels, key=lambda x: x['strength'])
                insights.append(f"Strong support at ${strongest_support['price']:.2f} - watch for bounce")

            if resistance_levels:
                strongest_resistance = max(resistance_levels, key=lambda x: x['strength'])
                insights.append(f"Strong resistance at ${strongest_resistance['price']:.2f} - watch for rejection")

        return insights

    def _predict_next_week(self, data: pd.DataFrame, market_structure: Dict, symbol_info: Dict) -> Dict:
        """Enhanced prediction with symbol context"""
        if len(data) < 10:
            return {"confidence": 0.0, "prediction": "Insufficient data"}

        # Your existing prediction logic
        recent_returns = data['Close'].pct_change().dropna().tail(5)
        momentum = recent_returns.mean()
        volatility = recent_returns.std()

        sma_short = data['Close'].rolling(5).mean().iloc[-1]
        sma_long = data['Close'].rolling(10).mean().iloc[-1]
        trend_strength = (sma_short - sma_long) / sma_long

        current_price = data['Close'].iloc[-1]
        weekly_range = market_structure['weekly_range']

        # Bullish scenario
        bullish_target = current_price * (1 + abs(momentum) + volatility)
        bullish_probability = max(0.1, 0.3 + momentum * 2)

        # Bearish scenario
        bearish_target = current_price * (1 - abs(momentum) - volatility)
        bearish_probability = max(0.1, 0.3 - momentum * 2)

        # Neutral scenario
        neutral_probability = 1 - bullish_probability - bearish_probability

        confidence = min(0.8, 0.4 + abs(trend_strength) + (1 - volatility))

        return {
            "confidence": confidence,
            "scenarios": [
                {
                    "type": "bullish",
                    "probability": bullish_probability,
                    "target": bullish_target,
                    "description": "Continuation of upward momentum"
                },
                {
                    "type": "bearish",
                    "probability": bearish_probability,
                    "target": bearish_target,
                    "description": "Reversal of recent trend"
                },
                {
                    "type": "neutral",
                    "probability": neutral_probability,
                    "target": current_price,
                    "description": "Range-bound consolidation"
                }
            ],
            "key_levels": {
                "resistance": current_price + weekly_range * 0.5,
                "support": current_price - weekly_range * 0.5
            }
        }

    def _calculate_confidence(self, data: pd.DataFrame) -> float:
        """Your existing implementation"""
        if data.empty:
            return 0.0

        completeness = len(data) / 20
        price_consistency = 1.0 - data['Close'].pct_change().abs().mean()
        volume_consistency = 1.0 - (data['Volume'].pct_change().abs().mean() / 2)

        confidence = (completeness + price_consistency + volume_consistency) / 3
        return min(confidence, 1.0)

    def _create_error_response(self, message: str) -> Dict:
        """Your existing implementation"""
        return {
            'status': 'error',
            'error': message,
            'timestamp': datetime.now().isoformat()
        }

# Initialize analyzer
analyzer = AIWeeklyAnalyzer()

# Enhanced Routes
@ai_weekly_bp.route('/analyze/<symbol>')
def analyze_symbol(symbol: str):
    """Analyze a single symbol"""
    weeks_back = request.args.get('weeks', 4, type=int)
    return jsonify(analyzer.analyze_symbol(symbol, weeks_back))

@ai_weekly_bp.route('/compare')
def compare_symbols():
    """Compare multiple symbols"""
    symbols = request.args.get('symbols', '').split(',')
    if not symbols or symbols == ['']:
        return jsonify({'error': 'No symbols provided'})

    results = {}
    for symbol in symbols:
        if symbol.strip():
            results[symbol.strip()] = analyzer.analyze_symbol(symbol.strip())

    return jsonify({
        'status': 'success',
        'comparisons': results,
        'timestamp': datetime.now().isoformat()
    })

@ai_weekly_bp.route('/symbols')
def get_symbols():
    """Get available symbols"""
    return jsonify({
        'status': 'success',
        'symbols': analyzer.get_available_symbols(),
        'timestamp': datetime.now().isoformat()
    })

@ai_weekly_bp.route('/symbol/<symbol>')
def get_symbol_info(symbol: str):
    """Get symbol information"""
    return jsonify({
        'status': 'success',
        'symbol_info': analyzer.get_symbol_info(symbol),
        'timestamp': datetime.now().isoformat()
    })

@ai_weekly_bp.route('/dashboard')
def dashboard():
    """Render the AI weekly dashboard"""
    symbols = ALL_SYMBOLS
    return render_template('ai_weekly_dashboard.html', symbols=symbols)

@ai_weekly_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'analyzer': 'AI Weekly Analysis v2.0',
        'symbols_available': len(ALL_SYMBOLS),
        'categories': list(SYMBOL_UNIVERSE.keys())
    })
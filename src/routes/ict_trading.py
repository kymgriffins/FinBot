from flask import Blueprint, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import sqlite3
import json
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

ict_trading_bp = Blueprint('ict_trading', __name__)

# ICT Configuration
class ICTMarketHours(Enum):
    LONDON_OPEN = "02:00"
    NY_OPEN = "09:30"
    NY_MID = "10:00"
    NY_CLOSE = "16:00"
    ASIA_OPEN = "19:00"

@dataclass
class ICTLevel:
    level_type: str
    price: float
    strength: float
    timeframe: str
    session: str
    description: str

class ICTMarketAnalyzer:
    def __init__(self, db_path='ict_trading_journal.db'):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_profiles (
                symbol TEXT,
                date TEXT,
                session TEXT,
                high REAL,
                low REAL,
                open REAL,
                close REAL,
                volume INTEGER,
                premium_levels TEXT,
                discount_levels TEXT,
                fvg_levels TEXT,
                liquidity_levels TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, date, session)
            )
        ''')

        conn.commit()
        conn.close()

    def analyze_daily_profile(self, symbol: str, date: datetime = None):
        if date is None:
            date = datetime.now()

        try:
            start_date = date - timedelta(days=5)
            end_date = date + timedelta(days=1)

            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval='1d')

            if data.empty:
                return {"error": "No data available"}

            target_data = data[data.index.date == date.date()]
            if target_data.empty:
                return {"error": "No data for target date"}

            daily_high = float(target_data['High'].iloc[0])
            daily_low = float(target_data['Low'].iloc[0])
            daily_open = float(target_data['Open'].iloc[0])
            daily_close = float(target_data['Close'].iloc[0])
            daily_range = daily_high - daily_low

            premium_levels = self._calculate_premium_levels(daily_high, daily_low, daily_open)
            discount_levels = self._calculate_discount_levels(daily_high, daily_low, daily_open)
            fvg_levels = self._find_fair_value_gaps(data, date)
            liquidity_levels = self._find_liquidity_levels(data, date)

            return {
                'symbol': symbol,
                'date': date.strftime('%Y-%m-%d'),
                'daily_high': daily_high,
                'daily_low': daily_low,
                'daily_open': daily_open,
                'daily_close': daily_close,
                'daily_range': daily_range,
                'premium_levels': [asdict(level) for level in premium_levels],
                'discount_levels': [asdict(level) for level in discount_levels],
                'fvg_levels': [asdict(level) for level in fvg_levels],
                'liquidity_levels': [asdict(level) for level in liquidity_levels],
                'market_condition': self._determine_market_condition(daily_open, daily_close, daily_high, daily_low)
            }

        except Exception as e:
            logger.error(f"Error analyzing daily profile for {symbol}: {e}")
            return {"error": str(e)}

    def _calculate_premium_levels(self, high: float, low: float, open_price: float):
        daily_range = high - low
        levels = []

        premium_zones = [
            (0.236, 'Minor Premium'),
            (0.382, 'Moderate Premium'),
            (0.618, 'Major Premium'),
            (0.786, 'Extreme Premium')
        ]

        for ratio, description in premium_zones:
            level_price = open_price + (daily_range * ratio)
            if level_price <= high:
                levels.append(ICTLevel(
                    level_type='premium',
                    price=round(level_price, 4),
                    strength=ratio,
                    timeframe='D1',
                    session='NY',
                    description=description
                ))

        return levels

    def _calculate_discount_levels(self, high: float, low: float, open_price: float):
        daily_range = high - low
        levels = []

        discount_zones = [
            (0.236, 'Minor Discount'),
            (0.382, 'Moderate Discount'),
            (0.618, 'Major Discount'),
            (0.786, 'Extreme Discount')
        ]

        for ratio, description in discount_zones:
            level_price = open_price - (daily_range * ratio)
            if level_price >= low:
                levels.append(ICTLevel(
                    level_type='discount',
                    price=round(level_price, 4),
                    strength=ratio,
                    timeframe='D1',
                    session='NY',
                    description=description
                ))

        return levels

    def _find_fair_value_gaps(self, data, target_date):
        fvg_levels = []

        for i in range(1, len(data)):
            prev_high = data['High'].iloc[i-1]
            prev_low = data['Low'].iloc[i-1]
            curr_high = data['High'].iloc[i]
            curr_low = data['Low'].iloc[i]

            if curr_low > prev_high:
                fvg_levels.append(ICTLevel(
                    level_type='fvg_bullish',
                    price=round((prev_high + curr_low) / 2, 4),
                    strength=0.7,
                    timeframe='H1',
                    session='Auto',
                    description=f'Bullish FVG: {prev_high} - {curr_low}'
                ))

            elif curr_high < prev_low:
                fvg_levels.append(ICTLevel(
                    level_type='fvg_bearish',
                    price=round((curr_high + prev_low) / 2, 4),
                    strength=0.7,
                    timeframe='H1',
                    session='Auto',
                    description=f'Bearish FVG: {curr_high} - {prev_low}'
                ))

        return fvg_levels

    def _find_liquidity_levels(self, data, target_date):
        liquidity_levels = []

        recent_highs = data['High'].tail(10).nlargest(3)
        for level in recent_highs:
            liquidity_levels.append(ICTLevel(
                level_type='liquidity_high',
                price=round(level, 4),
                strength=0.8,
                timeframe='D1',
                session='All',
                description='Recent High Liquidity'
            ))

        recent_lows = data['Low'].tail(10).nsmallest(3)
        for level in recent_lows:
            liquidity_levels.append(ICTLevel(
                level_type='liquidity_low',
                price=round(level, 4),
                strength=0.8,
                timeframe='D1',
                session='All',
                description='Recent Low Liquidity'
            ))

        return liquidity_levels

    def _determine_market_condition(self, open_price: float, close_price: float, high: float, low: float) -> str:
        body_size = abs(close_price - open_price)
        total_range = high - low

        if body_size / total_range < 0.3:
            return "Consolidation"
        elif close_price > open_price:
            return "Bullish"
        else:
            return "Bearish"

# Initialize analyzer
ict_analyzer = ICTMarketAnalyzer()

# ICT Trading Routes
@ict_trading_bp.route('/dashboard')
def ict_dashboard():
    """Main ICT Trading Dashboard"""
    symbols = ['ES=F', 'NQ=F', 'YM=F', 'CL=F', 'GC=F', 'EURUSD=X']
    return jsonify({
        'status': 'success',
        'symbols': symbols,
        'message': 'ICT Trading Dashboard'
    })

@ict_trading_bp.route('/analyze/<symbol>')
def analyze_symbol(symbol: str):
    """Analyze symbol with ICT methodology"""
    date_str = request.args.get('date')
    date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.now()

    analysis = ict_analyzer.analyze_daily_profile(symbol, date)
    return jsonify(analysis)

@ict_trading_bp.route('/levels/<symbol>')
def get_ict_levels(symbol: str):
    """Get ICT levels for symbol"""
    date_str = request.args.get('date')
    date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.now()

    analysis = ict_analyzer.analyze_daily_profile(symbol, date)

    levels = {
        'premium_levels': analysis.get('premium_levels', []),
        'discount_levels': analysis.get('discount_levels', []),
        'fvg_levels': analysis.get('fvg_levels', []),
        'liquidity_levels': analysis.get('liquidity_levels', [])
    }

    return jsonify(levels)

@ict_trading_bp.route('/market/analysis')
def market_analysis():
    """Get market analysis for multiple symbols"""
    symbols = request.args.get('symbols', 'ES=F,NQ=F,CL=F').split(',')
    analyses = {}

    for symbol in symbols:
        if symbol.strip():
            analysis = ict_analyzer.analyze_daily_profile(symbol.strip())
            analyses[symbol.strip()] = analysis

    return jsonify(analyses)

@ict_trading_bp.route('/health')
def ict_health():
    """ICT System Health Check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'ICT Market Analyzer',
        'version': '1.0.0'
    })
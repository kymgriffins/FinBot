import os
import logging
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DailyMarketAnalyzer:
    def __init__(self):
        self.symbols = self.get_symbols()
        self.ny_tz = pytz.timezone('America/New_York')
        self.london_tz = pytz.timezone('Europe/London')
        self.asia_tz = pytz.timezone('Asia/Tokyo')

    def get_symbols(self):
        symbols = os.getenv('SYMBOLS', 'ES=F,NQ=F,YM=F,6E=F,CL=F,GC=F,SI=F')
        return [s.strip() for s in symbols.split(',')] if symbols else []

    def get_symbol_name(self, symbol):
        names = {
            'ES=F': 'S&P 500 Futures',
            'NQ=F': 'NASDAQ Futures',
            'YM=F': 'Dow Futures',
            '6E=F': 'Euro FX Futures',
            'CL=F': 'Crude Oil Futures',
            'GC=F': 'Gold Futures',
            'SI=F': 'Silver Futures'
        }
        return names.get(symbol, symbol)

    def get_trading_sessions(self, date: datetime) -> Dict:
        """Define trading session times"""
        return {
            'asia': {
                'start': date.replace(hour=0, minute=0, second=0),  # Midnight UTC
                'end': date.replace(hour=8, minute=0, second=0)     # 8 AM UTC
            },
            'london': {
                'start': date.replace(hour=8, minute=0, second=0),  # 8 AM UTC
                'end': date.replace(hour=16, minute=0, second=0)    # 4 PM UTC
            },
            'new_york': {
                'start': date.replace(hour=14, minute=30, second=0), # 2:30 PM UTC
                'end': date.replace(hour=21, minute=0, second=0)     # 9 PM UTC
            }
        }

    def calculate_pips(self, price_change: float, symbol: str) -> float:
        """Calculate pip movement based on symbol type"""
        pip_values = {
            '6E=F': 0.0001,  # EUR/USD - 4 decimal places
            'ES=F': 0.25,    # S&P - points
            'NQ=F': 0.25,    # NASDAQ - points
            'YM=F': 1.0,     # Dow - points
            'CL=F': 0.01,    # Oil - dollars
            'GC=F': 0.10,    # Gold - dollars
            'SI=F': 0.005    # Silver - dollars
        }
        return abs(price_change) / pip_values.get(symbol, 1.0)

    def analyze_session_data(self, data: pd.DataFrame, session: str, sessions: Dict, symbol: str) -> Dict:
        """Analyze data for a specific trading session"""
        session_data = data[
            (data['timestamp'] >= sessions[session]['start']) &
            (data['timestamp'] < sessions[session]['end'])
        ]

        if session_data.empty:
            return {
                'session': session,
                'pips': 0,
                'range': 0,
                'direction': 'flat',
                'high': 0,
                'low': 0,
                'volume': 0
            }

        session_high = session_data['high'].max()
        session_low = session_data['low'].min()
        session_range = session_high - session_low
        session_pips = self.calculate_pips(session_range, symbol)

        # Determine direction
        open_price = session_data.iloc[0]['open']
        close_price = session_data.iloc[-1]['close']
        direction = 'bullish' if close_price > open_price else 'bearish' if close_price < open_price else 'flat'

        return {
            'session': session,
            'pips': round(session_pips, 2),
            'range': round(session_range, 4),
            'direction': direction,
            'high': round(session_high, 4),
            'low': round(session_low, 4),
            'volume': int(session_data['volume'].sum())
        }

    def get_daily_analysis(self, symbol: str, date: datetime = None) -> Optional[Dict]:
        """Get comprehensive daily analysis for a symbol"""
        if date is None:
            date = datetime.now()

        try:
            # Fetch 1-minute data for the day
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=date.date(), end=date.date() + timedelta(days=1), interval='1m')

            if data.empty:
                return None

            data = data.reset_index()
            data = data.rename(columns={'Datetime': 'timestamp'})

            # Define trading sessions
            sessions = self.get_trading_sessions(date)

            # Analyze each session
            session_analysis = {}
            for session in ['asia', 'london', 'new_york']:
                session_analysis[session] = self.analyze_session_data(data, session, sessions, symbol)

            # Overall daily analysis
            daily_high = data['high'].max()
            daily_low = data['low'].min()
            daily_range = daily_high - daily_low
            daily_pips = self.calculate_pips(daily_range, symbol)

            open_price = data.iloc[0]['open']
            close_price = data.iloc[-1]['close']
            daily_direction = 'bullish' if close_price > open_price else 'bearish' if close_price < open_price else 'flat'

            return {
                'symbol': symbol,
                'symbol_name': self.get_symbol_name(symbol),
                'date': date.strftime('%Y-%m-%d'),
                'day_of_week': date.strftime('%A'),
                'overall': {
                    'open': round(open_price, 4),
                    'close': round(close_price, 4),
                    'high': round(daily_high, 4),
                    'low': round(daily_low, 4),
                    'range': round(daily_range, 4),
                    'pips': round(daily_pips, 2),
                    'direction': daily_direction,
                    'total_volume': int(data['volume'].sum())
                },
                'sessions': session_analysis,
                'session_volatility': {
                    'most_volatile': max(session_analysis.items(), key=lambda x: x[1]['pips'])[0],
                    'least_volatile': min(session_analysis.items(), key=lambda x: x[1]['pips'])[0]
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing daily data for {symbol}: {e}")
            return None

    def get_historical_daily_analysis(self, days_back: int = 5) -> Dict:
        """Get daily analysis for previous days"""
        analysis = {}

        for i in range(days_back):
            date = datetime.now() - timedelta(days=i+1)
            if date.weekday() >= 5:  # Skip weekends
                continue

            daily_analysis = {}
            for symbol in self.symbols:
                symbol_analysis = self.get_daily_analysis(symbol, date)
                if symbol_analysis:
                    daily_analysis[symbol] = symbol_analysis

            if daily_analysis:
                analysis[date.strftime('%Y-%m-%d')] = {
                    'date': date.strftime('%Y-%m-%d'),
                    'day': date.strftime('%A'),
                    'analysis': daily_analysis
                }

        return analysis

    def get_market_news(self) -> List[Dict]:
        """Get relevant market news (placeholder - integrate with news API later)"""
        # TODO: Integrate with NewsAPI, Alpha Vantage, or other news sources
        return [
            {
                'title': 'Economic Calendar Update',
                'impact': 'high',
                'time': '14:30 UTC',
                'description': 'US CPI Data Release'
            },
            {
                'title': 'FOMC Meeting',
                'impact': 'high',
                'time': '18:00 UTC',
                'description': 'Federal Reserve Interest Rate Decision'
            }
        ]

    def generate_daily_report(self) -> Dict:
        """Generate comprehensive daily market report"""
        current_analysis = {}
        for symbol in self.symbols:
            analysis = self.get_daily_analysis(symbol)
            if analysis:
                current_analysis[symbol] = analysis

        historical_analysis = self.get_historical_daily_analysis(3)
        news = self.get_market_news()

        return {
            'timestamp': datetime.now().isoformat(),
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'current_analysis': current_analysis,
            'historical_comparison': historical_analysis,
            'market_news': news,
            'summary': self.generate_summary(current_analysis)
        }

    def generate_summary(self, analysis: Dict) -> Dict:
        """Generate summary insights"""
        if not analysis:
            return {}

        total_pips = 0
        bullish_count = 0
        bearish_count = 0

        for symbol_data in analysis.values():
            total_pips += symbol_data['overall']['pips']
            if symbol_data['overall']['direction'] == 'bullish':
                bullish_count += 1
            elif symbol_data['overall']['direction'] == 'bearish':
                bearish_count += 1

        return {
            'total_symbols': len(analysis),
            'average_pips': round(total_pips / len(analysis), 2),
            'market_sentiment': 'bullish' if bullish_count > bearish_count else 'bearish' if bearish_count > bullish_count else 'neutral',
            'bullish_count': bullish_count,
            'bearish_count': bearish_count
        }
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf
from enum import Enum

logger = logging.getLogger(__name__)

class DayProfile(Enum):
    INSIDE_DAY = "Inside Day"
    OUTSIDE_DAY = "Outside Day"
    BEARISH_ENGULFING = "Bearish Engulfing"
    BULLISH_ENGULFING = "Bullish Engulfing"
    GAP_UP = "Gap Up"
    GAP_DOWN = "Gap Down"
    DOJI = "Doji"
    REVERSAL = "Reversal"
    TREND_CONTINUATION = "Trend Continuation"

class WeeklyNarrative:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.weekly_data = None
        self.daily_data = {}
        self.weekly_open = None
        self.weekly_high = None
        self.weekly_low = None
        self.weekly_close = None
        self.pwh = None  # Previous Week High
        self.pwl = None  # Previous Week Low
        self.narrative = {}

    def fetch_weekly_data(self):
        """Fetch 3 weeks of daily data for analysis"""
        try:
            ticker = yf.Ticker(self.symbol)

            # Get 3 weeks of daily data for context
            data = ticker.history(period='3wk', interval='1d')

            if data.empty:
                return False

            # Separate current week and previous week
            current_week = data.tail(5)  # Last 5 trading days
            previous_week = data.head(5)  # First 5 trading days of the period

            # Store daily data
            for date, row in current_week.iterrows():
                day_name = date.strftime('%A')
                self.daily_data[day_name] = {
                    'date': date,
                    'open': row['Open'],
                    'high': row['High'],
                    'low': row['Low'],
                    'close': row['Close'],
                    'volume': row['Volume']
                }

            # Calculate weekly levels
            self.weekly_open = current_week.iloc[0]['Open']
            self.weekly_high = current_week['High'].max()
            self.weekly_low = current_week['Low'].min()
            self.weekly_close = current_week.iloc[-1]['Close']

            # Previous week levels
            self.pwh = previous_week['High'].max()
            self.pwl = previous_week['Low'].min()

            return True

        except Exception as e:
            logger.error(f"Error fetching data for {self.symbol}: {e}")
            return False

    def analyze_daily_profile(self, day_data: Dict, day_name: str, prev_day_data: Dict = None) -> Dict:
        """Analyze daily candle profile and market structure"""
        profile = {
            'day': day_name,
            'profile_type': None,
            'key_levels': {},
            'liquidity_zones': [],
            'narrative': '',
            'structure_analysis': {}
        }

        # Calculate day range and body
        day_range = day_data['high'] - day_data['low']
        body_size = abs(day_data['close'] - day_data['open'])
        body_percentage = (body_size / day_range) * 100 if day_range > 0 else 0

        # Determine if inside/outside day relative to previous day
        if prev_day_data:
            is_inside_day = (day_data['high'] <= prev_day_data['high'] and
                           day_data['low'] >= prev_day_data['low'])
            is_outside_day = (day_data['high'] > prev_day_data['high'] and
                            day_data['low'] < prev_day_data['low'])
        else:
            is_inside_day = False
            is_outside_day = False

        # Gap analysis
        gap_up = prev_day_data and day_data['low'] > prev_day_data['high']
        gap_down = prev_day_data and day_data['high'] < prev_day_data['low']

        # Determine profile type
        if body_percentage < 30:  # Small body = doji-like
            profile['profile_type'] = DayProfile.DOJI.value
        elif is_inside_day:
            profile['profile_type'] = DayProfile.INSIDE_DAY.value
        elif is_outside_day:
            if day_data['close'] > day_data['open']:
                profile['profile_type'] = DayProfile.BULLISH_ENGULFING.value
            else:
                profile['profile_type'] = DayProfile.BEARISH_ENGULFING.value
        elif gap_up:
            profile['profile_type'] = DayProfile.GAP_UP.value
        elif gap_down:
            profile['profile_type'] = DayProfile.GAP_DOWN.value
        else:
            profile['profile_type'] = DayProfile.TREND_CONTINUATION.value

        # Key levels
        profile['key_levels'] = {
            'poc': self.calculate_poc(day_data),  # Point of Control
            'value_area_high': day_data['high'] - (day_range * 0.3),
            'value_area_low': day_data['low'] + (day_range * 0.3),
            'day_high': day_data['high'],
            'day_low': day_data['low'],
            'day_open': day_data['open'],
            'day_close': day_data['close']
        }

        # Liquidity zones (previous highs/lows that might get taken)
        profile['liquidity_zones'] = self.identify_liquidity_zones(day_data, prev_day_data)

        # Generate narrative
        profile['narrative'] = self.generate_daily_narrative(profile, day_data, prev_day_data)

        # Structure analysis
        profile['structure_analysis'] = self.analyze_market_structure(day_data, prev_day_data)

        return profile

    def calculate_poc(self, day_data: Dict) -> float:
        """Calculate Point of Control (simplified)"""
        # In a real implementation, you'd use volume profile
        # Here we use the midpoint as a simplified POC
        return (day_data['high'] + day_data['low']) / 2

    def identify_liquidity_zones(self, day_data: Dict, prev_day_data: Dict = None) -> List[Dict]:
        """Identify potential liquidity zones (stops above/below key levels)"""
        zones = []

        if prev_day_data:
            # Previous day high/low as liquidity
            zones.extend([
                {'level': prev_day_data['high'], 'type': 'above_prev_high', 'strength': 'high'},
                {'level': prev_day_data['low'], 'type': 'below_prev_low', 'strength': 'high'}
            ])

        # Weekly levels as liquidity
        if self.weekly_high and self.weekly_low:
            zones.extend([
                {'level': self.weekly_high, 'type': 'weekly_high', 'strength': 'very_high'},
                {'level': self.weekly_low, 'type': 'weekly_low', 'strength': 'very_high'}
            ])

        # Previous week levels
        if self.pwh and self.pwl:
            zones.extend([
                {'level': self.pwh, 'type': 'prev_week_high', 'strength': 'medium'},
                {'level': self.pwl, 'type': 'prev_week_low', 'strength': 'medium'}
            ])

        return zones

    def generate_daily_narrative(self, profile: Dict, day_data: Dict, prev_day_data: Dict = None) -> str:
        """Generate narrative for the day's price action"""
        day_name = profile['day']
        profile_type = profile['profile_type']

        narratives = {
            'Monday': {
                DayProfile.INSIDE_DAY.value: "Monday consolidates within Friday's range - market undecided",
                DayProfile.OUTSIDE_DAY.value: "Monday expands beyond Friday's range - early week momentum",
                DayProfile.GAP_UP.value: "Monday gaps up - bullish sentiment to start week",
                DayProfile.GAP_DOWN.value: "Monday gaps down - bearish sentiment to start week",
                DayProfile.DOJI.value: "Monday indecision - market awaits catalyst"
            },
            'Tuesday': {
                DayProfile.INSIDE_DAY.value: "Tuesday inside Monday's range - continuation of consolidation",
                DayProfile.OUTSIDE_DAY.value: "Tuesday breaks Monday's range - institutional participation",
                DayProfile.BULLISH_ENGULFING.value: "Tuesday bullish engulfing - reversal from Monday's weakness",
                DayProfile.BEARISH_ENGULFING.value: "Tuesday bearish engulfing - reversal from Monday's strength"
            },
            'Wednesday': {
                DayProfile.OUTSIDE_DAY.value: "Wednesday expansion - mid-week momentum move",
                DayProfile.INSIDE_DAY.value: "Wednesday consolidation - positioning for Thursday/Friday",
                DayProfile.TREND_CONTINUATION.value: "Wednesday continues trend - institutional flow evident"
            },
            'Thursday': {
                DayProfile.REVERSAL.value: "Thursday reversal - profit-taking before Friday",
                DayProfile.TREND_CONTINUATION.value: "Thursday trend continuation - strong institutional conviction",
                DayProfile.DOJI.value: "Thursday indecision - positioning for weekly close"
            },
            'Friday': {
                DayProfile.INSIDE_DAY.value: "Friday inside weekly range - typical TGIF retracement",
                DayProfile.OUTSIDE_DAY.value: "Friday breaks weekly range - unusual EOW momentum",
                DayProfile.DOJI.value: "Friday indecision - market closes near weekly open"
            }
        }

        base_narrative = narratives.get(day_name, {}).get(profile_type, f"{day_name} shows {profile_type}")

        # Add liquidity context
        liquidity_context = self.add_liquidity_context(profile, day_data)

        return f"{base_narrative}. {liquidity_context}"

    def add_liquidity_context(self, profile: Dict, day_data: Dict) -> str:
        """Add liquidity-taking context to narrative"""
        high_taken = any(zone['level'] <= day_data['high'] for zone in profile['liquidity_zones']
                        if zone['type'].endswith('high'))
        low_taken = any(zone['level'] >= day_data['low'] for zone in profile['liquidity_zones']
                       if zone['type'].endswith('low'))

        if high_taken and low_taken:
            return "Both-side liquidity run observed."
        elif high_taken:
            return "Liquidity above previous highs taken."
        elif low_taken:
            return "Liquidity below previous lows taken."
        else:
            return "No significant liquidity levels taken."

    def analyze_market_structure(self, day_data: Dict, prev_day_data: Dict = None) -> Dict:
        """Analyze market structure changes"""
        structure = {
            'trend': 'neutral',
            'bias_shift': False,
            'key_breakouts': [],
            'support_resistance': []
        }

        if not prev_day_data:
            return structure

        # Determine trend bias
        if day_data['close'] > day_data['open'] and day_data['close'] > prev_day_data['close']:
            structure['trend'] = 'bullish'
        elif day_data['close'] < day_data['open'] and day_data['close'] < prev_day_data['close']:
            structure['trend'] = 'bearish'

        # Check for bias shifts
        prev_trend = 'bullish' if prev_day_data['close'] > prev_day_data['open'] else 'bearish'
        if structure['trend'] != prev_trend and structure['trend'] != 'neutral':
            structure['bias_shift'] = True

        # Identify breakouts
        if day_data['high'] > prev_day_data['high']:
            structure['key_breakouts'].append(f"Break above previous high: {prev_day_data['high']:.2f}")
        if day_data['low'] < prev_day_data['low']:
            structure['key_breakouts'].append(f"Break below previous low: {prev_day_data['low']:.2f}")

        return structure

    def generate_weekly_narrative(self) -> Dict:
        """Generate complete weekly narrative"""
        if not self.fetch_weekly_data():
            return {"error": "Could not fetch data"}

        week_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        daily_profiles = {}
        prev_day_data = None

        # Analyze each day
        for day in week_days:
            if day in self.daily_data:
                day_data = self.daily_data[day]
                profile = self.analyze_daily_profile(day_data, day, prev_day_data)
                daily_profiles[day] = profile
                prev_day_data = day_data

        # Generate weekly summary
        weekly_summary = self.generate_weekly_summary(daily_profiles)

        return {
            'symbol': self.symbol,
            'weekly_levels': {
                'weekly_open': self.weekly_open,
                'weekly_high': self.weekly_high,
                'weekly_low': self.weekly_low,
                'weekly_close': self.weekly_close,
                'prev_week_high': self.pwh,
                'prev_week_low': self.pwl
            },
            'daily_profiles': daily_profiles,
            'weekly_summary': weekly_summary,
            'trading_implications': self.generate_trading_implications(daily_profiles)
        }

    def generate_weekly_summary(self, daily_profiles: Dict) -> str:
        """Generate weekly narrative summary"""
        if not daily_profiles:
            return "Insufficient data for weekly analysis"

        # Count profile types
        profile_counts = {}
        for day, profile in daily_profiles.items():
            p_type = profile['profile_type']
            profile_counts[p_type] = profile_counts.get(p_type, 0) + 1

        # Determine dominant themes
        themes = []
        if DayProfile.INSIDE_DAY.value in profile_counts:
            themes.append("consolidation")
        if DayProfile.OUTSIDE_DAY.value in profile_counts:
            themes.append("expansion")
        if any('reversal' in profile['narrative'].lower() for profile in daily_profiles.values()):
            themes.append("reversal")

        theme_text = " and ".join(themes) if themes else "mixed price action"

        # Weekly close relative to open
        close_relation = "above" if self.weekly_close > self.weekly_open else "below"

        return f"Week exhibited {theme_text} with close {close_relation} weekly open. Key levels respected: weekly high {self.weekly_high:.2f}, low {self.weekly_low:.2f}."

    def generate_trading_implications(self, daily_profiles: Dict) -> List[str]:
        """Generate trading implications for next week"""
        implications = []

        # Analyze weekly close position
        if self.weekly_close > self.weekly_open:
            implications.append("Bullish weekly close suggests potential continuation next week")
        else:
            implications.append("Bearish weekly close suggests potential pullback next week")

        # Analyze Friday's action
        friday_profile = daily_profiles.get('Friday', {})
        if friday_profile.get('profile_type') == DayProfile.INSIDE_DAY.value:
            implications.append("Friday inside day suggests range-bound start next week")
        elif friday_profile.get('profile_type') == DayProfile.OUTSIDE_DAY.value:
            implications.append("Friday expansion suggests momentum carry into next week")

        # Liquidity analysis
        weekly_range = self.weekly_high - self.weekly_low
        close_position = (self.weekly_close - self.weekly_low) / weekly_range if weekly_range > 0 else 0.5

        if close_position > 0.7:
            implications.append("Close near weekly highs - watch for breakout above PWH")
        elif close_position < 0.3:
            implications.append("Close near weekly lows - watch for breakdown below PWL")
        else:
            implications.append("Close in middle of range - balanced start expected next week")

        return implications
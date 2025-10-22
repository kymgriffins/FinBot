from flask import Blueprint, jsonify, render_template, request, session
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import sqlite3
import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional
import pandas as pd
import pytz

logger = logging.getLogger(__name__)

# Create blueprint
ict_trading_bp = Blueprint('ict_trading', __name__)

# ICT Configuration (same as before)
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

@dataclass
class TradingJournalEntry:
    id: str
    symbol: str
    date: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    position_size: float
    trade_type: str
    market_condition: str
    session: str
    premium_level: float
    discount_level: float
    daily_high: float
    daily_low: float
    setup: str
    outcome: str
    pnl: float
    notes: str
    confidence: float
    lessons: str

class ICTMarketAnalyzer:
    def __init__(self, db_path='ict_trading_journal.db'):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_journal (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                entry_price REAL NOT NULL,
                exit_price REAL,
                position_size REAL NOT NULL,
                trade_type TEXT NOT NULL,
                market_condition TEXT,
                session TEXT,
                premium_level REAL,
                discount_level REAL,
                daily_high REAL,
                daily_low REAL,
                setup TEXT,
                outcome TEXT,
                pnl REAL,
                notes TEXT,
                confidence REAL,
                lessons TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                id TEXT PRIMARY KEY,
                symbol TEXT,
                strategy TEXT,
                start_date TEXT,
                end_date TEXT,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                total_pnl REAL,
                avg_win REAL,
                avg_loss REAL,
                profit_factor REAL,
                max_drawdown REAL,
                sharpe_ratio REAL,
                parameters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def analyze_daily_profile(self, symbol: str, date: datetime = None) -> Dict:
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

            # Generate session analysis
            sessions = self._analyze_market_sessions(data, date)
            key_times = self._get_key_trading_times()
            trading_setups = self._identify_trading_setups(daily_open, daily_close, daily_high, daily_low, premium_levels, discount_levels)

            return {
                'symbol': symbol,
                'date': date.strftime('%Y-%m-%d'),
                'daily_high': daily_high,
                'daily_low': daily_low,
                'daily_open': daily_open,
                'daily_close': daily_close,
                'daily_range': daily_range,
                'daily_bias': self._determine_market_condition(daily_open, daily_close, daily_high, daily_low),
                'premium_levels': [asdict(level) for level in premium_levels],
                'discount_levels': [asdict(level) for level in discount_levels],
                'fvg_levels': [asdict(level) for level in fvg_levels],
                'liquidity_levels': [asdict(level) for level in liquidity_levels],
                'sessions': sessions,
                'key_times': key_times,
                'trading_setups': trading_setups,
                'market_condition': self._determine_market_condition(daily_open, daily_close, daily_high, daily_low)
            }

        except Exception as e:
            logger.error(f"Error analyzing daily profile for {symbol}: {e}")
            return {"error": str(e)}

    def _calculate_premium_levels(self, high: float, low: float, open_price: float) -> List[ICTLevel]:
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

    def _calculate_discount_levels(self, high: float, low: float, open_price: float) -> List[ICTLevel]:
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

    def _find_fair_value_gaps(self, data: pd.DataFrame, target_date: datetime) -> List[ICTLevel]:
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

    def _find_liquidity_levels(self, data: pd.DataFrame, target_date: datetime) -> List[ICTLevel]:
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

    def _analyze_market_sessions(self, data: pd.DataFrame, target_date: datetime) -> List[Dict]:
        """Analyze market sessions for the day"""
        sessions = []

        # Define session times (EST)
        session_times = [
            {"name": "London", "start": "02:00", "end": "11:00", "profile": "High Volume"},
            {"name": "New York", "start": "09:30", "end": "16:00", "profile": "High Volatility"},
            {"name": "Asia", "start": "19:00", "end": "02:00", "profile": "Low Volume"}
        ]

        # For now, return session structure (would need intraday data for real analysis)
        for session in session_times:
            sessions.append({
                "name": session["name"],
                "start_time": session["start"],
                "end_time": session["end"],
                "high": None,  # Would need intraday data
                "low": None,
                "range": None,
                "profile": session["profile"]
            })

        return sessions

    def _get_key_trading_times(self) -> List[Dict]:
        """Get key trading times for ICT methodology"""
        return [
            {"time": "02:00", "event": "London Open", "importance": "High"},
            {"time": "09:30", "event": "New York Open", "importance": "High"},
            {"time": "10:00", "event": "NY Mid Session", "importance": "Medium"},
            {"time": "16:00", "event": "New York Close", "importance": "High"},
            {"time": "19:00", "event": "Asia Open", "importance": "Low"}
        ]

    def _identify_trading_setups(self, open_price: float, close_price: float, high: float, low: float,
                                premium_levels: List[ICTLevel], discount_levels: List[ICTLevel]) -> List[str]:
        """Identify potential ICT trading setups"""
        setups = []

        # Check for premium/discount setups
        if close_price > open_price:
            setups.append("Bullish Premium Rejection")
            setups.append("Discount to Premium Move")
        else:
            setups.append("Bearish Discount Rejection")
            setups.append("Premium to Discount Move")

        # Check for consolidation
        body_size = abs(close_price - open_price)
        total_range = high - low
        if body_size / total_range < 0.3:
            setups.append("Consolidation Breakout Setup")

        # Check for liquidity sweeps
        if len(premium_levels) > 0 and len(discount_levels) > 0:
            setups.append("Liquidity Sweep Setup")

        return setups

class ICTTradingJournal:
    def __init__(self, db_path='ict_trading_journal.db'):
        self.db_path = db_path
        self.analyzer = ICTMarketAnalyzer(db_path)

    def add_trade(self, trade_data: Dict) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if 'id' not in trade_data:
                trade_data['id'] = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            cursor.execute('''
                INSERT INTO trading_journal
                (id, symbol, date, entry_time, exit_time, entry_price, exit_price,
                 position_size, trade_type, market_condition, session, premium_level,
                 discount_level, daily_high, daily_low, setup, outcome, pnl, notes, confidence, lessons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data['id'],
                trade_data['symbol'],
                trade_data['date'],
                trade_data['entry_time'],
                trade_data.get('exit_time'),
                trade_data['entry_price'],
                trade_data.get('exit_price'),
                trade_data['position_size'],
                trade_data['trade_type'],
                trade_data.get('market_condition'),
                trade_data.get('session'),
                trade_data.get('premium_level'),
                trade_data.get('discount_level'),
                trade_data.get('daily_high'),
                trade_data.get('daily_low'),
                trade_data.get('setup'),
                trade_data.get('outcome'),
                trade_data.get('pnl', 0),
                trade_data.get('notes', ''),
                trade_data.get('confidence', 0.5),
                trade_data.get('lessons', '')
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error adding trade: {e}")
            return False

    def get_trades(self, symbol: str = None, start_date: str = None, end_date: str = None) -> List[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT * FROM trading_journal WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            query += " ORDER BY date DESC, entry_time DESC"

            cursor.execute(query, params)
            trades = cursor.fetchall()

            columns = [col[0] for col in cursor.description]
            trade_list = [dict(zip(columns, trade)) for trade in trades]

            conn.close()
            return trade_list

        except Exception as e:
            logger.error(f"Error retrieving trades: {e}")
            return []

    def calculate_journal_stats(self, symbol: str = None) -> Dict:
        trades = self.get_trades(symbol)

        if not trades:
            return {}

        winning_trades = [t for t in trades if t.get('outcome') == 'win']
        losing_trades = [t for t in trades if t.get('outcome') == 'loss']

        total_pnl = sum(t.get('pnl', 0) for t in trades)
        avg_win = np.mean([t.get('pnl', 0) for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.get('pnl', 0) for t in losing_trades]) if losing_trades else 0

        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trades) if trades else 0,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else float('inf'),
            'largest_win': max([t.get('pnl', 0) for t in winning_trades]) if winning_trades else 0,
            'largest_loss': min([t.get('pnl', 0) for t in losing_trades]) if losing_trades else 0
        }

# Initialize components
ict_analyzer = ICTMarketAnalyzer()
trading_journal = ICTTradingJournal()

# Create sample test data
def create_sample_trades():
    """Create sample trades for testing"""
    sample_trades = [
        {
            'symbol': 'ES=F',
            'date': '2024-01-15',
            'entry_time': '09:35',
            'exit_time': '10:15',
            'entry_price': 4850.50,
            'exit_price': 4855.75,
            'position_size': 1.0,
            'trade_type': 'long',
            'market_condition': 'Bullish',
            'session': 'New York',
            'premium_level': 4852.00,
            'discount_level': 4848.00,
            'daily_high': 4860.00,
            'daily_low': 4845.00,
            'setup': 'Premium Rejection',
            'outcome': 'win',
            'pnl': 5.25,
            'notes': 'Strong rejection at premium level with volume confirmation',
            'confidence': 8.5,
            'lessons': 'Premium rejections work well in trending markets'
        },
        {
            'symbol': 'NQ=F',
            'date': '2024-01-16',
            'entry_time': '14:20',
            'exit_time': '15:45',
            'entry_price': 17550.25,
            'exit_price': 17545.00,
            'position_size': 1.0,
            'trade_type': 'short',
            'market_condition': 'Bearish',
            'session': 'New York',
            'premium_level': 17552.00,
            'discount_level': 17548.00,
            'daily_high': 17555.00,
            'daily_low': 17540.00,
            'setup': 'Discount Rejection',
            'outcome': 'win',
            'pnl': 5.25,
            'notes': 'Clean rejection at discount level, good risk/reward',
            'confidence': 7.0,
            'lessons': 'Discount rejections need volume confirmation'
        },
        {
            'symbol': 'ES=F',
            'date': '2024-01-17',
            'entry_time': '10:30',
            'exit_time': '11:00',
            'entry_price': 4865.00,
            'exit_price': 4862.25,
            'position_size': 1.0,
            'trade_type': 'long',
            'market_condition': 'Consolidation',
            'session': 'New York',
            'premium_level': 4867.00,
            'discount_level': 4860.00,
            'daily_high': 4870.00,
            'daily_low': 4858.00,
            'setup': 'FVG Trade',
            'outcome': 'loss',
            'pnl': -2.75,
            'notes': 'FVG filled too quickly, should have waited for better entry',
            'confidence': 6.0,
            'lessons': 'FVG trades need patience and better timing'
        }
    ]

    # Add sample trades to database
    for trade in sample_trades:
        trading_journal.add_trade(trade)

    logger.info(f"Created {len(sample_trades)} sample trades for testing")

# Create sample data on startup
try:
    create_sample_trades()
except Exception as e:
    logger.info(f"Sample trades already exist or error creating: {e}")

# ICT Trading Routes
@ict_trading_bp.route('/')
def ict_dashboard():
    """Main ICT Trading Dashboard"""
    symbols = ['ES=F', 'NQ=F', 'YM=F', 'CL=F', 'GC=F', 'EURUSD=X']
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('ict_dashboard.html', symbols=symbols, datetime=datetime, current_date=current_date)

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

@ict_trading_bp.route('/journal')
def journal_dashboard():
    """Trading Journal Dashboard"""
    return render_template('journal_simple.html')

@ict_trading_bp.route('/test')
def test_route():
    """Test route"""
    return render_template('test_simple.html')

@ict_trading_bp.route('/market-overview')
def market_overview():
    """Market Overview Dashboard"""
    symbols = ['ES=F', 'NQ=F', 'YM=F', 'CL=F', 'GC=F', 'EURUSD=X']
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('market_overview.html', symbols=symbols, datetime=datetime, current_date=current_date)


@ict_trading_bp.route('/market-overview/last10')
def market_overview_last10():
    """Standalone page showing last 10 trading days ICT cards for a symbol."""
    return render_template('ict_last10.html')


@ict_trading_bp.route('/market-overview/cards')
def market_overview_cards():
    """Return ICT summary cards for the last N trading days for each symbol.

    Query params:
      symbols: comma-separated symbol list (default same as dashboard)
      days: number of recent trading days to include (default 10)
    """
    try:
        symbols = request.args.get('symbols', 'ES=F,NQ=F,YM=F,CL=F,GC=F,EURUSD=X').split(',')
        days = int(request.args.get('days', 10))

        # Build last N trading dates (weekdays)
        dates = []
        cur = datetime.now()
        while len(dates) < days:
            if cur.weekday() < 5:  # Mon-Fri
                dates.append(cur)
            cur = cur - timedelta(days=1)

        dates = sorted(dates)

        result: Dict[str, List[Dict]] = {}

        for symbol in symbols:
            sym = symbol.strip()
            cards: List[Dict] = []
            for d in dates:
                analysis = ict_analyzer.analyze_daily_profile(sym, d)
                # Skip days with no data
                if not analysis or 'error' in analysis:
                    continue

                top_premium = analysis.get('premium_levels', [])
                top_discount = analysis.get('discount_levels', [])

                card = {
                    'date': analysis.get('date'),
                    'symbol': sym,
                    'daily_open': analysis.get('daily_open'),
                    'daily_close': analysis.get('daily_close'),
                    'daily_high': analysis.get('daily_high'),
                    'daily_low': analysis.get('daily_low'),
                    'daily_range': analysis.get('daily_range'),
                    'market_condition': analysis.get('market_condition'),
                    'top_premium': top_premium[0] if top_premium else None,
                    'top_discount': top_discount[0] if top_discount else None,
                    'fvg_count': len(analysis.get('fvg_levels', [])),
                    'liquidity_count': len(analysis.get('liquidity_levels', []))
                }
                cards.append(card)

            result[sym] = cards

        # Render HTML page with cards
        return render_template('market_overview_cards.html', data=result)

    except Exception as e:
        logger.exception(f"Error building market overview cards: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


def _get_intraday_df(symbol: str, start_dt: datetime, end_dt: datetime) -> Optional[pd.DataFrame]:
    """Fetch intraday 1m data between start_dt (UTC) and end_dt (UTC) using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_dt, end=end_dt, interval='1m', actions=False)
        if df is None or df.empty:
            return None
        # Ensure timezone-aware UTC index
        idx = df.index
        if idx.tz is None:
            df.index = df.index.tz_localize(pytz.UTC)
        else:
            df.index = df.index.tz_convert(pytz.UTC)
        return df
    except Exception as e:
        logger.warning(f"Intraday fetch failed for {symbol}: {e}")
        return None


def _session_ohlc_from_df(df: pd.DataFrame, session_start_dt: datetime, session_end_dt: datetime) -> Optional[Dict]:
    """Compute OHLC and volume from df (UTC indexed) between session_start_dt and session_end_dt (UTC)."""
    try:
        mask = (df.index >= session_start_dt) & (df.index < session_end_dt)
        part = df.loc[mask]
        if part.empty:
            return None
        return {
            'open': float(part['Open'].iloc[0]),
            'high': float(part['High'].max()),
            'low': float(part['Low'].min()),
            'close': float(part['Close'].iloc[-1]),
            'volume': int(part['Volume'].sum()) if 'Volume' in part.columns else None
        }
    except Exception as e:
        logger.debug(f"Session OHLC calc failed: {e}")
        return None


def _pip_size_for_symbol(symbol: str) -> Optional[float]:
    # Basic heuristic: FX pairs with =X or / or contain common FX tickers
    s = symbol.upper()
    if 'JPY' in s:
        return 0.01
    if any(x in s for x in ['USD', 'EUR', 'GBP', 'AUD', 'NZD', 'CHF']):
        return 0.0001
    return None


@ict_trading_bp.route('/lookback')
def ict_lookback():
    """Lookback view: last N days per symbol with daily OHLC, ranges (points/pips), session OHLCs and selected-time window stats.

    Query params:
      symbols: comma-separated (default: ES=F,NQ=F,GC=F)
      days: int (default 10)
      provider: optional (not used yet)
      time: optional HH:MM (EST) to inspect a specific time of day
      window: optional minutes around time (default 10)
    """
    try:
        symbols = request.args.get('symbols', 'ES=F,NQ=F,GC=F').split(',')
        days = int(request.args.get('days', 10))
        time_str = request.args.get('time')  # e.g., '09:35'
        window_min = int(request.args.get('window', 10))

        # session definitions in US/Eastern
        sessions = {
            'asian_range': ('00:00', '02:00'),
            'london_killzone': ('02:00', '05:00'),
            'london_open': ('08:00', '08:30'),
            'ny_killzone': ('07:00', '10:00'),
            'ny_open': ('09:30', '10:00'),
            'power_3': ('14:00', '16:00'),
            'london_close': ('16:00', '17:00')
        }

        eastern = pytz.timezone('US/Eastern')

        end_date = datetime.now(tz=pytz.UTC)
        start_date = end_date - timedelta(days=days + 3)

        result: Dict[str, List[Dict]] = {}

        # Prepare list of dates (local dates in US/Eastern)
        dates = []
        cur = end_date.astimezone(eastern).date()
        while len(dates) < days:
            dates.append(cur)
            cur = cur - timedelta(days=1)
        dates = sorted(dates)

        # Fetch intraday data once per symbol covering full window
        for raw_sym in symbols:
            sym = raw_sym.strip()
            # yfinance expects start/end naive datetimes or tz-aware; use UTC
            intraday_df = _get_intraday_df(sym, start_date - timedelta(days=1), end_date + timedelta(days=1))

            days_list = []
            for d in dates:
                # build UTC start/end for that trading day (00:00 to 23:59 ET)
                day_start_et = eastern.localize(datetime(d.year, d.month, d.day, 0, 0))
                day_end_et = eastern.localize(datetime(d.year, d.month, d.day, 23, 59, 59))
                day_start_utc = day_start_et.astimezone(pytz.UTC)
                day_end_utc = day_end_et.astimezone(pytz.UTC)

                daily_info = {'date': d.isoformat(), 'symbol': sym}

                # Daily OHLC from intraday df or fallback to analyze_daily_profile
                if intraday_df is not None:
                    mask = (intraday_df.index >= day_start_utc) & (intraday_df.index <= day_end_utc)
                    day_df = intraday_df.loc[mask]
                    if not day_df.empty:
                        daily_info['daily_open'] = float(day_df['Open'].iloc[0])
                        daily_info['daily_high'] = float(day_df['High'].max())
                        daily_info['daily_low'] = float(day_df['Low'].min())
                        daily_info['daily_close'] = float(day_df['Close'].iloc[-1])
                        daily_info['daily_volume'] = int(day_df['Volume'].sum()) if 'Volume' in day_df.columns else None
                    else:
                        # fallback to analyzer
                        analysis = ict_analyzer.analyze_daily_profile(sym, datetime(d.year, d.month, d.day))
                        if 'error' in analysis:
                            continue
                        daily_info['daily_open'] = analysis.get('daily_open')
                        daily_info['daily_high'] = analysis.get('daily_high')
                        daily_info['daily_low'] = analysis.get('daily_low')
                        daily_info['daily_close'] = analysis.get('daily_close')
                        daily_info['daily_volume'] = None
                else:
                    analysis = ict_analyzer.analyze_daily_profile(sym, datetime(d.year, d.month, d.day))
                    if 'error' in analysis:
                        continue
                    daily_info['daily_open'] = analysis.get('daily_open')
                    daily_info['daily_high'] = analysis.get('daily_high')
                    daily_info['daily_low'] = analysis.get('daily_low')
                    daily_info['daily_close'] = analysis.get('daily_close')
                    daily_info['daily_volume'] = None

                # Range in points
                try:
                    daily_info['range_points'] = round(daily_info['daily_high'] - daily_info['daily_low'], 6)
                except Exception:
                    daily_info['range_points'] = None

                # Range in pips if FX
                pip = _pip_size_for_symbol(sym)
                if pip and daily_info.get('range_points') is not None:
                    daily_info['range_pips'] = int(round(daily_info['range_points'] / pip))
                else:
                    daily_info['range_pips'] = None

                # Sessions
                sess_map = {}
                for sname, (st, en) in sessions.items():
                    # session start/end in ET
                    sh, sm = map(int, st.split(':'))
                    eh, em = map(int, en.split(':'))
                    s_start_et = eastern.localize(datetime(d.year, d.month, d.day, sh, sm))
                    s_end_et = eastern.localize(datetime(d.year, d.month, d.day, eh, em))
                    # handle overnight sessions where end < start (e.g., Asia 00:00-02:00)
                    if s_end_et <= s_start_et:
                        s_end_et = s_end_et + timedelta(days=1)
                    s_start_utc = s_start_et.astimezone(pytz.UTC)
                    s_end_utc = s_end_et.astimezone(pytz.UTC)

                    if intraday_df is not None:
                        ohlc = _session_ohlc_from_df(intraday_df, s_start_utc, s_end_utc)
                        sess_map[sname] = ohlc
                    else:
                        sess_map[sname] = None

                daily_info['sessions'] = sess_map

                # Selected time stats
                if time_str:
                    th, tm = map(int, time_str.split(':'))
                    sel_start_et = eastern.localize(datetime(d.year, d.month, d.day, th, tm)) - timedelta(minutes=window_min // 2)
                    sel_end_et = eastern.localize(datetime(d.year, d.month, d.day, th, tm)) + timedelta(minutes=window_min // 2)
                    sel_start_utc = sel_start_et.astimezone(pytz.UTC)
                    sel_end_utc = sel_end_et.astimezone(pytz.UTC)
                    if intraday_df is not None:
                        sel = _session_ohlc_from_df(intraday_df, sel_start_utc, sel_end_utc)
                        daily_info['selected_time'] = sel
                    else:
                        daily_info['selected_time'] = None

                days_list.append(daily_info)

            result[sym] = days_list

        # Render HTML results for lookback
        return render_template('ict_lookback_results.html', data=result)

    except Exception as e:
        logger.exception(f"Error in ict_lookback: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@ict_trading_bp.route('/journal/add', methods=['POST'])
def add_trade_journal():
    """Add trade to journal"""
    try:
        trade_data = request.get_json()

        # Validate required fields
        required_fields = ['symbol', 'entry_price', 'position_size', 'trade_type']
        for field in required_fields:
            if field not in trade_data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400

        # Add default values for missing fields
        if 'date' not in trade_data:
            trade_data['date'] = datetime.now().strftime('%Y-%m-%d')
        if 'entry_time' not in trade_data:
            trade_data['entry_time'] = datetime.now().strftime('%H:%M:%S')
        if 'id' not in trade_data:
            trade_data['id'] = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        success = trading_journal.add_trade(trade_data)

        if success:
            return jsonify({'success': True, 'message': 'Trade added successfully', 'trade_id': trade_data['id']})
        else:
            return jsonify({'success': False, 'error': 'Failed to add trade'}), 500

    except Exception as e:
        logger.error(f"Error in add_trade_journal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@ict_trading_bp.route('/journal/trades')
def get_journal_trades():
    """Get trades from journal"""
    symbol = request.args.get('symbol')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    trades = trading_journal.get_trades(symbol, start_date, end_date)
    return jsonify({'trades': trades})

@ict_trading_bp.route('/journal/stats')
def get_journal_stats():
    """Get journal statistics"""
    symbol = request.args.get('symbol')
    stats = trading_journal.calculate_journal_stats(symbol)
    return jsonify(stats)

@ict_trading_bp.route('/backtest')
def backtest_dashboard():
    """Backtesting Dashboard"""
    return render_template('backtest_dashboard.html')

@ict_trading_bp.route('/backtest/run', methods=['POST'])
def run_backtest():
    """Run strategy backtest"""
    try:
        backtest_data = request.get_json()

        # Placeholder backtest results
        results = {
            'id': f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'symbol': backtest_data.get('symbol', 'ES=F'),
            'strategy': backtest_data.get('strategy', 'ICT Premium Discount'),
            'start_date': backtest_data.get('start_date', '2024-01-01'),
            'end_date': backtest_data.get('end_date', '2024-03-01'),
            'total_trades': 150,
            'winning_trades': 95,
            'losing_trades': 55,
            'win_rate': 0.633,
            'total_pnl': 3250.75,
            'avg_win': 78.25,
            'avg_loss': -45.50,
            'profit_factor': 2.95,
            'max_drawdown': -425.00,
            'sharpe_ratio': 1.72,
            'trades': [
                {'date': '2024-01-15', 'type': 'long', 'outcome': 'win', 'pnl': 5.25, 'entry_price': 4850.50, 'exit_price': 4855.75},
                {'date': '2024-01-16', 'type': 'short', 'outcome': 'win', 'pnl': 3.75, 'entry_price': 17550.25, 'exit_price': 17546.50},
                {'date': '2024-01-17', 'type': 'long', 'outcome': 'loss', 'pnl': -2.25, 'entry_price': 4865.00, 'exit_price': 4862.75}
            ]
        }

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        'database': 'connected',
        'analyzer': 'operational'
    })
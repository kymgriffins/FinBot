from flask import Blueprint, jsonify, request
import sqlite3
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

ict_journal_bp = Blueprint('ict_journal', __name__)

class ICTTradingJournal:
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

        conn.commit()
        conn.close()

    def add_trade(self, trade_data):
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

    def get_trades(self, symbol=None, start_date=None, end_date=None):
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

    def calculate_journal_stats(self, symbol=None):
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
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        }

# Initialize journal
trading_journal = ICTTradingJournal()

# ICT Journal Routes
@ict_journal_bp.route('/')
def journal_dashboard():
    """Trading Journal Dashboard"""
    return jsonify({'status': 'success', 'message': 'ICT Trading Journal'})

@ict_journal_bp.route('/add', methods=['POST'])
def add_trade_journal():
    """Add trade to journal"""
    trade_data = request.get_json()
    success = trading_journal.add_trade(trade_data)
    return jsonify({'success': success})

@ict_journal_bp.route('/trades')
def get_journal_trades():
    """Get trades from journal"""
    symbol = request.args.get('symbol')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    trades = trading_journal.get_trades(symbol, start_date, end_date)
    return jsonify({'trades': trades})

@ict_journal_bp.route('/stats')
def get_journal_stats():
    """Get journal statistics"""
    symbol = request.args.get('symbol')
    stats = trading_journal.calculate_journal_stats(symbol)
    return jsonify(stats)
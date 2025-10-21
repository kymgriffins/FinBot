import io
import logging
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import pytz
import yfinance as yf


logger = logging.getLogger(__name__)


class FuturesDataFetcher:
    def __init__(self):
        self.symbols = self.get_symbols()
        self.timezone = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))

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

    def get_symbol_emoji(self, symbol):
        emojis = {
            'ES=F': '📊',
            'NQ=F': '💻',
            'YM=F': '🏭',
            '6E=F': '💶',
            'CL=F': '🛢️',
            'GC=F': '🥇',
            'SI=F': '🥈'
        }
        return emojis.get(symbol, '📈')

    def get_week_date_range(self, date=None):
        if date is None:
            date = datetime.now()
        monday = date - timedelta(days=date.weekday())
        friday = monday + timedelta(days=4)
        return monday, friday

    def format_week_range(self, monday, friday):
        def get_day_suffix(day):
            if 4 <= day <= 20 or 24 <= day <= 30:
                return 'th'
            else:
                return ['st', 'nd', 'rd'][day % 10 - 1]

        monday_suffix = get_day_suffix(monday.day)
        friday_suffix = get_day_suffix(friday.day)
        monday_str = monday.strftime(f"%d{monday_suffix} %B")
        friday_str = friday.strftime(f"%d{friday_suffix} %B")
        return f"{monday_str} - {friday_str}"

    def fetch_weekly_data(self, symbol):
        try:
            logger.info(f"📊 Fetching weekly data for {symbol}")
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1wk', interval='1m')
            if data.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
            data = data.reset_index()
            data['symbol'] = symbol
            data['symbol_name'] = self.get_symbol_name(symbol)
            data = data.rename(columns={
                'Datetime': 'timestamp',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            data = data[['symbol', 'symbol_name', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
            logger.info(f"✅ Retrieved {len(data)} records for {symbol}")
            return data
        except Exception as e:
            logger.error(f"❌ Error fetching weekly data for {symbol}: {e}")
            return None

    def create_individual_csv_files(self):
        try:
            monday, friday = self.get_week_date_range()
            week_range = self.format_week_range(monday, friday)
            year = monday.year
            csv_files = []
            summary_data = []
            for symbol in self.symbols:
                try:
                    data = self.fetch_weekly_data(symbol)
                    if data is None or data.empty:
                        logger.warning(f"⚠️ No data for {symbol}, skipping")
                        continue
                    csv_buffer = io.StringIO()
                    data.to_csv(csv_buffer, index=False)
                    csv_content = csv_buffer.getvalue()
                    csv_buffer.close()
                    symbol_name_clean = self.get_symbol_name(symbol).replace(' ', '_').replace('/', '_')
                    filename = f"{symbol_name_clean}_{week_range.replace(' ', '_')}_{year}.csv"
                    filename = filename.replace('-', '_to_')
                    csv_files.append({
                        'symbol': symbol,
                        'symbol_name': self.get_symbol_name(symbol),
                        'symbol_emoji': self.get_symbol_emoji(symbol),
                        'filename': filename,
                        'content': csv_content,
                        'data': data,
                        'week_range': week_range
                    })
                    symbol_summary = self.create_symbol_summary(symbol, data, week_range)
                    summary_data.append(symbol_summary)
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Error processing {symbol}: {e}")
                    continue
            return csv_files, summary_data, week_range
        except Exception as e:
            logger.error(f"❌ Error creating CSV files: {e}")
            return [], [], None

    def create_symbol_summary(self, symbol, data, week_range):
        try:
            if data.empty:
                return None
            latest = data.iloc[-1]
            earliest = data.iloc[0]
            weekly_change_pct = ((latest['close'] - data.iloc[0]['open']) / data.iloc[0]['open']) * 100
            summary = {
                'symbol': symbol,
                'symbol_name': self.get_symbol_name(symbol),
                'symbol_emoji': self.get_symbol_emoji(symbol),
                'records': len(data),
                'week_range': week_range,
                'current_price': latest['close'],
                'week_high': data['high'].max(),
                'week_low': data['low'].min(),
                'week_change': weekly_change_pct,
                'total_volume': data['volume'].sum(),
                'data_period': f"{earliest['timestamp'].strftime('%Y-%m-%d %H:%M')} to {latest['timestamp'].strftime('%Y-%m-%d %H:%M')}"
            }
            return summary
        except Exception as e:
            logger.error(f"Error creating summary for {symbol}: {e}")
            return None



    def create_overall_summary_message(self, summary_data, week_range):
        try:
            message = f"📊 <b>Weekly Futures Data - {week_range}</b>\n\n"
            equity_futures = ['ES=F', 'NQ=F', 'YM=F']
            commodity_futures = ['CL=F', 'GC=F', 'SI=F']
            fx_futures = ['6E=F']
            message += "<b>📈 Equity Futures</b>\n"
            for summary in summary_data:
                if summary and summary['symbol'] in equity_futures:
                    change_emoji = "🟢" if summary['week_change'] >= 0 else "🔴"
                    message += f"{summary['symbol_emoji']} <b>{summary['symbol_name']}</b>: ${summary['current_price']:.2f} {change_emoji} {summary['week_change']:+.2f}%\n"
            message += "\n<b>🛢️ Commodity Futures</b>\n"
            for summary in summary_data:
                if summary and summary['symbol'] in commodity_futures:
                    change_emoji = "🟢" if summary['week_change'] >= 0 else "🔴"
                    if summary['symbol'] == 'GC=F':
                        price_str = f"${summary['current_price']:.2f}"
                    elif summary['symbol'] == 'SI=F':
                        price_str = f"${summary['current_price']:.3f}"
                    else:
                        price_str = f"${summary['current_price']:.2f}"
                    message += f"{summary['symbol_emoji']} <b>{summary['symbol_name']}</b>: {price_str} {change_emoji} {summary['week_change']:+.2f}%\n"
            message += "\n<b>💱 Forex Futures</b>\n"
            for summary in summary_data:
                if summary and summary['symbol'] in fx_futures:
                    change_emoji = "🟢" if summary['week_change'] >= 0 else "🔴"
                    message += f"{summary['symbol_emoji']} <b>{summary['symbol_name']}</b>: ${summary['current_price']:.4f} {change_emoji} {summary['week_change']:+.2f}%\n"
            message += f"\n📅 Data Period: {week_range}\n"
            message += f"🕒 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"📁 Files: {len(summary_data)} CSV files attached"
            return message
        except Exception as e:
            logger.error(f"Error creating summary message: {e}")
            return "Summary unavailable"







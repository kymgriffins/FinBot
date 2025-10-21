import os
import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FuturesDataFetcher:
    def __init__(self):
        self.symbols = self.get_symbols()
        self.timezone = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))
        self.interval = os.getenv('DATA_INTERVAL', '1m')
        self.period = os.getenv('DATA_PERIOD', '1d')

    def get_symbols(self):
        """Get trading symbols as list"""
        symbols = os.getenv('SYMBOLS', 'ES=F,NQ=F,YM=F')
        return [s.strip() for s in symbols.split(',')] if symbols else []

    def get_symbol_name(self, symbol):
        """Get proper name for symbols"""
        names = {
            'ES=F': 'S&P 500 Futures',
            'NQ=F': 'NASDAQ Futures',
            'YM=F': 'Dow Futures',
            'CL=F': 'Crude Oil',
            'GC=F': 'Gold'
        }
        return names.get(symbol, symbol)

    def fetch_futures_data(self, symbol):
        """Fetch futures data for a symbol"""
        try:
            logger.info(f"📊 Fetching data for {symbol} ({self.get_symbol_name(symbol)})")

            # Download data
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=self.period, interval=self.interval)

            if data.empty:
                logger.warning(f"No data returned for {symbol}")
                return None

            # Add symbol and clean up
            data = data.reset_index()
            data['symbol'] = symbol
            data['symbol_name'] = self.get_symbol_name(symbol)

            # Rename columns for consistency
            data = data.rename(columns={
                'Datetime': 'timestamp',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            # Select relevant columns
            data = data[['symbol', 'symbol_name', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]

            logger.info(f"✅ Retrieved {len(data)} records for {symbol}")
            return data

        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            return None

    def get_current_prices(self):
        """Get current prices for all symbols"""
        current_prices = {}

        for symbol in self.symbols:
            try:
                data = self.fetch_futures_data(symbol)
                if data is not None and not data.empty:
                    latest = data.iloc[-1]
                    current_prices[symbol] = {
                        'name': self.get_symbol_name(symbol),
                        'price': latest['close'],
                        'change': latest['close'] - latest['open'],
                        'change_pct': ((latest['close'] - latest['open']) / latest['open']) * 100,
                        'timestamp': latest['timestamp'],
                        'volume': latest['volume']
                    }
            except Exception as e:
                logger.error(f"Error getting current price for {symbol}: {e}")
                continue

        return current_prices

    def get_detailed_analysis(self, symbol):
        """Get detailed analysis for a symbol"""
        try:
            data = self.fetch_futures_data(symbol)
            if data is None or data.empty:
                return None

            latest = data.iloc[-1]
            hourly_data = data[data['timestamp'] >= (datetime.now() - timedelta(hours=1))]

            analysis = {
                'symbol': symbol,
                'name': self.get_symbol_name(symbol),
                'current_price': latest['close'],
                'open': latest['open'],
                'high': latest['high'],
                'low': latest['low'],
                'volume': latest['volume'],
                'change': latest['close'] - latest['open'],
                'change_pct': ((latest['close'] - latest['open']) / latest['open']) * 100,
                'hour_high': hourly_data['high'].max(),
                'hour_low': hourly_data['low'].min(),
                'hour_volume': hourly_data['volume'].sum(),
                'timestamp': latest['timestamp'],
                'data_points': len(data)
            }

            return analysis

        except Exception as e:
            logger.error(f"Error in detailed analysis for {symbol}: {e}")
            return None

# Telegram integration (from previous code)
import requests

def auto_detect_telegram_chat_id():
    """Auto-detect and use the most recent Telegram chat ID"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not found")
        return None

    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data['ok'] and data['result']:
                latest_update = data['result'][-1]
                chat_id = latest_update['message']['chat']['id']
                chat_name = latest_update['message']['chat'].get('first_name', 'Unknown')
                logger.info(f"✅ Auto-selected chat: {chat_name} (ID: {chat_id})")
                return chat_id
            else:
                logger.warning("No recent messages found.")
                return None
        else:
            logger.error(f"Failed to get Telegram updates: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error auto-detecting Telegram chat ID: {e}")
        return None

def send_telegram_message(message, chat_id=None):
    """Send message to Telegram"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return False

    if not chat_id:
        chat_id = auto_detect_telegram_chat_id()

    if not chat_id:
        logger.error("No Telegram chat ID available")
        return False

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }

        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Telegram message sent")
            return True
        else:
            logger.error(f"❌ Failed to send Telegram message: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error sending Telegram message: {e}")
        return False

def format_price_message(prices):
    """Format current prices for Telegram"""
    if not prices:
        return "❌ No price data available"

    message = "📊 <b>Futures Market Update</b>\n\n"

    for symbol, data in prices.items():
        emoji = "📈" if data['change'] >= 0 else "📉"
        change_emoji = "🟢" if data['change'] >= 0 else "🔴"

        message += f"{emoji} <b>{data['name']}</b>\n"
        message += f"   💵 Price: <b>${data['price']:.2f}</b>\n"
        message += f"   {change_emoji} Change: ${data['change']:.2f} ({data['change_pct']:+.2f}%)\n"
        message += f"   📦 Volume: {data['volume']:,.0f}\n"
        message += f"   🕒 Time: {data['timestamp'].strftime('%H:%M:%S')}\n\n"

    message += "⚡ <i>Real-time futures data</i>"
    return message

def format_detailed_analysis(analysis):
    """Format detailed analysis for Telegram"""
    if not analysis:
        return "❌ No analysis data available"

    emoji = "📈" if analysis['change'] >= 0 else "📉"
    change_emoji = "🟢" if analysis['change'] >= 0 else "🔴"

    message = f"{emoji} <b>Detailed Analysis - {analysis['name']}</b>\n\n"
    message += f"💵 <b>Current Price:</b> ${analysis['current_price']:.2f}\n"
    message += f"📊 <b>Today's Range:</b> ${analysis['low']:.2f} - ${analysis['high']:.2f}\n"
    message += f"🔄 <b>Daily Change:</b> {change_emoji} ${analysis['change']:.2f} ({analysis['change_pct']:+.2f}%)\n\n"

    message += f"⏰ <b>Last Hour:</b>\n"
    message += f"   📈 High: ${analysis['hour_high']:.2f}\n"
    message += f"   📉 Low: ${analysis['hour_low']:.2f}\n"
    message += f"   📦 Volume: {analysis['hour_volume']:,.0f}\n\n"

    message += f"📊 <b>Data Points:</b> {analysis['data_points']}\n"
    message += f"🕒 <b>Last Update:</b> {analysis['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"

    return message

def main():
    """Main function to test futures data fetching"""
    logger.info("🚀 Starting Futures Data Fetcher...")

    # Initialize data fetcher
    fetcher = FuturesDataFetcher()

    print("🔧 Testing Futures Data Fetching...")
    print("=" * 50)

    # Test symbol configuration
    symbols = fetcher.symbols
    print(f"✅ Trading Symbols: {', '.join(symbols)}")

    # Fetch current prices
    print("\n📊 Fetching current prices...")
    prices = fetcher.get_current_prices()

    if prices:
        for symbol, data in prices.items():
            change_emoji = "🟢" if data['change'] >= 0 else "🔴"
            print(f"✅ {data['name']}: ${data['price']:.2f} {change_emoji} {data['change_pct']:+.2f}%")

        # Send to Telegram
        print("\n🤖 Sending to Telegram...")
        message = format_price_message(prices)
        if send_telegram_message(message):
            print("✅ Price update sent to Telegram!")
        else:
            print("❌ Failed to send Telegram message")

        # Show detailed analysis for first symbol
        print(f"\n📈 Detailed analysis for {symbols[0]}...")
        analysis = fetcher.get_detailed_analysis(symbols[0])
        if analysis:
            print(f"✅ {analysis['name']} Analysis:")
            print(f"   Current: ${analysis['current_price']:.2f}")
            print(f"   Change: {analysis['change_pct']:+.2f}%")
            print(f"   Volume: {analysis['volume']:,.0f}")
            print(f"   Hour Range: ${analysis['hour_low']:.2f} - ${analysis['hour_high']:.2f}")

            # Send detailed analysis
            detailed_msg = format_detailed_analysis(analysis)
            if send_telegram_message(detailed_msg):
                print("✅ Detailed analysis sent to Telegram!")
    else:
        print("❌ Failed to fetch prices")

if __name__ == "__main__":
    main()
import os
import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
import pytz
import requests
import io
from flask import Flask, jsonify

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

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

    def get_symbols(self):
        """Get trading symbols as list"""
        symbols = os.getenv('SYMBOLS', 'ES=F,NQ=F,YM=F,6E=F,CL=F,GC=F,SI=F')
        return [s.strip() for s in symbols.split(',')] if symbols else []

    def get_symbol_name(self, symbol):
        """Get proper name for symbols"""
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
        """Get emoji for each symbol"""
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
        """Get the Monday to Friday date range for a given date"""
        if date is None:
            date = datetime.now()

        # Find Monday of the week
        monday = date - timedelta(days=date.weekday())
        # Find Friday of the week
        friday = monday + timedelta(days=4)

        return monday, friday

    def format_week_range(self, monday, friday):
        """Format date range as '22nd July - 26th July'"""
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
        """Fetch 1-minute data for the entire week"""
        try:
            logger.info(f"📊 Fetching weekly data for {symbol}")

            # Get data for the past 7 days with 1-minute intervals
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1wk', interval='1m')

            if data.empty:
                logger.warning(f"No data returned for {symbol}")
                return None

            # Add symbol info and clean up
            data = data.reset_index()
            data['symbol'] = symbol
            data['symbol_name'] = self.get_symbol_name(symbol)

            # Rename columns
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
            logger.error(f"❌ Error fetching weekly data for {symbol}: {e}")
            return None

    def create_individual_csv_files(self):
        """Create separate CSV files for each symbol with proper naming"""
        try:
            monday, friday = self.get_week_date_range()
            week_range = self.format_week_range(monday, friday)
            year = monday.year

            csv_files = []
            summary_data = []

            for symbol in self.symbols:
                try:
                    # Fetch data for this symbol
                    data = self.fetch_weekly_data(symbol)

                    if data is None or data.empty:
                        logger.warning(f"⚠️ No data for {symbol}, skipping")
                        continue

                    # Create CSV in memory
                    csv_buffer = io.StringIO()
                    data.to_csv(csv_buffer, index=False)
                    csv_content = csv_buffer.getvalue()
                    csv_buffer.close()

                    # Create filename with week range
                    symbol_name_clean = self.get_symbol_name(symbol).replace(' ', '_').replace('/', '_')
                    filename = f"{symbol_name_clean}_{week_range.replace(' ', '_')}_{year}.csv"
                    filename = filename.replace('-', '_to_')

                    # Store file info
                    csv_files.append({
                        'symbol': symbol,
                        'symbol_name': self.get_symbol_name(symbol),
                        'symbol_emoji': self.get_symbol_emoji(symbol),
                        'filename': filename,
                        'content': csv_content,
                        'data': data,
                        'week_range': week_range
                    })

                    # Create summary for this symbol
                    symbol_summary = self.create_symbol_summary(symbol, data, week_range)
                    summary_data.append(symbol_summary)

                    logger.info(f"✅ Created CSV for {symbol}: {filename}")

                    # Small delay to avoid rate limiting
                    time.sleep(1)

                except Exception as e:
                    logger.error(f"❌ Error processing {symbol}: {e}")
                    continue

            return csv_files, summary_data, week_range

        except Exception as e:
            logger.error(f"❌ Error creating CSV files: {e}")
            return [], [], None

    def create_symbol_summary(self, symbol, data, week_range):
        """Create summary for a single symbol"""
        try:
            if data.empty:
                return None

            latest = data.iloc[-1]
            earliest = data.iloc[0]

            # Calculate weekly change from first open to last close
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
        """Create overall summary message for Telegram"""
        try:
            message = f"📊 <b>Weekly Futures Data - {week_range}</b>\n\n"

            # Group by asset class for better organization
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
                    if summary['symbol'] == 'GC=F':  # Gold
                        price_str = f"${summary['current_price']:.2f}"
                    elif summary['symbol'] == 'SI=F':  # Silver
                        price_str = f"${summary['current_price']:.3f}"
                    else:  # Crude Oil
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

# Telegram integration
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

def send_telegram_document(csv_content, filename, caption, chat_id=None):
    """Send CSV file via Telegram"""
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
        # Create file in memory
        csv_bytes = csv_content.encode('utf-8')
        files = {
            'document': (filename, csv_bytes, 'text/csv')
        }

        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        data = {
            'chat_id': chat_id,
            'caption': caption,
            'parse_mode': 'HTML'
        }

        response = requests.post(url, data=data, files=files, timeout=30)
        if response.status_code == 200:
            logger.info(f"✅ CSV file sent: {filename}")
            return True
        else:
            logger.error(f"❌ Failed to send document {filename}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error sending document {filename}: {e}")
        return False

# Flask Routes
@app.route('/')
def home():
    symbols = os.getenv('SYMBOLS', 'ES=F,NQ=F,YM=F,6E=F,CL=F,GC=F,SI=F').split(',')

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Futures Data Bot Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .gradient-bg {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .card-hover {{
            transition: all 0.3s ease;
        }}
        .card-hover:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }}
        .pulse {{
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
            100% {{ transform: scale(1); }}
        }}
    </style>
</head>
<body class="gradient-bg min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="text-center mb-12">
            <h1 class="text-4xl md:text-6xl font-bold text-white mb-4">
                <i class="fas fa-robot mr-4"></i>Futures Data Bot
            </h1>
            <p class="text-xl text-white opacity-90">Real-time Market Data & Analytics</p>
            <div class="inline-flex items-center mt-4 px-4 py-2 bg-green-500 text-white rounded-full pulse">
                <div class="w-3 h-3 bg-white rounded-full mr-2"></div>
                <span class="font-semibold">ACTIVE</span>
            </div>
        </div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-white rounded-2xl p-6 card-hover">
                <div class="flex items-center">
                    <div class="p-3 bg-blue-100 rounded-xl">
                        <i class="fas fa-chart-line text-blue-600 text-2xl"></i>
                    </div>
                    <div class="ml-4">
                        <h3 class="text-sm font-semibold text-gray-500">SYMBOLS TRACKED</h3>
                        <p class="text-2xl font-bold text-gray-800">{len(symbols)}</p>
                    </div>
                </div>
            </div>

            <div class="bg-white rounded-2xl p-6 card-hover">
                <div class="flex items-center">
                    <div class="p-3 bg-green-100 rounded-xl">
                        <i class="fas fa-bolt text-green-600 text-2xl"></i>
                    </div>
                    <div class="ml-4">
                        <h3 class="text-sm font-semibold text-gray-500">DATA INTERVAL</h3>
                        <p class="text-2xl font-bold text-gray-800">1 Minute</p>
                    </div>
                </div>
            </div>

            <div class="bg-white rounded-2xl p-6 card-hover">
                <div class="flex items-center">
                    <div class="p-3 bg-purple-100 rounded-xl">
                        <i class="fas fa-sync-alt text-purple-600 text-2xl"></i>
                    </div>
                    <div class="ml-4">
                        <h3 class="text-sm font-semibold text-gray-500">UPDATE FREQUENCY</h3>
                        <p class="text-2xl font-bold text-gray-800">Real-time</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Symbols Panel -->
            <div class="bg-white rounded-2xl p-6 card-hover">
                <h2 class="text-2xl font-bold text-gray-800 mb-6 flex items-center">
                    <i class="fas fa-list-ul mr-3 text-blue-600"></i>Tracked Symbols
                </h2>
                <div class="space-y-3">
                    {"".join([f'''
                    <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div class="flex items-center">
                            <i class="fas fa-chart-bar text-gray-600 mr-3"></i>
                            <span class="font-semibold">{symbol}</span>
                        </div>
                        <span class="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">Active</span>
                    </div>
                    ''' for symbol in symbols])}
                </div>
            </div>

            <!-- Actions Panel -->
            <div class="bg-white rounded-2xl p-6 card-hover">
                <h2 class="text-2xl font-bold text-gray-800 mb-6 flex items-center">
                    <i class="fas fa-rocket mr-3 text-green-600"></i>Quick Actions
                </h2>
                <div class="space-y-4">
                    <a href="/generate-csv"
                       class="w-full flex items-center justify-between p-4 bg-blue-50 text-blue-700 rounded-xl hover:bg-blue-100 transition-colors">
                        <div class="flex items-center">
                            <i class="fas fa-file-csv text-xl mr-3"></i>
                            <span class="font-semibold">Generate Weekly CSV</span>
                        </div>
                        <i class="fas fa-arrow-right"></i>
                    </a>

                    <a href="/test-telegram"
                       class="w-full flex items-center justify-between p-4 bg-green-50 text-green-700 rounded-xl hover:bg-green-100 transition-colors">
                        <div class="flex items-center">
                            <i class="fab fa-telegram text-xl mr-3"></i>
                            <span class="font-semibold">Test Telegram Bot</span>
                        </div>
                        <i class="fas fa-arrow-right"></i>
                    </a>

                    <a href="/health"
                       class="w-full flex items-center justify-between p-4 bg-purple-50 text-purple-700 rounded-xl hover:bg-purple-100 transition-colors">
                        <div class="flex items-center">
                            <i class="fas fa-heartbeat text-xl mr-3"></i>
                            <span class="font-semibold">System Health</span>
                        </div>
                        <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
            </div>
        </div>

        <!-- API Endpoints -->
        <div class="bg-white rounded-2xl p-6 mt-8 card-hover">
            <h2 class="text-2xl font-bold text-gray-800 mb-6 flex items-center">
                <i class="fas fa-code mr-3 text-gray-600"></i>API Endpoints
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="border-l-4 border-blue-500 pl-4">
                    <h3 class="font-semibold text-gray-800">/health</h3>
                    <p class="text-sm text-gray-600">System status check</p>
                </div>
                <div class="border-l-4 border-green-500 pl-4">
                    <h3 class="font-semibold text-gray-800">/generate-csv</h3>
                    <p class="text-sm text-gray-600">Create & send weekly data</p>
                </div>
                <div class="border-l-4 border-purple-500 pl-4">
                    <h3 class="font-semibold text-gray-800">/test-telegram</h3>
                    <p class="text-sm text-gray-600">Test Telegram integration</p>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center mt-12 text-white opacity-75">
            <p>Futures Data Bot • Built with Flask • Deployed on Render</p>
            <p class="text-sm mt-2">
                <i class="fas fa-clock mr-1"></i>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
    </div>

    <script>
        // Add some interactivity
        document.addEventListener('DOMContentLoaded', function() {{
            // Add click animations
            const cards = document.querySelectorAll('.card-hover');
            cards.forEach(card => {{
                card.addEventListener('click', function() {{
                    this.style.transform = 'scale(0.98)';
                    setTimeout(() => {{
                        this.style.transform = '';
                    }}, 150);
                }});
            }});

            // Update time every minute
            function updateTime() {{
                const now = new Date();
                document.querySelector('footer p:last-child').innerHTML =
                    '<i class="fas fa-clock mr-1"></i>Last updated: ' + now.toLocaleString();
            }}
            setInterval(updateTime, 60000);
        }});
    </script>
</body>
</html>
    """

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/generate-csv')
def generate_csv():
    """Generate and send weekly CSV files"""
    try:
        logger.info("🚀 Starting CSV generation via API...")

        # Initialize data fetcher
        fetcher = FuturesDataFetcher()

        # Generate individual CSV files
        csv_files, summary_data, week_range = fetcher.create_individual_csv_files()

        if not csv_files:
            return jsonify({"error": "Failed to generate CSV files"}), 500

        # Send to Telegram
        summary_message = fetcher.create_overall_summary_message(summary_data, week_range)
        telegram_sent = send_telegram_message(summary_message)

        # Send each CSV file
        successful_sends = 0
        for file_info in csv_files:
            caption = f"{file_info['symbol_emoji']} {file_info['symbol_name']} - {week_range}\nRecords: {len(file_info['data']):,}"
            if send_telegram_document(file_info['content'], file_info['filename'], caption):
                successful_sends += 1
            time.sleep(1)  # Delay between sends

        return jsonify({
            "status": "success",
            "week_range": week_range,
            "files_generated": len(csv_files),
            "files_sent": successful_sends,
            "telegram_message_sent": telegram_sent,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in generate_csv: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-telegram')
def test_telegram():
    """Test Telegram connection"""
    test_message = "🤖 <b>Futures Bot Test</b>\n\nBot is running successfully on Render!\nService: Active ✅"

    if send_telegram_message(test_message):
        return jsonify({"status": "success", "message": "Test message sent to Telegram"})
    else:
        return jsonify({"status": "error", "message": "Failed to send Telegram message"}), 500

# Manual execution (for testing)
def main():
    """Main function to generate and send weekly CSV files"""
    logger.info("🚀 Starting Weekly CSV Generator...")

    # Initialize data fetcher
    fetcher = FuturesDataFetcher()

    print("🔧 Generating Weekly CSV Files...")
    print("=" * 50)

    # Test symbol configuration
    symbols = fetcher.symbols
    print(f"✅ Trading Symbols: {', '.join(symbols)}")
    print(f"✅ Total Symbols: {len(symbols)}")

    # Generate individual CSV files
    print("\n📊 Fetching weekly 1-minute data for each symbol...")
    start_time = time.time()

    csv_files, summary_data, week_range = fetcher.create_individual_csv_files()

    if csv_files and summary_data:
        elapsed_time = time.time() - start_time
        print(f"✅ Data fetched in {elapsed_time:.2f} seconds")
        print(f"✅ Generated {len(csv_files)} CSV files")

        # Show file summary
        print(f"\n📁 Files for {week_range}:")
        for file_info in csv_files:
            print(f"   {file_info['symbol_emoji']} {file_info['filename']} ({len(file_info['data']):,} records)")

        # Send to Telegram
        print("\n🤖 Sending to Telegram...")

        # First send the summary message
        summary_message = fetcher.create_overall_summary_message(summary_data, week_range)
        if send_telegram_message(summary_message):
            print("✅ Summary sent to Telegram!")

        # Then send each CSV file individually
        successful_sends = 0
        for file_info in csv_files:
            caption = f"{file_info['symbol_emoji']} {file_info['symbol_name']} - {week_range}\nRecords: {len(file_info['data']):,}"

            if send_telegram_document(file_info['content'], file_info['filename'], caption):
                successful_sends += 1
                print(f"✅ Sent: {file_info['filename']}")
            else:
                print(f"❌ Failed to send: {file_info['filename']}")

            # Small delay between file sends
            time.sleep(1)

        print(f"\n🎉 Successfully sent {successful_sends} out of {len(csv_files)} files")

    else:
        print("❌ Failed to generate CSV files")

if __name__ == "__main__":
    # For local development
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
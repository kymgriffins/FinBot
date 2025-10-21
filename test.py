import os
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def auto_detect_telegram_chat_id():
    """Auto-detect and use the most recent Telegram chat ID"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not bot_token:
        logging.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return None

    try:
        # Get recent updates to find chat IDs
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data['ok'] and data['result']:
                # Get the most recent message's chat ID
                latest_update = data['result'][-1]
                chat_id = latest_update['message']['chat']['id']
                chat_name = latest_update['message']['chat'].get('first_name', 'Unknown')

                logging.info(f"✅ Auto-selected most recent chat: {chat_name} (ID: {chat_id})")

                # List all available chats for info
                unique_chats = {}
                for update in data['result']:
                    if 'message' in update:
                        chat = update['message']['chat']
                        chat_id = chat['id']
                        chat_name = f"{chat.get('first_name', 'Unknown')} (@{chat.get('username', 'no_username')})"
                        unique_chats[chat_id] = chat_name

                if len(unique_chats) > 1:
                    logging.info("📋 Available chats (using most recent):")
                    for cid, name in unique_chats.items():
                        logging.info(f"   - {name} (ID: {cid})")

                return chat_id
            else:
                logging.warning("No recent messages found. Please send a message to your bot first.")
                return None
        else:
            logging.error(f"Failed to get Telegram updates: {response.text}")
            return None

    except Exception as e:
        logging.error(f"Error auto-detecting Telegram chat ID: {e}")
        return None

def send_telegram_message(message, chat_id=None):
    """Send message to Telegram with auto chat ID detection"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not bot_token:
        logging.error("TELEGRAM_BOT_TOKEN not configured")
        return False

    # Use provided chat_id or auto-detect
    if not chat_id:
        chat_id = auto_detect_telegram_chat_id()

    if not chat_id:
        logging.error("No Telegram chat ID available")
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
            logging.info("✅ Telegram message sent successfully")
            return True
        else:
            logging.error(f"❌ Failed to send Telegram message: {response.text}")
            return False

    except Exception as e:
        logging.error(f"❌ Error sending Telegram message: {e}")
        return False

def get_symbols():
    """Get trading symbols as list"""
    symbols = os.getenv('SYMBOLS', '')
    return [s.strip() for s in symbols.split(',')] if symbols else []

def test_connections():
    """Test all connections based on the config"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print("🔧 Testing Configuration...")
    print("=" * 50)

    # Test Telegram config
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if telegram_token:
        print(f"✅ Telegram Bot Token: {telegram_token[:10]}...")

        # Auto-detect and use most recent chat ID
        chat_id = auto_detect_telegram_chat_id()
        if chat_id:
            print(f"✅ Auto-selected Chat ID: {chat_id}")

            # Test message sending
            symbols = get_symbols()
            test_msg = f"""🤖 <b>FinBot Test</b>

✅ Configuration loaded successfully!
📊 Symbols: {', '.join(symbols)}
🕒 Auto-detected your chat ID

Bot is ready!"""

            if send_telegram_message(test_msg, chat_id):
                print("✅ Telegram test message sent!")
            else:
                print("❌ Failed to send Telegram test message")
        else:
            print("❌ Could not auto-detect Telegram Chat ID")
            print("💡 Send a message to your bot first, then restart")
    else:
        print("❌ Telegram Bot Token missing")

    # Test Email config
    sender_email = os.getenv('SENDER_EMAIL')
    if sender_email:
        print(f"✅ Email Sender: {sender_email}")
    else:
        print("❌ Email configuration missing")

    # Test Symbols
    symbols = get_symbols()
    if symbols:
        print(f"✅ Trading Symbols: {', '.join(symbols)}")

    print("\n🎯 Configuration Complete!")
    print("💡 The most recent Telegram chat has been auto-selected")

if __name__ == "__main__":
    test_connections()
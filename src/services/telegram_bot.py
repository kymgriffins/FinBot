import logging
import os
import requests


logger = logging.getLogger(__name__)


def auto_detect_telegram_chat_id():
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
                return chat_id
            return None
        logger.error(f"Failed to get Telegram updates: {response.text}")
        return None
    except Exception as e:
        logger.error(f"Error auto-detecting Telegram chat ID: {e}")
        return None


def send_telegram_message(message, chat_id=None):
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
        payload = { 'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML' }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        logger.error(f"Failed to send Telegram message: {response.text}")
        return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False


def send_telegram_document(csv_content, filename, caption, chat_id=None):
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
        files = { 'document': (filename, csv_content.encode('utf-8'), 'text/csv') }
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        data = { 'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML' }
        response = requests.post(url, data=data, files=files, timeout=30)
        if response.status_code == 200:
            return True
        logger.error(f"Failed to send document {filename}: {response.text}")
        return False
    except Exception as e:
        logger.error(f"Error sending document {filename}: {e}")
        return False



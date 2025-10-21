from flask import Blueprint, jsonify
from src.services.telegram_bot import send_telegram_message


telegram_bp = Blueprint('telegram', __name__)


@telegram_bp.route('/test')
def test_telegram():
    test_message = "🤖 <b>Futures Bot Test</b>\n\nBot is running successfully!\nService: Active ✅"
    if send_telegram_message(test_message):
        return jsonify({"status": "success", "message": "Test message sent to Telegram"})
    return jsonify({"status": "error", "message": "Failed to send Telegram message"}), 500



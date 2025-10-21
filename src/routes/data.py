import logging
import time
from flask import Blueprint, jsonify

from src.services.data_fetcher import FuturesDataFetcher
from src.services.telegram_bot import send_telegram_message, send_telegram_document


logger = logging.getLogger(__name__)
data_bp = Blueprint('data', __name__)


@data_bp.route('/generate-csv')
def generate_csv():
    try:
        fetcher = FuturesDataFetcher()
        csv_files, summary_data, week_range = fetcher.create_individual_csv_files()
        if not csv_files:
            return jsonify({"error": "Failed to generate CSV files"}), 500
        summary_message = fetcher.create_overall_summary_message(summary_data, week_range)
        telegram_sent = send_telegram_message(summary_message)
        successful_sends = 0
        for file_info in csv_files:
            caption = f"{file_info['symbol_emoji']} {file_info['symbol_name']} - {week_range}\nRecords: {len(file_info['data']):,}"
            if send_telegram_document(file_info['content'], file_info['filename'], caption):
                successful_sends += 1
            time.sleep(1)
        return jsonify({
            "status": "success",
            "week_range": week_range,
            "files_generated": len(csv_files),
            "files_sent": successful_sends,
            "telegram_message_sent": telegram_sent
        })
    except Exception as e:
        logger.exception("Error in generate_csv")
        return jsonify({"error": str(e)}), 500



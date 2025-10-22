from flask import Blueprint, jsonify, request, render_template, current_app
from src.services.data_adapters.fmp_adapter import FMPAdapter
from src.services.provider_registry import get_adapter, map_symbol_to_provider
import logging
import os
logger = logging.getLogger(__name__)
fmp_bp = Blueprint('fmp', __name__)
fmp_adapter = FMPAdapter()

@fmp_bp.route('/dash')
def fmp_dashboard():
    """FMP Analytics Dashboard"""
    # Debug: Check template folder and files
    template_dir = current_app.template_folder
    logger.info(f"Template folder: {template_dir}")

    # Check if template exists
    template_path = os.path.join(template_dir, 'fmp_dashboard.html')
    logger.info(f"Looking for template at: {template_path}")
    logger.info(f"Template exists: {os.path.exists(template_path)}")

    # List all templates
    if os.path.exists(template_dir):
        templates = os.listdir(template_dir)
        logger.info(f"Available templates: {templates}")

    try:
        return render_template('fmp_dashboard.html')
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        return f"Template error: {e}", 500
@fmp_bp.route('/usage')
def get_usage():
    """Get FMP API usage statistics"""
    try:
        usage = fmp_adapter.get_api_usage()
        return jsonify({
            "status": "success",
            "usage": usage
        })
    except Exception as e:
        logger.error(f"Error getting FMP usage: {e}")
        return jsonify({"error": "Failed to get usage data"}), 500

@fmp_bp.route('/financials/<symbol>')
def get_financials(symbol):
    """Get financial statements for a symbol"""
    try:
        provider = request.args.get('provider') or request.args.get('data_provider') or 'fmp'
        statement_type = request.args.get('type', 'income')

        # map canonical symbol to provider specific symbol
        provider_symbol = map_symbol_to_provider(symbol, provider)

        adapter = get_adapter(provider)
        # if adapter doesn't support financials, fall back to fmp
        if provider.lower() != 'fmp':
            try:
                statements = adapter.get_financial_statements(provider_symbol, statement_type)
            except Exception:
                statements = fmp_adapter.get_financial_statements(symbol, statement_type)
        else:
            statements = fmp_adapter.get_financial_statements(symbol, statement_type)

        if statements is None:
            return jsonify({"error": "No financial data available"}), 404

        return jsonify({
            "status": "success",
            "symbol": symbol,
            "statement_type": statement_type,
            "data": statements.to_dict('records') if hasattr(statements, 'to_dict') else statements
        })
    except Exception as e:
        logger.error(f"Error getting financials for {symbol}: {e}")
        return jsonify({"error": "Failed to get financial data"}), 500

@fmp_bp.route('/news')
def get_news():
    """Get market news"""
    try:
        limit = request.args.get('limit', 10, type=int)
        news = fmp_adapter.get_market_news(limit)

        return jsonify({
            "status": "success",
            "news": news
        })
    except Exception as e:
        logger.error(f"Error getting news: {e}")
        return jsonify({"error": "Failed to get news"}), 500

@fmp_bp.route('/screener')
def stock_screener():
    """Stock screener with filters"""
    try:
        filters = {}

        # Add filters from query parameters
        if request.args.get('market_cap_min'):
            filters['marketCapMoreThan'] = int(request.args.get('market_cap_min'))
        if request.args.get('volume_min'):
            filters['volumeMoreThan'] = int(request.args.get('volume_min'))
        if request.args.get('sector'):
            filters['sector'] = request.args.get('sector')

        stocks = fmp_adapter.get_stock_screener(filters)

        return jsonify({
            "status": "success",
            "filters": filters,
            "stocks": stocks.to_dict('records') if hasattr(stocks, 'to_dict') else stocks
        })
    except Exception as e:
        logger.error(f"Error with stock screener: {e}")
        return jsonify({"error": "Failed to run stock screener"}), 500

@fmp_bp.route('/technical/<symbol>')
def technical_indicators(symbol):
    """Get technical indicators"""
    try:
        provider = request.args.get('provider') or request.args.get('data_provider') or 'fmp'
        indicator = request.args.get('indicator', 'sma')
        period = request.args.get('period', 50, type=int)

        provider_symbol = map_symbol_to_provider(symbol, provider)
        adapter = get_adapter(provider)
        try:
            indicators = adapter.get_technical_indicators(provider_symbol, indicator, period)
        except Exception:
            indicators = fmp_adapter.get_technical_indicators(symbol, indicator, period)

        return jsonify({
            "status": "success",
            "symbol": symbol,
            "indicator": indicator,
            "period": period,
            "data": indicators.to_dict('records') if hasattr(indicators, 'to_dict') else indicators
        })
    except Exception as e:
        logger.error(f"Error getting technical indicators for {symbol}: {e}")
        return jsonify({"error": "Failed to get technical indicators"}), 500

@fmp_bp.route('/earnings')
def earnings_calendar():
    """Get earnings calendar"""
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        earnings = fmp_adapter.get_earnings_calendar(from_date, to_date)

        return jsonify({
            "status": "success",
            "earnings": earnings.to_dict('records') if hasattr(earnings, 'to_dict') else earnings
        })
    except Exception as e:
        logger.error(f"Error getting earnings calendar: {e}")
        return jsonify({"error": "Failed to get earnings calendar"}), 500

@fmp_bp.route('/forex')
def forex_rates():
    """Get forex exchange rates"""
    try:
        base_currency = request.args.get('base', 'USD')
        rates = fmp_adapter.get_forex_rates(base_currency)

        return jsonify({
            "status": "success",
            "base_currency": base_currency,
            "rates": rates
        })
    except Exception as e:
        logger.error(f"Error getting forex rates: {e}")
        return jsonify({"error": "Failed to get forex rates"}), 500

@fmp_bp.route('/crypto/<symbol>')
def crypto_price(symbol):
    """Get cryptocurrency price"""
    try:
        provider = request.args.get('provider') or request.args.get('data_provider') or 'fmp'
        provider_symbol = map_symbol_to_provider(symbol, provider)
        adapter = get_adapter(provider)
        try:
            price = adapter.get_crypto_prices(provider_symbol)
        except Exception:
            price = fmp_adapter.get_crypto_prices(symbol)

        return jsonify({
            "status": "success",
            "symbol": symbol,
            "price": price
        })
    except Exception as e:
        logger.error(f"Error getting crypto price for {symbol}: {e}")
        return jsonify({"error": "Failed to get crypto price"}), 500
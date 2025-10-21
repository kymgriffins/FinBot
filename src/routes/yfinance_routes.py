from flask import Blueprint, jsonify, request, render_template
import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)
yfinance_bp = Blueprint('yfinance', __name__)

@yfinance_bp.route('/')
def yfinance_dashboard():
    """yFinance Analytics Dashboard"""
    return render_template('yfinance_dashboard.html')

@yfinance_bp.route('/tracked-symbols')
def get_tracked_symbols():
    """Get current prices for tracked symbols"""
    try:
        symbols = os.getenv('SYMBOLS', 'AAPL,MSFT,GOOGL,TSLA,SPY,QQQ').split(',')
        symbols_data = []

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                history = ticker.history(period='1d', interval='1m')

                if not history.empty:
                    current_price = history['Close'].iloc[-1]
                    prev_close = history['Close'].iloc[0] if len(history) > 1 else current_price
                    change = current_price - prev_close
                    change_percent = (change / prev_close) * 100

                    symbols_data.append({
                        'symbol': symbol,
                        'name': info.get('longName', symbol),
                        'price': round(current_price, 2),
                        'change': round(change, 2),
                        'change_percent': round(change_percent, 2),
                        'volume': info.get('volume', 0),
                        'currency': info.get('currency', 'USD')
                    })

            except Exception as e:
                logger.warning(f"Error fetching data for {symbol}: {e}")
                continue

        return jsonify({
            "status": "success",
            "symbols": symbols_data
        })

    except Exception as e:
        logger.error(f"Error getting tracked symbols: {e}")
        return jsonify({"error": "Failed to get tracked symbols"}), 500

@yfinance_bp.route('/market-status')
def market_status():
    """Check if US market is open"""
    try:
        # Check SPY (S&P 500 ETF) to determine market status
        spy = yf.Ticker("SPY")
        history = spy.history(period='1d', interval='1m')

        is_open = len(history) > 0 and datetime.now().hour >= 9 and datetime.now().hour < 16

        return jsonify({
            "status": "success",
            "is_open": is_open,
            "current_time": datetime.now().strftime('%H:%M:%S'),
            "market_hours": "9:30 AM - 4:00 PM EST"
        })

    except Exception as e:
        logger.error(f"Error checking market status: {e}")
        return jsonify({"error": "Failed to check market status"}), 500

@yfinance_bp.route('/quote/<symbol>')
def get_quote(symbol):
    """Get detailed quote for a symbol"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        history = ticker.history(period='1d', interval='1m')

        if history.empty:
            return jsonify({"error": "No data available for symbol"}), 404

        current_price = history['Close'].iloc[-1]
        prev_close = info.get('previousClose', current_price)
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100

        quote = {
            'symbol': symbol,
            'longName': info.get('longName', symbol),
            'currentPrice': round(current_price, 2),
            'previousClose': round(prev_close, 2),
            'change': round(change, 2),
            'changePercent': round(change_percent, 2),
            'open': info.get('open', current_price),
            'dayHigh': info.get('dayHigh', current_price),
            'dayLow': info.get('dayLow', current_price),
            'volume': info.get('volume', 0),
            'marketCap': info.get('marketCap', 0),
            'trailingPE': info.get('trailingPE'),
            'forwardPE': info.get('forwardPE'),
            'dividendYield': info.get('dividendYield'),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
            'exchange': info.get('exchange', 'N/A'),
            'currency': info.get('currency', 'USD')
        }

        return jsonify({
            "status": "success",
            "quote": quote
        })

    except Exception as e:
        logger.error(f"Error getting quote for {symbol}: {e}")
        return jsonify({"error": f"Failed to get quote for {symbol}"}), 500

@yfinance_bp.route('/historical/<symbol>')
def get_historical(symbol):
    """Get historical price data"""
    try:
        period = request.args.get('period', '1mo')
        interval = request.args.get('interval', '1d')

        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period, interval=interval)

        if history.empty:
            return jsonify({"error": "No historical data available"}), 404

        # Convert to list of dictionaries
        historical_data = []
        for date, row in history.iterrows():
            historical_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(row['Open'], 2),
                'high': round(row['High'], 2),
                'low': round(row['Low'], 2),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
                'dividends': round(row['Dividends'], 4) if 'Dividends' in row and pd.notna(row['Dividends']) else 0,
                'stock_splits': row['Stock Splits'] if 'Stock Splits' in row and pd.notna(row['Stock Splits']) else 0
            })

        return jsonify({
            "status": "success",
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "historical": historical_data
        })

    except Exception as e:
        logger.error(f"Error getting historical data for {symbol}: {e}")
        return jsonify({"error": f"Failed to get historical data for {symbol}"}), 500

@yfinance_bp.route('/options/<symbol>')
def get_options(symbol):
    """Get options chain data"""
    try:
        ticker = yf.Ticker(symbol)
        options_dates = ticker.options

        if not options_dates:
            return jsonify({"error": "No options data available"}), 404

        # Get the nearest expiration
        nearest_date = options_dates[0]
        calls = ticker.option_chain(nearest_date).calls
        puts = ticker.option_chain(nearest_date).puts

        options_data = {
            'expiration_date': nearest_date,
            'calls_count': len(calls),
            'puts_count': len(puts),
            'nearest_calls': calls.head(10).to_dict('records'),
            'nearest_puts': puts.head(10).to_dict('records')
        }

        return jsonify({
            "status": "success",
            "symbol": symbol,
            "options": options_data
        })

    except Exception as e:
        logger.error(f"Error getting options for {symbol}: {e}")
        return jsonify({"error": f"Failed to get options data for {symbol}"}), 500

@yfinance_bp.route('/news/<symbol>')
def get_news(symbol):
    """Get news for a symbol"""
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news

        if not news:
            return jsonify({"error": "No news available"}), 404

        formatted_news = []
        for article in news[:10]:  # Limit to 10 articles
            formatted_news.append({
                'title': article.get('title', 'No title'),
                'publisher': article.get('publisher', 'Unknown'),
                'link': article.get('link', '#'),
                'published_at': datetime.fromtimestamp(article.get('providerPublishTime', 0)).isoformat() if article.get('providerPublishTime') else 'Unknown',
                'summary': article.get('summary', 'No summary available')
            })

        return jsonify({
            "status": "success",
            "symbol": symbol,
            "news": formatted_news
        })

    except Exception as e:
        logger.error(f"Error getting news for {symbol}: {e}")
        return jsonify({"error": f"Failed to get news for {symbol}"}), 500

@yfinance_bp.route('/search/<query>')
def search_symbols(query):
    """Search for symbols"""
    try:
        # Note: yfinance doesn't have a built-in search, so we'll return some common matches
        common_symbols = {
            'apple': 'AAPL', 'microsoft': 'MSFT', 'google': 'GOOGL',
            'tesla': 'TSLA', 'amazon': 'AMZN', 'meta': 'META',
            'netflix': 'NFLX', 'nvidia': 'NVDA', 'spy': 'SPY',
            'qqq': 'QQQ', 'bitcoin': 'BTC-USD', 'gold': 'GC=F',
            'oil': 'CL=F', 'silver': 'SI=F'
        }

        query_lower = query.lower()
        matches = []

        for name, symbol in common_symbols.items():
            if query_lower in name:
                matches.append({'symbol': symbol, 'name': name.title()})

        return jsonify({
            "status": "success",
            "query": query,
            "matches": matches
        })

    except Exception as e:
        logger.error(f"Error searching symbols: {e}")
        return jsonify({"error": "Failed to search symbols"}), 500
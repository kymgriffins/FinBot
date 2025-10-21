from flask import Blueprint, jsonify, request, render_template
from src.services.dailyanalyzer import DailyMarketAnalyzer
import logging
import os

logger = logging.getLogger(__name__)
daily_bp = Blueprint('daily', __name__)
analyzer = DailyMarketAnalyzer()

@daily_bp.route('/dashboard')
def daily_dashboard():
    """Modern dashboard for daily analysis"""
    symbols = os.getenv('SYMBOLS', 'ES=F,NQ=F,YM=F,6E=F,CL=F,GC=F,SI=F').split(',')
    return render_template('daily.html', symbols=symbols)

@daily_bp.route('/daily-report')
def daily_report():
    """Get comprehensive daily market report"""
    try:
        report = analyzer.generate_daily_report()
        return jsonify({
            "status": "success",
            "report": report
        })
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        return jsonify({"error": "Failed to generate daily report"}), 500

@daily_bp.route('/session-analysis')
def session_analysis():
    """Get session-based analysis for all symbols"""
    try:
        analysis = {}
        for symbol in analyzer.symbols:
            symbol_analysis = analyzer.get_daily_analysis(symbol)
            if symbol_analysis:
                analysis[symbol] = symbol_analysis

        return jsonify({
            "status": "success",
            "analysis": analysis
        })
    except Exception as e:
        logger.error(f"Error generating session analysis: {e}")
        return jsonify({"error": "Failed to generate session analysis"}), 500

@daily_bp.route('/historical-analysis')
def historical_analysis():
    """Get historical daily analysis"""
    try:
        days = request.args.get('days', 5, type=int)
        analysis = analyzer.get_historical_daily_analysis(days)

        return jsonify({
            "status": "success",
            "days_analyzed": days,
            "analysis": analysis
        })
    except Exception as e:
        logger.error(f"Error generating historical analysis: {e}")
        return jsonify({"error": "Failed to generate historical analysis"}), 500

@daily_bp.route('/symbol/<symbol>')
def symbol_analysis(symbol):
    """Get daily analysis for a specific symbol"""
    try:
        analysis = analyzer.get_daily_analysis(symbol)

        if not analysis:
            return jsonify({"error": f"No data available for {symbol}"}), 404

        return jsonify({
            "status": "success",
            "analysis": analysis
        })
    except Exception as e:
        logger.error(f"Error analyzing symbol {symbol}: {e}")
        return jsonify({"error": f"Failed to analyze {symbol}"}), 500

@daily_bp.route('/compare-sessions')
def compare_sessions():
    """Compare session performance across all symbols"""
    try:
        session_data = {
            'asia': [],
            'london': [],
            'new_york': []
        }

        for symbol in analyzer.symbols:
            analysis = analyzer.get_daily_analysis(symbol)
            if analysis:
                for session_name, session_info in analysis['sessions'].items():
                    session_data[session_name].append({
                        'symbol': symbol,
                        'symbol_name': analysis['symbol_name'],
                        'pips': session_info['pips'],
                        'direction': session_info['direction'],
                        'volume': session_info['volume']
                    })

        # Sort each session by pips (most volatile first)
        for session in session_data:
            session_data[session].sort(key=lambda x: x['pips'], reverse=True)

        return jsonify({
            "status": "success",
            "session_comparison": session_data
        })
    except Exception as e:
        logger.error(f"Error comparing sessions: {e}")
        return jsonify({"error": "Failed to compare sessions"}), 500

@daily_bp.route('/market-summary')
def market_summary():
    """Get overall market summary and sentiment"""
    try:
        report = analyzer.generate_daily_report()
        summary = report.get('summary', {})

        # Calculate additional metrics
        total_volume = 0
        most_volatile_symbol = None
        max_pips = 0

        for symbol, analysis in report.get('current_analysis', {}).items():
            total_volume += analysis['overall']['total_volume']
            if analysis['overall']['pips'] > max_pips:
                max_pips = analysis['overall']['pips']
                most_volatile_symbol = analysis['symbol_name']

        market_summary = {
            **summary,
            'total_volume': total_volume,
            'most_volatile_symbol': most_volatile_symbol,
            'max_pips': max_pips,
            'total_symbols_analyzed': len(report.get('current_analysis', {}))
        }

        return jsonify({
            "status": "success",
            "market_summary": market_summary
        })
    except Exception as e:
        logger.error(f"Error generating market summary: {e}")
        return jsonify({"error": "Failed to generate market summary"}), 500

@daily_bp.route('/telegram-report')
def telegram_daily_report():
    """Generate a formatted daily report for Telegram"""
    try:
        report = analyzer.generate_daily_report()

        # Format for Telegram
        message = f"📊 <b>Daily Market Report - {report['current_date']}</b>\n\n"

        # Market sentiment
        sentiment_emoji = "🟢" if report['summary']['market_sentiment'] == 'bullish' else "🔴" if report['summary']['market_sentiment'] == 'bearish' else "⚪"
        message += f"{sentiment_emoji} <b>Market Sentiment:</b> {report['summary']['market_sentiment'].upper()}\n"
        message += f"📈 <b>Symbols Analyzed:</b> {report['summary']['total_symbols']}\n"
        message += f"📊 <b>Average Pips:</b> {report['summary']['average_pips']}\n\n"

        # Top performers
        message += "<b>🏆 Session Highlights:</b>\n"

        # Get session comparison
        session_comp = {}
        for symbol, analysis in report.get('current_analysis', {}).items():
            most_volatile_session = analysis['session_volatility']['most_volatile']
            session_comp[most_volatile_session] = session_comp.get(most_volatile_session, 0) + 1

        for session, count in session_comp.items():
            message += f"• {session.title()}: {count} symbols\n"

        message += f"\n📅 Generated: {report['timestamp'][11:16]} UTC"

        return jsonify({
            "status": "success",
            "telegram_message": message,
            "formatted": True
        })
    except Exception as e:
        logger.error(f"Error generating Telegram report: {e}")
        return jsonify({"error": "Failed to generate Telegram report"}), 500

@daily_bp.route('/export-csv')
def export_daily_csv():
    """Export daily analysis as CSV"""
    try:
        import pandas as pd
        from io import StringIO

        report = analyzer.generate_daily_report()
        data = []

        for symbol, analysis in report.get('current_analysis', {}).items():
            row = {
                'symbol': symbol,
                'symbol_name': analysis['symbol_name'],
                'date': analysis['date'],
                'open': analysis['overall']['open'],
                'close': analysis['overall']['close'],
                'high': analysis['overall']['high'],
                'low': analysis['overall']['low'],
                'total_pips': analysis['overall']['pips'],
                'direction': analysis['overall']['direction'],
                'total_volume': analysis['overall']['total_volume']
            }

            # Add session data
            for session_name, session_info in analysis['sessions'].items():
                row[f'{session_name}_pips'] = session_info['pips']
                row[f'{session_name}_direction'] = session_info['direction']
                row[f'{session_name}_volume'] = session_info['volume']

            data.append(row)

        df = pd.DataFrame(data)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        csv_buffer.close()

        return jsonify({
            "status": "success",
            "csv_data": csv_content,
            "filename": f"daily_analysis_{report['current_date']}.csv",
            "records": len(data)
        })
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return jsonify({"error": "Failed to export CSV"}), 500

# Health check for daily analysis service
@daily_bp.route('/health')
def daily_health():
    """Health check for daily analysis service"""
    try:
        # Test with one symbol
        test_analysis = analyzer.get_daily_analysis(analyzer.symbols[0] if analyzer.symbols else 'ES=F')

        return jsonify({
            "status": "healthy",
            "service": "daily_analysis",
            "symbols_configured": len(analyzer.symbols),
            "test_symbol_analyzed": test_analysis is not None,
            "timestamp": analyzer.get_current_timestamp() if hasattr(analyzer, 'get_current_timestamp') else "N/A"
        })
    except Exception as e:
        logger.error(f"Daily analysis health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "service": "daily_analysis",
            "error": str(e)
        }), 500
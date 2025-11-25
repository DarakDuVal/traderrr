"""
app/api/routes.py - REST API endpoints for trading system
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import threading
import numpy as np

from app.core.data_manager import DataManager
from app.core.signal_generator import SignalGenerator
from app.core.portfolio_analyzer import PortfolioAnalyzer
from app.core.portfolio_manager import PortfolioManager
from config.settings import Config

api_bp = Blueprint("api", __name__)
logger = logging.getLogger(__name__)

# Global instances
dm = DataManager(db_path=Config.DATABASE_PATH())
signal_gen = SignalGenerator(min_confidence=Config.MIN_CONFIDENCE())
portfolio_analyzer = PortfolioAnalyzer()
portfolio_manager = PortfolioManager(db_path=Config.DATABASE_PATH())

# Global state for signals
current_signals = []
last_update = None


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for IBM Cloud"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "last_update": last_update,
            "signal_count": len(current_signals),
            "version": "1.0.0",
        }

        # Test database connection
        try:
            dm.get_portfolio_summary(Config.PORTFOLIO_TICKERS()[:1])
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
            health_status["status"] = "degraded"

        # Check if data is stale
        if last_update:
            time_since_update = datetime.now() - datetime.fromisoformat(last_update)
            if time_since_update.total_seconds() > 21600:  # 6 hours
                health_status["status"] = "degraded"
                health_status["warning"] = "Data may be stale"

        status_code = 200 if health_status["status"] == "healthy" else 503
        return jsonify(health_status), status_code

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            503,
        )


@api_bp.route("/signals", methods=["GET"])
def get_signals():
    """Get current trading signals"""
    try:
        # Convert signals to JSON-serializable format
        signals_data = []
        for signal in current_signals:
            signals_data.append(
                {
                    "ticker": signal.ticker,
                    "signal_type": signal.signal_type.value,
                    "confidence": signal.confidence,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "target_price": signal.target_price,
                    "regime": signal.regime.value,
                    "reasons": signal.reasons,
                    "timestamp": signal.timestamp.isoformat(),
                }
            )

        return jsonify(
            {
                "signals": signals_data,
                "last_update": last_update,
                "total_count": len(signals_data),
            }
        )

    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio", methods=["GET"])
def get_portfolio():
    """Get portfolio overview"""
    try:
        # Get recent data for portfolio overview
        portfolio_data = dm.get_multiple_stocks(
            Config.PORTFOLIO_TICKERS(), period="30d"
        )

        if not portfolio_data:
            return jsonify({"error": "No portfolio data available"}), 500

        # Calculate portfolio metrics
        try:
            metrics = portfolio_analyzer.analyze_portfolio(
                portfolio_data, Config.PORTFOLIO_WEIGHTS()
            )

            portfolio_metrics = {
                "volatility": metrics.volatility,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "value_at_risk": metrics.value_at_risk,
                "expected_shortfall": metrics.expected_shortfall,
            }
        except Exception as e:
            logger.warning(f"Portfolio metrics calculation failed: {e}")
            portfolio_metrics = {
                "volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "value_at_risk": 0.0,
                "expected_shortfall": 0.0,
            }

        # Get position risks
        try:
            position_risks = portfolio_analyzer.calculate_position_risks(
                portfolio_data, Config.PORTFOLIO_WEIGHTS(), Config.PORTFOLIO_VALUE()
            )

            position_data = [
                {
                    "ticker": pos.ticker,
                    "weight": pos.weight,
                    "position_size": pos.position_size,
                    "risk_contribution": pos.contribution_to_risk,
                    "liquidity_score": pos.liquidity_score,
                    "concentration_risk": pos.concentration_risk,
                }
                for pos in position_risks
            ]
        except Exception as e:
            logger.warning(f"Position risk calculation failed: {e}")
            position_data = []

        # Get simple overview for each ticker
        overview = {}
        for ticker in Config.PORTFOLIO_TICKERS():
            try:
                if ticker in portfolio_data:
                    data = portfolio_data[ticker]
                    if not data.empty:
                        current_price = data["Close"].iloc[-1]
                        daily_change = data["Close"].pct_change().iloc[-1]
                        volume_ratio = (
                            data["Volume"].iloc[-1]
                            / data["Volume"].rolling(20).mean().iloc[-1]
                        )

                        overview[ticker] = {
                            "price": current_price,
                            "daily_change": daily_change,
                            "volume_ratio": volume_ratio,
                            "weight": Config.PORTFOLIO_WEIGHTS().get(ticker, 0),
                        }
            except Exception as e:
                logger.warning(f"Error processing {ticker}: {e}")
                overview[ticker] = {
                    "price": 0,
                    "daily_change": 0,
                    "volume_ratio": 1,
                    "weight": Config.PORTFOLIO_WEIGHTS().get(ticker, 0),
                }

        return jsonify(
            {
                "portfolio_metrics": portfolio_metrics,
                "position_risks": position_data,
                "portfolio_overview": overview,
                "total_value": Config.PORTFOLIO_VALUE(),
                "updated_at": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Portfolio API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/update", methods=["POST"])
def trigger_update():
    """Manually trigger signal update"""
    try:
        # Run update in background thread to avoid timeout
        def update_signals():
            global current_signals, last_update

            try:
                logger.info("Starting signal update")

                # Download fresh data
                portfolio_data = dm.get_multiple_stocks(
                    Config.PORTFOLIO_TICKERS(), period="6mo"
                )

                if not portfolio_data:
                    logger.warning("No portfolio data received")
                    return

                # Generate new signals
                new_signals = signal_gen.generate_portfolio_signals(portfolio_data)

                # Update global state
                current_signals.clear()
                current_signals.extend(new_signals)
                last_update = datetime.now().isoformat()

                logger.info(f"Updated {len(new_signals)} signals")

            except Exception as e:
                logger.error(f"Error in background update: {e}")

        # Start background thread
        threading.Thread(target=update_signals, daemon=True).start()

        return jsonify(
            {
                "message": "Signal update initiated",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Update API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/tickers/<ticker>", methods=["GET"])
def get_ticker_data(ticker):
    """Get detailed data for a specific ticker"""
    try:
        # Get query parameters
        period = request.args.get("period", "3mo")
        include_indicators = request.args.get("indicators", "false").lower() == "true"

        # Get stock data
        data = dm.get_stock_data(ticker, period=period)

        if data.empty:
            return jsonify({"error": f"No data available for {ticker}"}), 404

        # Prepare response
        response_data = {
            "ticker": ticker,
            "period": period,
            "data_points": len(data),
            "date_range": {
                "start": data.index[0].isoformat(),
                "end": data.index[-1].isoformat(),
            },
            "current_price": data["Close"].iloc[-1],
            "daily_change": data["Close"].pct_change().iloc[-1],
            "volume": data["Volume"].iloc[-1],
        }

        # Add technical indicators if requested
        if include_indicators:
            try:
                from app.core.indicators import TechnicalIndicators

                ti = TechnicalIndicators()

                rsi = ti.rsi(data["Close"]).iloc[-1]
                macd_line, signal_line, _ = ti.macd(data["Close"])
                bb_upper, bb_middle, bb_lower = ti.bollinger_bands(data["Close"])

                response_data["indicators"] = {
                    "rsi": rsi,
                    "macd": {
                        "line": macd_line.iloc[-1],
                        "signal": signal_line.iloc[-1],
                        "bullish": macd_line.iloc[-1] > signal_line.iloc[-1],
                    },
                    "bollinger_bands": {
                        "upper": bb_upper.iloc[-1],
                        "middle": bb_middle.iloc[-1],
                        "lower": bb_lower.iloc[-1],
                        "position": (data["Close"].iloc[-1] - bb_lower.iloc[-1])
                        / (bb_upper.iloc[-1] - bb_lower.iloc[-1]),
                    },
                }
            except Exception as e:
                logger.warning(f"Error calculating indicators for {ticker}: {e}")
                response_data["indicators"] = {
                    "error": "Could not calculate indicators"
                }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Ticker API error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/risk-report", methods=["GET"])
def get_risk_report():
    """Get comprehensive risk report"""
    try:
        # Get portfolio data
        portfolio_data = dm.get_multiple_stocks(Config.PORTFOLIO_TICKERS(), period="1y")

        if not portfolio_data:
            return jsonify({"error": "No portfolio data available"}), 500

        # Generate risk report
        risk_report = portfolio_analyzer.generate_risk_report(
            portfolio_data, Config.PORTFOLIO_WEIGHTS(), Config.PORTFOLIO_VALUE()
        )

        return jsonify(risk_report)

    except Exception as e:
        logger.error(f"Risk report API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/correlation", methods=["GET"])
def get_correlation_matrix():
    """Get correlation matrix for portfolio"""
    try:
        # Get portfolio data
        portfolio_data = dm.get_multiple_stocks(
            Config.PORTFOLIO_TICKERS(), period="6mo"
        )

        if not portfolio_data:
            return jsonify({"error": "No portfolio data available"}), 500

        # Calculate correlation matrix
        correlation_matrix = portfolio_analyzer.calculate_correlation_matrix(
            portfolio_data
        )

        if correlation_matrix.empty:
            return jsonify({"error": "Could not calculate correlation matrix"}), 500

        # Convert to JSON-serializable format
        correlation_data = {
            "tickers": correlation_matrix.columns.tolist(),
            "matrix": correlation_matrix.values.tolist(),
            "average_correlation": correlation_matrix.values[
                np.triu_indices_from(correlation_matrix.values, k=1)
            ].mean(),
            "max_correlation": correlation_matrix.values[
                np.triu_indices_from(correlation_matrix.values, k=1)
            ].max(),
            "min_correlation": correlation_matrix.values[
                np.triu_indices_from(correlation_matrix.values, k=1)
            ].min(),
        }

        return jsonify(correlation_data)

    except Exception as e:
        logger.error(f"Correlation API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/optimization", methods=["POST"])
def optimize_portfolio():
    """Optimize portfolio weights"""
    try:
        # Get request parameters
        data = request.get_json() or {}
        risk_tolerance = data.get("risk_tolerance", 0.15)
        target_return = data.get("target_return")  # Optional

        # Get portfolio data
        portfolio_data = dm.get_multiple_stocks(Config.PORTFOLIO_TICKERS(), period="1y")

        if not portfolio_data:
            return jsonify({"error": "No portfolio data available"}), 500

        # Optimize portfolio
        optimized_weights = portfolio_analyzer.optimize_portfolio(
            portfolio_data,
            Config.PORTFOLIO_WEIGHTS(),
            target_return=target_return,
            risk_tolerance=risk_tolerance,
        )

        # Calculate comparison metrics
        current_metrics = portfolio_analyzer.analyze_portfolio(
            portfolio_data, Config.PORTFOLIO_WEIGHTS()
        )
        optimized_metrics = portfolio_analyzer.analyze_portfolio(
            portfolio_data, optimized_weights
        )

        return jsonify(
            {
                "current_weights": Config.PORTFOLIO_WEIGHTS(),
                "optimized_weights": optimized_weights,
                "current_metrics": {
                    "volatility": current_metrics.volatility,
                    "sharpe_ratio": current_metrics.sharpe_ratio,
                    "max_drawdown": current_metrics.max_drawdown,
                },
                "optimized_metrics": {
                    "volatility": optimized_metrics.volatility,
                    "sharpe_ratio": optimized_metrics.sharpe_ratio,
                    "max_drawdown": optimized_metrics.max_drawdown,
                },
                "parameters": {
                    "risk_tolerance": risk_tolerance,
                    "target_return": target_return,
                },
            }
        )

    except Exception as e:
        logger.error(f"Optimization API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio/positions", methods=["GET"])
def get_portfolio_positions_api():
    """Get all portfolio positions with current values"""
    try:
        positions = portfolio_manager.get_all_positions()

        if not positions:
            return jsonify({"positions": [], "total_value": 0, "updated_at": datetime.now().isoformat()}), 200

        # Get current prices
        tickers = list(positions.keys())
        try:
            portfolio_data = dm.get_multiple_stocks(tickers, period="1d")
        except Exception as e:
            logger.warning(f"Could not fetch current prices: {e}")
            portfolio_data = {}

        # Build response with current values
        positions_with_values = []
        total_value = 0

        for ticker, shares in positions.items():
            current_price = 0

            if ticker in portfolio_data and not portfolio_data[ticker].empty:
                current_price = portfolio_data[ticker]["Close"].iloc[-1]

            position_value = shares * current_price
            total_value += position_value

            positions_with_values.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "current_price": current_price,
                    "position_value": position_value,
                }
            )

        return jsonify(
            {
                "positions": positions_with_values,
                "total_value": total_value,
                "updated_at": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Get positions API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio/positions", methods=["POST"])
def add_portfolio_position():
    """Add or update a portfolio position"""
    try:
        data = request.get_json() or {}
        ticker = data.get("ticker")
        shares = data.get("shares")

        if not ticker or shares is None:
            return jsonify({"error": "Missing ticker or shares"}), 400

        # Validate and update
        success, issues = portfolio_manager.add_or_update_position(ticker, shares)

        if not success:
            return jsonify({"error": "Validation failed", "issues": issues}), 400

        # Return updated position with current value
        try:
            portfolio_data = dm.get_multiple_stocks([ticker.upper()], period="1d")
            current_price = (
                portfolio_data[ticker.upper()]["Close"].iloc[-1]
                if ticker.upper() in portfolio_data and not portfolio_data[ticker.upper()].empty
                else 0
            )
        except Exception as e:
            logger.warning(f"Could not fetch price for {ticker}: {e}")
            current_price = 0

        position_value = float(shares) * current_price

        return jsonify(
            {
                "message": f"Position {ticker.upper()} updated successfully",
                "position": {
                    "ticker": ticker.upper(),
                    "shares": float(shares),
                    "current_price": current_price,
                    "position_value": position_value,
                },
                "updated_at": datetime.now().isoformat(),
            }
        ), 201

    except Exception as e:
        logger.error(f"Add position API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio/positions/<ticker>", methods=["PUT"])
def update_portfolio_position(ticker):
    """Update shares for a specific position"""
    try:
        data = request.get_json() or {}
        shares = data.get("shares")

        if shares is None:
            return jsonify({"error": "Missing shares"}), 400

        # Validate and update
        success, issues = portfolio_manager.add_or_update_position(ticker, shares)

        if not success:
            return jsonify({"error": "Validation failed", "issues": issues}), 400

        # Return updated position with current value
        try:
            portfolio_data = dm.get_multiple_stocks([ticker.upper()], period="1d")
            current_price = (
                portfolio_data[ticker.upper()]["Close"].iloc[-1]
                if ticker.upper() in portfolio_data and not portfolio_data[ticker.upper()].empty
                else 0
            )
        except Exception as e:
            logger.warning(f"Could not fetch price for {ticker}: {e}")
            current_price = 0

        position_value = float(shares) * current_price

        return jsonify(
            {
                "message": f"Position {ticker.upper()} updated successfully",
                "position": {
                    "ticker": ticker.upper(),
                    "shares": float(shares),
                    "current_price": current_price,
                    "position_value": position_value,
                },
                "updated_at": datetime.now().isoformat(),
            }
        ), 200

    except Exception as e:
        logger.error(f"Update position API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio/positions/<ticker>", methods=["DELETE"])
def delete_portfolio_position(ticker):
    """Remove a position from the portfolio"""
    try:
        success, issues = portfolio_manager.remove_position(ticker)

        if not success:
            return jsonify({"error": "Could not remove position", "issues": issues}), 400

        return jsonify(
            {
                "message": f"Position {ticker.upper()} removed successfully",
                "updated_at": datetime.now().isoformat(),
            }
        ), 200

    except Exception as e:
        logger.error(f"Delete position API error: {e}")
        return jsonify({"error": str(e)}), 500


# Initialize background update on first import
def initialize_signals():
    """Initialize signals and portfolio on startup"""
    global current_signals, last_update

    try:
        logger.info("Initializing system...")

        # Initialize portfolio from config if empty
        try:
            initial_positions = {
                "AAPL": 10,
                "META": 20,
                "MSFT": 15,
                "NVDA": 5,
                "GOOGL": 8,
                "JPM": 12,
                "BAC": 25,
                "PG": 8,
                "JNJ": 6,
                "VTI": 9,
                "SPY": 7,
                "SIEGY": 40,
                "VWAGY": 50,
                "SYIEY": 18,
                "QTUM": 100,
                "QBTS": 50,
            }
            portfolio_manager.initialize_from_config(initial_positions)
            logger.info("Portfolio initialized")
        except Exception as e:
            logger.warning(f"Could not initialize portfolio: {e}")

        logger.info("Initializing trading signals")

        # Get initial portfolio data
        portfolio_tickers = portfolio_manager.get_tickers()
        if not portfolio_tickers:
            portfolio_tickers = Config.PORTFOLIO_TICKERS()[:5]

        portfolio_data = dm.get_multiple_stocks(portfolio_tickers[:5], period="3mo")

        if portfolio_data:
            # Generate initial signals
            initial_signals = signal_gen.generate_portfolio_signals(portfolio_data)
            current_signals.extend(initial_signals)
            last_update = datetime.now().isoformat()

            logger.info(f"Initialized with {len(initial_signals)} signals")
        else:
            logger.warning("Could not initialize signals - no data available")

    except Exception as e:
        logger.error(f"Error initializing system: {e}")


# Run initialization when module is imported
initialize_signals()

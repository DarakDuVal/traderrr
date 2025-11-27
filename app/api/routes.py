"""
app/api/routes.py - REST API endpoints for trading system with Flasgger documentation
"""

from flask import Blueprint, request, jsonify, Response
from datetime import datetime
import logging
import threading
import numpy as np
from typing import Tuple, Any, List, Optional, cast, Dict

from app.core.data_manager import DataManager
from app.core.signal_generator import SignalGenerator
from app.core.portfolio_analyzer import PortfolioAnalyzer
from app.core.portfolio_manager import PortfolioManager
from app.api.auth import require_api_key
from config.settings import Config

api_bp = Blueprint("api", __name__)
logger = logging.getLogger(__name__)

# Global instances
dm = DataManager(db_path=Config.DATABASE_PATH())
signal_gen = SignalGenerator(min_confidence=Config.MIN_CONFIDENCE())
portfolio_analyzer = PortfolioAnalyzer()
portfolio_manager = PortfolioManager(db_path=Config.DATABASE_PATH())

# Global state for signals
current_signals: List[Any] = []
last_update: Optional[str] = None


# ============================================================================
# HEALTH ENDPOINTS
# ============================================================================


@api_bp.route("/health", methods=["GET"])
@require_api_key
def health_check() -> Tuple[Response, int]:
    """
    Get system health status
    ---
    tags:
      - health
    security:
      - Bearer: []
    responses:
      200:
        description: Health check successful
        schema:
          type: object
          properties:
            status:
              type: string
              enum: ['healthy', 'degraded', 'unhealthy']
              description: Overall system health status
            timestamp:
              type: string
              description: Health check timestamp (ISO8601)
            database:
              type: string
              description: Database connection status
            last_update:
              type: string
              description: Last system update timestamp
            signal_count:
              type: integer
              description: Number of active trading signals
            version:
              type: string
              description: API version
            warning:
              type: string
              description: Optional warning message
      503:
        description: Service unavailable
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "last_update": last_update,
            "signal_count": len(current_signals),
            "version": "1.0.0",
        }

        try:
            tickers = portfolio_manager.get_tickers()
            if tickers:
                dm.get_portfolio_summary([tickers[0]])
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
            health_status["status"] = "degraded"

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


# ============================================================================
# SIGNALS ENDPOINTS
# ============================================================================


@api_bp.route("/signals", methods=["GET"])
@require_api_key
def get_signals() -> Tuple[Response, int]:
    """
    Get current trading signals
    ---
    tags:
      - signals
    security:
      - Bearer: []
    responses:
      200:
        description: Current trading signals
        schema:
          type: object
          properties:
            signals:
              type: array
              items:
                type: object
                properties:
                  ticker:
                    type: string
                  signal_type:
                    type: string
                    enum: ['BUY', 'SELL', 'HOLD', 'STRONG_BUY', 'STRONG_SELL']
                  confidence:
                    type: number
                  entry_price:
                    type: number
                  stop_loss:
                    type: number
                  target_price:
                    type: number
                  regime:
                    type: string
                  reasons:
                    type: array
                    items:
                      type: string
                  timestamp:
                    type: string
            last_update:
              type: string
            total_count:
              type: integer
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
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

        return (
            jsonify(
                {
                    "signals": signals_data,
                    "last_update": last_update,
                    "total_count": len(signals_data),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/signal-history", methods=["GET"])
@require_api_key
def get_signal_history() -> Tuple[Response, int]:
    """
    Get historical trading signals with optional filters
    ---
    tags:
      - signals
    security:
      - Bearer: []
    parameters:
      - name: ticker
        in: query
        type: string
        description: Filter by ticker (e.g., AAPL)
      - name: start_date
        in: query
        type: string
        description: Start date (YYYY-MM-DD)
      - name: end_date
        in: query
        type: string
        description: End date (YYYY-MM-DD)
      - name: signal_type
        in: query
        type: string
        description: Filter by type (BUY, SELL, HOLD)
      - name: min_confidence
        in: query
        type: number
        description: Minimum confidence (0.0-1.0)
      - name: limit
        in: query
        type: integer
        description: Max records (default 100, max 1000)
    responses:
      200:
        description: Signal history retrieved
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
        ticker = request.args.get("ticker", type=str)
        start_date = request.args.get("start_date", type=str)
        end_date = request.args.get("end_date", type=str)
        signal_type = request.args.get("signal_type", type=str)
        min_confidence = request.args.get("min_confidence", default=0.0, type=float)
        limit = request.args.get("limit", default=100, type=int)

        limit = min(limit, 1000)

        signals = dm.get_signal_history(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            signal_type=signal_type,
            min_confidence=min_confidence,
            limit=limit,
        )

        return (
            jsonify(
                {
                    "signals": signals,
                    "count": len(signals),
                    "filters": {
                        "ticker": ticker,
                        "start_date": start_date,
                        "end_date": end_date,
                        "signal_type": signal_type,
                        "min_confidence": min_confidence,
                        "limit": limit,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Signal history API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/signal-history/<ticker>", methods=["GET"])
@require_api_key
def get_signal_history_by_ticker(ticker: str) -> Tuple[Response, int]:
    """
    Get signal history for a specific ticker
    ---
    tags:
      - signals
    security:
      - Bearer: []
    parameters:
      - name: ticker
        in: path
        type: string
        required: true
      - name: limit
        in: query
        type: integer
        description: Max records (default 50, max 1000)
    responses:
      200:
        description: Signal history retrieved
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
        limit = request.args.get("limit", default=50, type=int)
        limit = min(limit, 1000)

        signals = dm.get_signals_by_ticker(ticker=ticker, limit=limit)

        return (
            jsonify(
                {
                    "ticker": ticker.upper(),
                    "signals": signals,
                    "count": len(signals),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Signal history API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/signal-stats", methods=["GET"])
@require_api_key
def get_signal_stats() -> Tuple[Response, int]:
    """
    Get statistics about signals
    ---
    tags:
      - signals
    security:
      - Bearer: []
    parameters:
      - name: ticker
        in: query
        type: string
        description: Optional - filter by ticker
    responses:
      200:
        description: Signal statistics retrieved
      401:
        description: Unauthorized
      404:
        description: No signal data available
      500:
        description: Server error
    """
    try:
        ticker = request.args.get("ticker", type=str)

        stats = dm.get_signals_stats(ticker=ticker)

        if not stats:
            return (
                jsonify(
                    {
                        "message": (
                            "No signal data available"
                            if not ticker
                            else f"No signals found for {ticker}"
                        )
                    }
                ),
                404,
            )

        return (
            jsonify(
                {
                    "ticker": ticker.upper() if ticker else None,
                    "stats": stats,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Signal stats API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/update", methods=["POST"])
@require_api_key
def trigger_update() -> Tuple[Response, int]:
    """
    Manually trigger signal update
    ---
    tags:
      - signals
    security:
      - Bearer: []
    responses:
      202:
        description: Signal update initiated
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:

        def update_signals() -> None:
            global current_signals, last_update

            try:
                logger.info("Starting signal update")

                tickers = portfolio_manager.get_tickers()
                if not tickers:
                    logger.warning("No portfolio positions configured")
                    return

                portfolio_data = dm.get_multiple_stocks(tickers, period="6mo")

                if not portfolio_data:
                    logger.warning("No portfolio data received")
                    return

                new_signals = signal_gen.generate_portfolio_signals(portfolio_data)

                current_signals.clear()
                current_signals.extend(new_signals)
                last_update = datetime.now().isoformat()

                logger.info(f"Updated {len(new_signals)} signals")

            except Exception as e:
                logger.error(f"Error in background update: {e}")

        threading.Thread(target=update_signals, daemon=True).start()

        return (
            jsonify(
                {
                    "message": "Signal update initiated",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            202,
        )

    except Exception as e:
        logger.error(f"Update API error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PORTFOLIO PERFORMANCE ENDPOINTS
# ============================================================================


@api_bp.route("/portfolio-performance", methods=["GET"])
@require_api_key
def get_portfolio_performance() -> Tuple[Response, int]:
    """
    Get historical portfolio performance data
    ---
    tags:
      - portfolio-performance
    security:
      - Bearer: []
    parameters:
      - name: start_date
        in: query
        type: string
        description: Start date (YYYY-MM-DD)
      - name: end_date
        in: query
        type: string
        description: End date (YYYY-MM-DD)
      - name: limit
        in: query
        type: integer
        description: Max records (default 100, max 1000)
    responses:
      200:
        description: Performance data retrieved
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
        start_date = request.args.get("start_date", type=str)
        end_date = request.args.get("end_date", type=str)
        limit = request.args.get("limit", default=100, type=int)

        limit = min(limit, 1000)

        performance = dm.get_portfolio_performance(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        return (
            jsonify(
                {
                    "performance": performance,
                    "count": len(performance),
                    "filters": {
                        "start_date": start_date,
                        "end_date": end_date,
                        "limit": limit,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Portfolio performance API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio-performance/summary", methods=["GET"])
@require_api_key
def get_performance_summary() -> Tuple[Response, int]:
    """
    Get portfolio performance summary for a period
    ---
    tags:
      - portfolio-performance
    security:
      - Bearer: []
    parameters:
      - name: days
        in: query
        type: integer
        description: Look-back period (default 30, max 365)
    responses:
      200:
        description: Performance summary retrieved
      401:
        description: Unauthorized
      404:
        description: No data available
      500:
        description: Server error
    """
    try:
        days = request.args.get("days", default=30, type=int)
        days = max(1, min(days, 365))

        summary = dm.get_performance_summary(days=days)

        if not summary:
            return (
                jsonify({"message": "No performance data available for the specified period"}),
                404,
            )

        return (
            jsonify(
                {
                    "period_days": days,
                    "summary": summary,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Performance summary API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio-performance/metrics", methods=["GET"])
@require_api_key
def get_performance_metrics() -> Tuple[Response, int]:
    """
    Get comprehensive portfolio performance metrics
    ---
    tags:
      - portfolio-performance
    security:
      - Bearer: []
    parameters:
      - name: days
        in: query
        type: integer
        description: Analysis period (default 90, max 365)
    responses:
      200:
        description: Performance metrics retrieved
      401:
        description: Unauthorized
      404:
        description: No data available
      500:
        description: Server error
    """
    try:
        days = request.args.get("days", default=90, type=int)
        days = max(1, min(days, 365))

        metrics = dm.get_performance_metrics(days=days)

        if not metrics:
            return (
                jsonify({"message": "No performance data available for the specified period"}),
                404,
            )

        return (
            jsonify(
                {
                    "period_days": days,
                    "metrics": metrics,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Performance metrics API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio-performance/latest", methods=["GET"])
@require_api_key
def get_latest_performance() -> Tuple[Response, int]:
    """
    Get the latest portfolio performance record
    ---
    tags:
      - portfolio-performance
    security:
      - Bearer: []
    responses:
      200:
        description: Latest performance retrieved
      401:
        description: Unauthorized
      404:
        description: No data available
      500:
        description: Server error
    """
    try:
        performance = dm.get_portfolio_performance(limit=1)

        if not performance:
            return (
                jsonify(
                    {
                        "message": "No performance data available",
                    }
                ),
                404,
            )

        return (
            jsonify(
                {
                    "latest_performance": performance[0],
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Latest performance API error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PORTFOLIO MANAGEMENT ENDPOINTS
# ============================================================================


@api_bp.route("/portfolio", methods=["GET"])
@require_api_key
def get_portfolio() -> Tuple[Response, int]:
    """
    Get portfolio overview with metrics and risk analysis
    ---
    tags:
      - portfolio
    security:
      - Bearer: []
    responses:
      200:
        description: Portfolio overview retrieved
      400:
        description: No portfolio positions configured
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
        tickers = portfolio_manager.get_tickers()
        if not tickers:
            return jsonify({"error": "No portfolio positions configured"}), 400

        portfolio_data = dm.get_multiple_stocks(tickers, period="30d")

        if not portfolio_data:
            return jsonify({"error": "No portfolio data available"}), 500

        current_prices = {}
        for ticker in tickers:
            if ticker in portfolio_data and not portfolio_data[ticker].empty:
                current_prices[ticker] = portfolio_data[ticker]["Close"].iloc[-1]
            else:
                current_prices[ticker] = 0

        weights = portfolio_manager.get_weights(current_prices)
        total_value = portfolio_manager.get_total_value(current_prices)

        try:
            metrics = portfolio_analyzer.analyze_portfolio(portfolio_data, weights)
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

        try:
            position_risks = portfolio_analyzer.calculate_position_risks(
                portfolio_data, weights, total_value
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

        overview = {}
        for ticker in tickers:
            try:
                if ticker in portfolio_data:
                    data = portfolio_data[ticker]
                    if not data.empty:
                        current_price = data["Close"].iloc[-1]
                        daily_change = data["Close"].pct_change().iloc[-1]
                        volume_ratio = (
                            data["Volume"].iloc[-1] / data["Volume"].rolling(20).mean().iloc[-1]
                        )

                        overview[ticker] = {
                            "price": current_price,
                            "daily_change": daily_change,
                            "volume_ratio": volume_ratio,
                            "weight": weights.get(ticker, 0),
                        }
            except Exception as e:
                logger.warning(f"Error processing {ticker}: {e}")
                overview[ticker] = {
                    "price": 0,
                    "daily_change": 0,
                    "volume_ratio": 1,
                    "weight": weights.get(ticker, 0),
                }

        return (
            jsonify(
                {
                    "portfolio_metrics": portfolio_metrics,
                    "position_risks": position_data,
                    "portfolio_overview": overview,
                    "total_value": total_value,
                    "updated_at": datetime.now().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Portfolio API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio/positions", methods=["GET"])
@require_api_key
def get_portfolio_positions_api() -> Tuple[Response, int]:
    """
    Get all portfolio positions with current values
    ---
    tags:
      - portfolio
    security:
      - Bearer: []
    responses:
      200:
        description: Positions retrieved
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
        positions = portfolio_manager.get_all_positions()

        if not positions:
            return (
                jsonify(
                    {
                        "positions": [],
                        "total_value": 0,
                        "updated_at": datetime.now().isoformat(),
                    }
                ),
                200,
            )

        tickers = list(positions.keys())
        try:
            portfolio_data = dm.get_multiple_stocks(tickers, period="1d")
        except Exception as e:
            logger.warning(f"Could not fetch current prices: {e}")
            portfolio_data = {}

        positions_with_values = []
        total_value = 0.0

        for ticker, shares in positions.items():
            current_price = 0.0

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

        return (
            jsonify(
                {
                    "positions": positions_with_values,
                    "total_value": total_value,
                    "updated_at": datetime.now().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Get positions API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio/positions", methods=["POST"])
@require_api_key
def add_portfolio_position() -> Tuple[Response, int]:
    """
    Add or update a portfolio position
    ---
    tags:
      - portfolio
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            ticker:
              type: string
              description: Stock ticker symbol
            shares:
              type: number
              description: Number of shares to hold
          required:
            - ticker
            - shares
    responses:
      201:
        description: Position added/updated
      400:
        description: Invalid request
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
        data = request.get_json() or {}
        ticker = data.get("ticker")
        shares = data.get("shares")

        if not ticker or shares is None:
            return jsonify({"error": "Missing ticker or shares"}), 400

        success, issues = portfolio_manager.add_or_update_position(ticker, shares)

        if not success:
            return jsonify({"error": "Validation failed", "issues": issues}), 400

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

        return (
            jsonify(
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
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Add position API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio/positions/<ticker>", methods=["PUT"])
@require_api_key
def update_portfolio_position(ticker: str) -> Tuple[Response, int]:
    """
    Update shares for a specific position
    ---
    tags:
      - portfolio
    security:
      - Bearer: []
    parameters:
      - name: ticker
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            shares:
              type: number
              description: Number of shares to hold
          required:
            - shares
    responses:
      200:
        description: Position updated
      400:
        description: Invalid request
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
        data = request.get_json() or {}
        shares = data.get("shares")

        if shares is None:
            return jsonify({"error": "Missing shares"}), 400

        success, issues = portfolio_manager.add_or_update_position(ticker, shares)

        if not success:
            return jsonify({"error": "Validation failed", "issues": issues}), 400

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

        return (
            jsonify(
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
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Update position API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/portfolio/positions/<ticker>", methods=["DELETE"])
@require_api_key
def delete_portfolio_position(ticker: str) -> Tuple[Response, int]:
    """
    Remove a position from the portfolio
    ---
    tags:
      - portfolio
    security:
      - Bearer: []
    parameters:
      - name: ticker
        in: path
        type: string
        required: true
    responses:
      200:
        description: Position deleted
      400:
        description: Could not remove position
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
        success, issues = portfolio_manager.remove_position(ticker)

        if not success:
            return (
                jsonify({"error": "Could not remove position", "issues": issues}),
                400,
            )

        return (
            jsonify(
                {
                    "message": f"Position {ticker.upper()} removed successfully",
                    "updated_at": datetime.now().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Delete position API error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TICKER DATA ENDPOINTS
# ============================================================================


@api_bp.route("/tickers/<ticker>", methods=["GET"])
@require_api_key
def get_ticker_data(ticker: str) -> Tuple[Response, int]:
    """
    Get detailed data for a specific ticker
    ---
    tags:
      - tickers
    security:
      - Bearer: []
    parameters:
      - name: ticker
        in: path
        type: string
        required: true
      - name: period
        in: query
        type: string
        description: Data period (default 3mo)
      - name: indicators
        in: query
        type: string
        description: Include technical indicators (true/false)
    responses:
      200:
        description: Ticker data retrieved
      401:
        description: Unauthorized
      404:
        description: No data available
      500:
        description: Server error
    """
    try:
        period = request.args.get("period", "3mo")
        include_indicators = request.args.get("indicators", "false").lower() == "true"

        data = dm.get_stock_data(ticker, period=period)

        if data.empty:
            return jsonify({"error": f"No data available for {ticker}"}), 404

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
                response_data["indicators"] = {"error": "Could not calculate indicators"}

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Ticker API error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# RISK ANALYSIS ENDPOINTS
# ============================================================================


@api_bp.route("/risk-report", methods=["GET"])
@require_api_key
def get_risk_report() -> Tuple[Response, int]:
    """
    Get comprehensive risk report
    ---
    tags:
      - risk
    security:
      - Bearer: []
    responses:
      200:
        description: Risk report retrieved
      400:
        description: No portfolio positions configured
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
        tickers = portfolio_manager.get_tickers()
        if not tickers:
            return jsonify({"error": "No portfolio positions configured"}), 400

        portfolio_data = dm.get_multiple_stocks(tickers, period="1y")

        if not portfolio_data:
            return jsonify({"error": "No portfolio data available"}), 500

        current_prices = {}
        for ticker in tickers:
            if ticker in portfolio_data and not portfolio_data[ticker].empty:
                current_prices[ticker] = portfolio_data[ticker]["Close"].iloc[-1]
            else:
                current_prices[ticker] = 0

        weights = portfolio_manager.get_weights(current_prices)
        total_value = portfolio_manager.get_total_value(current_prices)

        risk_report_data = portfolio_analyzer.generate_risk_report(
            portfolio_data, weights, total_value
        )

        return jsonify(risk_report_data), 200

    except Exception as e:
        logger.error(f"Risk report API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/correlation", methods=["GET"])
@require_api_key
def get_correlation_matrix() -> Tuple[Response, int]:
    """
    Get correlation matrix for portfolio
    ---
    tags:
      - risk
    security:
      - Bearer: []
    responses:
      200:
        description: Correlation matrix retrieved
      400:
        description: No portfolio positions configured
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
        tickers = portfolio_manager.get_tickers()
        if not tickers:
            return jsonify({"error": "No portfolio positions configured"}), 400

        portfolio_data = dm.get_multiple_stocks(tickers, period="6mo")

        if not portfolio_data:
            return jsonify({"error": "No portfolio data available"}), 500

        corr_matrix = portfolio_analyzer.calculate_correlation_matrix(portfolio_data)

        if corr_matrix.empty:
            return jsonify({"error": "Could not calculate correlation matrix"}), 500

        correlation_data = {
            "tickers": corr_matrix.columns.tolist(),
            "matrix": corr_matrix.values.tolist(),
            "average_correlation": corr_matrix.values[
                np.triu_indices_from(corr_matrix.values, k=1)
            ].mean(),
            "max_correlation": corr_matrix.values[
                np.triu_indices_from(corr_matrix.values, k=1)
            ].max(),
            "min_correlation": corr_matrix.values[
                np.triu_indices_from(corr_matrix.values, k=1)
            ].min(),
        }

        return jsonify(correlation_data), 200

    except Exception as e:
        logger.error(f"Correlation API error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/optimization", methods=["POST"])
@require_api_key
def optimize_portfolio() -> Tuple[Response, int]:
    """
    Optimize portfolio weights
    ---
    tags:
      - risk
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: false
        schema:
          type: object
          properties:
            risk_tolerance:
              type: number
              description: Target portfolio volatility (0.0-1.0)
              default: 0.15
            target_return:
              type: number
              description: Target annual return (optional)
    responses:
      200:
        description: Portfolio optimized
      400:
        description: No portfolio positions configured
      401:
        description: Unauthorized
      500:
        description: Server error
    """
    try:
        tickers = portfolio_manager.get_tickers()
        if not tickers:
            return jsonify({"error": "No portfolio positions configured"}), 400

        data = request.get_json() or {}
        risk_tolerance = data.get("risk_tolerance", 0.15)
        target_return = data.get("target_return")

        portfolio_data = dm.get_multiple_stocks(tickers, period="1y")

        if not portfolio_data:
            return jsonify({"error": "No portfolio data available"}), 500

        current_prices = {}
        for ticker in tickers:
            if ticker in portfolio_data and not portfolio_data[ticker].empty:
                current_prices[ticker] = portfolio_data[ticker]["Close"].iloc[-1]
            else:
                current_prices[ticker] = 0

        current_weights = portfolio_manager.get_weights(current_prices)

        optimized_weights = portfolio_analyzer.optimize_portfolio(
            portfolio_data,
            current_weights,
            target_return=target_return,
            risk_tolerance=risk_tolerance,
        )

        current_metrics = portfolio_analyzer.analyze_portfolio(portfolio_data, current_weights)
        optimized_metrics = portfolio_analyzer.analyze_portfolio(portfolio_data, optimized_weights)

        return (
            jsonify(
                {
                    "current_weights": current_weights,
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
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Optimization API error: {e}")
        return jsonify({"error": str(e)}), 500


# Initialize background update on first import
def initialize_signals() -> None:
    """Initialize signals and portfolio on startup"""
    global current_signals, last_update

    try:
        logger.info("Initializing system...")

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
            portfolio_manager.initialize_from_config(cast(Dict[str, float], initial_positions))
            logger.info("Portfolio initialized")
        except Exception as e:
            logger.warning(f"Could not initialize portfolio: {e}")

        logger.info("Initializing trading signals")

        portfolio_tickers = portfolio_manager.get_tickers()
        if not portfolio_tickers:
            portfolio_tickers = Config.PORTFOLIO_TICKERS()[:5]

        portfolio_data = dm.get_multiple_stocks(portfolio_tickers[:5], period="3mo")

        if portfolio_data:
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

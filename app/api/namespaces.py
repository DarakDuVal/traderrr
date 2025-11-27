"""
app/api/namespaces.py
Flask-RESTX namespaces and API models for OpenAPI documentation
"""

from flask_restx import Namespace, fields

# ============================================================================
# NAMESPACE DEFINITIONS
# ============================================================================

health_ns = Namespace("health", description="System health and status checks")

signals_ns = Namespace("signals", description="Trading signal generation and retrieval")

portfolio_ns = Namespace("portfolio", description="Portfolio management and position tracking")

performance_ns = Namespace(
    "portfolio-performance", description="Portfolio performance metrics and analysis"
)

risk_ns = Namespace("risk", description="Risk analysis and portfolio optimization")

tickers_ns = Namespace("tickers", description="Ticker data and technical indicators")

# ============================================================================
# SHARED RESPONSE MODELS
# ============================================================================

# Health Check Models
health_response = health_ns.model(
    "HealthResponse",
    {
        "status": fields.String(
            required=True,
            enum=["healthy", "degraded", "unhealthy"],
            description="Overall system health status",
        ),
        "timestamp": fields.String(description="Health check timestamp (ISO8601)"),
        "database": fields.String(description="Database connection status"),
        "last_update": fields.String(description="Last system update timestamp (ISO8601)"),
        "signal_count": fields.Integer(description="Number of active trading signals"),
        "version": fields.String(description="API version"),
        "warning": fields.String(description="Optional warning message"),
    },
)

# Trading Signal Models
signal_model = signals_ns.model(
    "TradingSignal",
    {
        "ticker": fields.String(
            required=True, description="Stock ticker symbol (e.g., AAPL, MSFT)"
        ),
        "signal_type": fields.String(
            required=True,
            enum=["BUY", "SELL", "HOLD", "STRONG_BUY", "STRONG_SELL"],
            description="Type of trading signal",
        ),
        "confidence": fields.Float(description="Confidence level (0.0 - 1.0, higher is better)"),
        "entry_price": fields.Float(description="Recommended entry price for the position"),
        "stop_loss": fields.Float(description="Stop loss price for risk management"),
        "target_price": fields.Float(description="Target price for take profit"),
        "regime": fields.String(
            enum=[
                "TRENDING_UP",
                "TRENDING_DOWN",
                "MEAN_REVERTING",
                "SIDEWAYS",
                "HIGH_VOLATILITY",
            ],
            description="Current market regime",
        ),
        "reasons": fields.List(
            fields.String, description="Technical or fundamental reasons for the signal"
        ),
        "timestamp": fields.String(description="Signal generation timestamp (ISO8601)"),
    },
)

signals_response = signals_ns.model(
    "SignalsResponse",
    {
        "signals": fields.List(fields.Nested(signal_model), description="Array of trading signals"),
        "last_update": fields.String(description="Last signal update timestamp (ISO8601)"),
        "total_count": fields.Integer(description="Total number of signals"),
    },
)

signal_stats = signals_ns.model(
    "SignalStatistics",
    {
        "total_signals": fields.Integer(description="Total signals generated"),
        "buy_signals": fields.Integer(description="Count of BUY signals"),
        "sell_signals": fields.Integer(description="Count of SELL signals"),
        "hold_signals": fields.Integer(description="Count of HOLD signals"),
        "average_confidence": fields.Float(description="Average signal confidence"),
        "success_rate": fields.Float(description="Historical success rate"),
        "period": fields.String(description="Analysis period"),
        "last_updated": fields.String(description="Last update timestamp"),
    },
)

# Portfolio Models
position_request = portfolio_ns.model(
    "PositionRequest",
    {
        "ticker": fields.String(required=True, description="Stock ticker symbol"),
        "shares": fields.Float(required=True, description="Number of shares to hold"),
    },
)

position_response = portfolio_ns.model(
    "Position",
    {
        "ticker": fields.String(description="Stock ticker symbol"),
        "shares": fields.Float(description="Number of shares held"),
        "current_price": fields.Float(description="Current market price per share"),
        "position_value": fields.Float(description="Total position value (shares × price)"),
        "weight": fields.Float(description="Portfolio weight percentage (0.0 - 1.0)"),
    },
)

portfolio_metrics = portfolio_ns.model(
    "PortfolioMetrics",
    {
        "volatility": fields.Float(description="Portfolio volatility (annualized)"),
        "sharpe_ratio": fields.Float(description="Sharpe ratio (risk-adjusted return)"),
        "max_drawdown": fields.Float(description="Maximum drawdown percentage"),
        "value_at_risk": fields.Float(description="Value at risk (95% confidence)"),
        "expected_shortfall": fields.Float(description="Expected shortfall (CVaR)"),
    },
)

position_risk = portfolio_ns.model(
    "PositionRisk",
    {
        "ticker": fields.String(description="Stock ticker symbol"),
        "weight": fields.Float(description="Portfolio weight"),
        "position_size": fields.Float(description="Position value"),
        "risk_contribution": fields.Float(description="Risk contribution to portfolio"),
        "liquidity_score": fields.Float(description="Liquidity score (0-1)"),
        "concentration_risk": fields.Float(description="Concentration risk factor"),
    },
)

portfolio_response = portfolio_ns.model(
    "PortfolioOverview",
    {
        "portfolio_metrics": fields.Nested(
            portfolio_metrics, description="Overall portfolio risk metrics"
        ),
        "position_risks": fields.List(
            fields.Nested(position_risk), description="Per-position risk analysis"
        ),
        "portfolio_overview": fields.Raw(description="Price and weight data for each position"),
        "total_value": fields.Float(description="Total portfolio value in base currency"),
        "updated_at": fields.String(description="Last update timestamp"),
    },
)

# Performance Models
performance_record = performance_ns.model(
    "PerformanceRecord",
    {
        "date": fields.String(description="Record date (ISO8601)"),
        "portfolio_value": fields.Float(description="Portfolio value on this date"),
        "daily_return": fields.Float(description="Daily return as percentage"),
        "volatility": fields.Float(description="Daily volatility metric"),
        "sharpe_ratio": fields.Float(description="Sharpe ratio for the period"),
        "max_drawdown": fields.Float(description="Maximum drawdown up to this date"),
    },
)

performance_summary = performance_ns.model(
    "PerformanceSummary",
    {
        "period_days": fields.Integer(description="Number of days in analysis period"),
        "summary": fields.Raw(description="Aggregated performance statistics"),
    },
)

performance_metrics_model = performance_ns.model(
    "PerformanceMetrics",
    {
        "period_days": fields.Integer(description="Analysis period in days"),
        "total_return": fields.Float(description="Total return percentage"),
        "annualized_return": fields.Float(description="Annualized return"),
        "volatility": fields.Float(description="Annualized volatility"),
        "sharpe_ratio": fields.Float(description="Sharpe ratio"),
        "max_drawdown": fields.Float(description="Maximum drawdown"),
        "win_rate": fields.Float(description="Winning days percentage"),
        "worst_day": fields.Float(description="Worst single day return"),
        "best_day": fields.Float(description="Best single day return"),
    },
)

# Risk Analysis Models
correlation_matrix = risk_ns.model(
    "CorrelationMatrix",
    {
        "tickers": fields.List(fields.String, description="Ordered list of tickers in matrix"),
        "matrix": fields.List(
            fields.List(fields.Float), description="Correlation matrix (2D array)"
        ),
        "average_correlation": fields.Float(description="Average correlation between assets"),
        "max_correlation": fields.Float(description="Maximum correlation value"),
        "min_correlation": fields.Float(description="Minimum correlation value"),
    },
)

risk_report = risk_ns.model(
    "RiskReport",
    {
        "portfolio_var": fields.Float(description="Portfolio Value at Risk"),
        "portfolio_es": fields.Float(description="Portfolio Expected Shortfall"),
        "concentration_risk": fields.Float(description="Concentration risk metric"),
        "correlation_risk": fields.Float(description="Correlation risk metric"),
        "position_risks": fields.List(
            fields.Nested(position_risk), description="Individual position risks"
        ),
        "recommendations": fields.List(
            fields.String, description="Risk mitigation recommendations"
        ),
    },
)

optimization_request = risk_ns.model(
    "OptimizationRequest",
    {
        "risk_tolerance": fields.Float(
            default=0.15, description="Target portfolio volatility (0.0-1.0)"
        ),
        "target_return": fields.Float(description="Target annual return (optional)"),
    },
)

optimization_response = risk_ns.model(
    "OptimizationResult",
    {
        "current_weights": fields.Raw(description="Current portfolio weights"),
        "optimized_weights": fields.Raw(description="Optimized portfolio weights"),
        "current_metrics": fields.Nested(
            portfolio_metrics, description="Current portfolio metrics"
        ),
        "optimized_metrics": fields.Nested(
            portfolio_metrics, description="Optimized portfolio metrics"
        ),
        "parameters": fields.Raw(description="Optimization parameters used"),
    },
)

# Ticker Data Models
ticker_data = tickers_ns.model(
    "TickerData",
    {
        "ticker": fields.String(description="Stock ticker symbol"),
        "period": fields.String(description="Data period (e.g., 3mo, 1y)"),
        "data_points": fields.Integer(description="Number of data points"),
        "date_range": fields.Raw(description="Start and end dates"),
        "current_price": fields.Float(description="Current stock price"),
        "daily_change": fields.Float(description="Daily change percentage"),
        "volume": fields.Float(description="Trading volume"),
        "indicators": fields.Raw(description="Technical indicators (if requested)"),
    },
)

# Error Model
error_response = {
    "error": fields.String(description="Error message"),
    "timestamp": fields.String(description="Error timestamp"),
    "details": fields.String(description="Additional error details"),
}

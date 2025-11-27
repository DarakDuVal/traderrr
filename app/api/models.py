"""
app/api/models.py - Data models for API responses
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class MarketRegime(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    MEAN_REVERTING = "MEAN_REVERTING"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"


@dataclass
class TradingSignalResponse:
    ticker: str
    signal_type: str
    confidence: float
    entry_price: float
    stop_loss: float
    target_price: float
    regime: str
    reasons: List[str]
    timestamp: str


@dataclass
class PortfolioMetricsResponse:
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    value_at_risk: float
    expected_shortfall: float
    updated_at: str


@dataclass
class PositionRiskResponse:
    ticker: str
    weight: float
    position_size: float
    risk_contribution: float
    liquidity_score: float
    concentration_risk: float


@dataclass
class HealthResponse:
    status: str
    timestamp: str
    database: str
    last_update: Optional[str]
    signal_count: int
    version: str


@dataclass
class ErrorResponse:
    error: str
    timestamp: str
    details: Optional[str] = None


def serialize_signal(signal: Any) -> dict:
    """Convert TradingSignal object to dictionary"""
    return {
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


def serialize_portfolio_metrics(metrics: Any) -> dict:
    """Convert PortfolioMetrics object to dictionary"""
    return {
        "volatility": metrics.volatility,
        "sharpe_ratio": metrics.sharpe_ratio,
        "max_drawdown": metrics.max_drawdown,
        "value_at_risk": metrics.value_at_risk,
        "expected_shortfall": metrics.expected_shortfall,
        "beta": metrics.beta,
        "alpha": metrics.alpha,
    }


def serialize_position_risk(position_risk: Any) -> dict:
    """Convert PositionRisk object to dictionary"""
    return {
        "ticker": position_risk.ticker,
        "weight": position_risk.weight,
        "position_size": position_risk.position_size,
        "daily_var": position_risk.daily_var,
        "risk_contribution": position_risk.contribution_to_risk,
        "liquidity_score": position_risk.liquidity_score,
        "concentration_risk": position_risk.concentration_risk,
    }

"""Pydantic schemas for risk endpoints."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RiskMetricsResponse(BaseModel):
    var_95: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    volatility: Optional[float] = None
    sortino_ratio: Optional[float] = None


class CorrelationResponse(BaseModel):
    tickers: List[str]
    matrix: List[List[float]]


class StressTestRequest(BaseModel):
    scenario: str = Field(..., description="Scenario name or description")
    market_change: float = Field(..., description="Market change as decimal (-0.20 = -20%)")
    volatility_multiplier: float = Field(1.5, gt=0, description="Volatility multiplier")


class StressTestResponse(BaseModel):
    scenario: str
    portfolio_impact: float
    positions_impact: Dict[str, float]

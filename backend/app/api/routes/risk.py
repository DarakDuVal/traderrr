"""
Risk routes — /api/v1/risk
"""

import logging

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.risk import (
    CorrelationResponse,
    RiskMetricsResponse,
    StressTestRequest,
    StressTestResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/metrics", response_model=RiskMetricsResponse)  # type: ignore[misc, untyped-decorator]
async def get_risk_metrics(
    current_user: User = Depends(get_current_user),
) -> RiskMetricsResponse:
    """Return risk metrics (VaR, Sharpe ratio, max drawdown)."""
    # Placeholder — real implementation delegates to core.portfolio_analyzer
    return RiskMetricsResponse(
        var_95=None,
        sharpe_ratio=None,
        max_drawdown=None,
        volatility=None,
        sortino_ratio=None,
    )


@router.get("/correlation", response_model=CorrelationResponse)  # type: ignore[misc, untyped-decorator]
async def get_correlation(
    current_user: User = Depends(get_current_user),
) -> CorrelationResponse:
    """Return correlation matrix for portfolio tickers."""
    return CorrelationResponse(tickers=[], matrix=[])


@router.post("/stress-test", response_model=StressTestResponse)  # type: ignore[misc, untyped-decorator]
async def stress_test(
    body: StressTestRequest,
    current_user: User = Depends(get_current_user),
) -> StressTestResponse:
    """Run a stress test scenario against the portfolio."""
    return StressTestResponse(
        scenario=body.scenario,
        portfolio_impact=0.0,
        positions_impact={},
    )

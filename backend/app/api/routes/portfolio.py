"""
Portfolio routes — /api/v1/portfolio
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.portfolio import PortfolioPosition
from app.models.trading import PortfolioPerformance
from app.models.user import User
from app.schemas.portfolio import (
    PerformanceResponse,
    PositionCreate,
    PositionResponse,
    PositionUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[PositionResponse])
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PositionResponse]:
    """Return all portfolio positions for the current user."""
    result = await db.execute(
        select(PortfolioPosition).where(PortfolioPosition.user_id == current_user.id)
    )
    positions = result.scalars().all()
    return [PositionResponse.model_validate(p) for p in positions]


@router.post("/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def add_position(
    body: PositionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionResponse:
    """Add a new portfolio position."""
    position = PortfolioPosition(
        user_id=current_user.id,
        ticker=body.ticker.upper(),
        shares=body.shares,
    )
    db.add(position)
    await db.flush()
    await db.refresh(position)
    return PositionResponse.model_validate(position)


@router.put("/positions/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: int,
    body: PositionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionResponse:
    """Update an existing portfolio position."""
    result = await db.execute(
        select(PortfolioPosition).where(
            PortfolioPosition.id == position_id,
            PortfolioPosition.user_id == current_user.id,
        )
    )
    position = result.scalar_one_or_none()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    if body.shares is not None:
        position.shares = body.shares
    await db.flush()
    await db.refresh(position)
    return PositionResponse.model_validate(position)


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a portfolio position."""
    result = await db.execute(
        select(PortfolioPosition).where(
            PortfolioPosition.id == position_id,
            PortfolioPosition.user_id == current_user.id,
        )
    )
    position = result.scalar_one_or_none()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    await db.delete(position)


@router.get("/performance", response_model=list[PerformanceResponse])
async def get_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PerformanceResponse]:
    """Return portfolio performance metrics."""
    result = await db.execute(
        select(PortfolioPerformance)
        .where(PortfolioPerformance.user_id == current_user.id)
        .order_by(PortfolioPerformance.date.desc())
        .limit(30)
    )
    records = result.scalars().all()
    return [PerformanceResponse.model_validate(r) for r in records]

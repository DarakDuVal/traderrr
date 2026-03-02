"""
Signals routes — /api/v1/signals
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.trading import SignalHistory
from app.models.user import User
from app.schemas.signals import SignalFilter, SignalListResponse, SignalResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=SignalListResponse)  # type: ignore[misc, untyped-decorator]
async def list_signals(
    ticker: Optional[str] = Query(None),
    signal_type: Optional[str] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SignalListResponse:
    """List signals with optional filters."""
    query = select(SignalHistory).where(SignalHistory.user_id == current_user.id)
    if ticker:
        query = query.where(SignalHistory.ticker == ticker.upper())
    if signal_type:
        query = query.where(SignalHistory.signal_type == signal_type.upper())
    if min_confidence is not None:
        query = query.where(SignalHistory.confidence >= min_confidence)
    query = query.order_by(SignalHistory.date.desc()).limit(100)

    result = await db.execute(query)
    signals = result.scalars().all()

    count_q = (
        select(func.count())
        .select_from(SignalHistory)
        .where(SignalHistory.user_id == current_user.id)
    )
    total = (await db.execute(count_q)).scalar() or 0

    return SignalListResponse(
        signals=[SignalResponse.model_validate(s) for s in signals],
        total=total,
    )


@router.get("/{ticker}", response_model=SignalListResponse)  # type: ignore[misc, untyped-decorator]
async def signals_by_ticker(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SignalListResponse:
    """Get signals for a specific ticker."""
    query = (
        select(SignalHistory)
        .where(
            SignalHistory.user_id == current_user.id,
            SignalHistory.ticker == ticker.upper(),
        )
        .order_by(SignalHistory.date.desc())
        .limit(100)
    )
    result = await db.execute(query)
    signals = result.scalars().all()
    return SignalListResponse(
        signals=[SignalResponse.model_validate(s) for s in signals],
        total=len(signals),
    )


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)  # type: ignore[misc, untyped-decorator]
async def generate_signals(
    admin_user: User = Depends(require_role("admin")),
) -> dict:
    """Trigger signal generation (admin only). Dispatches Celery task."""
    try:
        from app.workers.signals import generate_all_signals

        task = generate_all_signals.delay()
        return {"detail": "Signal generation started", "task_id": task.id}
    except Exception as exc:
        logger.error("Failed to dispatch signal generation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start signal generation",
        )

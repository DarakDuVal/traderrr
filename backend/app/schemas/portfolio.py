"""Pydantic schemas for portfolio endpoints."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class PositionCreate(BaseModel):
    ticker: str = Field(..., max_length=10)
    shares: float = Field(..., gt=0)


class PositionUpdate(BaseModel):
    shares: Optional[float] = Field(None, gt=0)


class PositionResponse(BaseModel):
    id: int
    ticker: str
    shares: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PerformanceResponse(BaseModel):
    date: date
    portfolio_value: float
    daily_return: float
    volatility: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None

    model_config = {"from_attributes": True}

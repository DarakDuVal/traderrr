"""Pydantic schemas for signal endpoints."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class SignalFilter(BaseModel):
    ticker: Optional[str] = None
    signal_type: Optional[str] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=1)
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class SignalResponse(BaseModel):
    id: int
    ticker: str
    date: date
    signal_type: str
    signal_value: float
    confidence: float
    entry_price: float
    target_price: float
    stop_loss: float
    regime: Optional[str] = None
    reasons: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    signals: List[SignalResponse]
    total: int

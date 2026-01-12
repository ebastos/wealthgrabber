"""Data models for wealthgrabber output formatting."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AccountData:
    """Container for formatted account data."""

    description: str
    number: str
    value: float
    currency: str


@dataclass
class ActivityData:
    """Container for formatted activity data."""

    date: str  # YYYY-MM-DD format
    activity_type: str
    description: str
    amount: float
    currency: str
    sign: str  # "+" or "-"
    account_label: Optional[str] = None


@dataclass
class PositionData:
    """Container for formatted position data."""

    symbol: str
    name: str
    quantity: float
    market_value: float
    book_value: float
    currency: str
    pnl: float
    pnl_pct: float
    account_label: Optional[str] = None

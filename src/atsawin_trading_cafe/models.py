"""Core data models for Trading Cafe."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeOutcome(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    OPEN = "OPEN"


@dataclass(slots=True)
class TradeEntry:
    symbol: str
    side: TradeSide
    entry_price: float
    volume: float
    opened_at: datetime
    outcome: TradeOutcome = TradeOutcome.OPEN
    exit_price: float | None = None
    closed_at: datetime | None = None
    pnl: float = 0.0
    risk_percent: float = 0.0
    setup: str = ""
    emotion: str = ""
    note: str = ""


@dataclass(slots=True)
class JournalSummary:
    trade_count: int
    win_count: int
    loss_count: int
    breakeven_count: int
    total_pnl: float
    win_rate: float
    average_risk_percent: float
    symbols: list[str] = field(default_factory=list)
    setups: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class BotStatus:
    name: str
    state: str
    last_seen: datetime | None = None
    error: str = ""
    raw_log: str = ""


@dataclass(slots=True)
class RiskWarning:
    code: str
    severity: str
    message: str

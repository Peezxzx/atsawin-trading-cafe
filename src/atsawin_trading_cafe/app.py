"""Optional FastAPI app for Atsawin Trading Cafe."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

try:
    from fastapi import FastAPI
except ImportError:  # keep core package usable without API deps
    FastAPI = None  # type: ignore[assignment]

from .journal import format_summary_thai, summarize_trades
from .models import TradeEntry, TradeOutcome, TradeSide
from .prompts import ATSAWIN_TRADING_CAFE_SYSTEM_PROMPT
from .risk import check_trade_risk

if FastAPI is not None:
    app = FastAPI(title="Atsawin Trading Cafe", version="0.1.0")
else:
    app = None


def _trade_from_payload(payload: dict) -> TradeEntry:
    return TradeEntry(
        symbol=str(payload["symbol"]).upper(),
        side=TradeSide(str(payload["side"]).upper()),
        entry_price=float(payload["entry_price"]),
        volume=float(payload.get("volume", 0.0)),
        opened_at=datetime.fromisoformat(payload.get("opened_at", datetime.now().isoformat())),
        outcome=TradeOutcome(str(payload.get("outcome", "OPEN")).upper()),
        exit_price=float(payload["exit_price"]) if payload.get("exit_price") is not None else None,
        closed_at=datetime.fromisoformat(payload["closed_at"]) if payload.get("closed_at") else None,
        pnl=float(payload.get("pnl", 0.0)),
        risk_percent=float(payload.get("risk_percent", 0.0)),
        setup=str(payload.get("setup", "")),
        emotion=str(payload.get("emotion", "")),
        note=str(payload.get("note", "")),
    )


if app is not None:
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "atsawin-trading-cafe"}

    @app.get("/context")
    def context() -> dict[str, str]:
        return {"system_prompt": ATSAWIN_TRADING_CAFE_SYSTEM_PROMPT}

    @app.post("/journal/summarize")
    def journal_summarize(payload: dict) -> dict:
        trades = [_trade_from_payload(item) for item in payload.get("trades", [])]
        summary = summarize_trades(trades)
        return {"summary": asdict(summary), "message_thai": format_summary_thai(summary)}

    @app.post("/risk/check")
    def risk_check(payload: dict) -> dict:
        trades = [_trade_from_payload(item) for item in payload.get("trades", [])]
        warnings = check_trade_risk(
            trades,
            max_risk_percent=float(payload.get("max_risk_percent", 5.0)),
            overtrade_limit=int(payload.get("overtrade_limit", 10)),
            loss_streak_limit=int(payload.get("loss_streak_limit", 3)),
        )
        return {"warnings": [asdict(warning) for warning in warnings]}

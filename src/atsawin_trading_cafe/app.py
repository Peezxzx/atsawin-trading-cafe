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
from .mt5_contract import MarketSnapshot, SymbolSpec, build_pretrade_plan, plan_to_report
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

    @app.post("/ea/pretrade-plan")
    def ea_pretrade_plan(payload: dict) -> dict:
        """Calculate a Trading Cafe pre-trade plan from EA/bridge signal data."""
        signal = payload.get("signal", payload)
        market_data = payload.get("market", {})
        spec_data = payload.get("symbol_spec", {})

        symbol = str(signal.get("mt5_symbol") or market_data.get("symbol") or spec_data.get("symbol") or "XAUUSDm")
        market = MarketSnapshot(
            symbol=symbol,
            bid=float(market_data.get("bid", signal.get("entry_price", 0.0))),
            ask=float(market_data.get("ask", signal.get("entry_price", 0.0))),
            balance=float(market_data.get("balance", payload.get("balance", 0.0))),
            equity=float(market_data["equity"]) if market_data.get("equity") is not None else None,
        )
        spec = SymbolSpec(
            symbol=symbol,
            tick_value=float(spec_data.get("tick_value", 1.0)),
            tick_size=float(spec_data.get("tick_size", 0.01)),
            volume_min=float(spec_data.get("volume_min", 0.01)),
            volume_max=float(spec_data.get("volume_max", payload.get("max_lot", 1.0))),
            volume_step=float(spec_data.get("volume_step", 0.01)),
            point=float(spec_data.get("point", 0.001)),
        )
        plan = build_pretrade_plan(
            signal,
            market,
            spec,
            risk_percent=float(payload.get("risk_percent", 2.5)),
            max_lot=float(payload.get("max_lot", 1.0)),
            min_confidence=float(payload.get("min_confidence", 0.30)),
            max_spread_points=float(payload.get("max_spread_points", 500.0)),
            min_actual_rr=float(payload.get("min_actual_rr", 1.0)),
        )
        return plan_to_report(plan, signal)

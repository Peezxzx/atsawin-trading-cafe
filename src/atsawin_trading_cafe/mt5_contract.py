"""EA/MT5 integration contract for Atsawin Trading Cafe.

This module is intentionally independent from MetaTrader5 so it can be tested
without MT5 installed. The live adapter (`mt5_live.py`) supplies account, tick,
and symbol spec data from MT5.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SIGNAL_DIR = Path(r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common\Files\atsawin")
DEFAULT_SIGNAL_FILE = "latest_signal.json"
DEFAULT_REPORT_FILE = "trading_cafe_report.json"


@dataclass(slots=True)
class SymbolSpec:
    symbol: str
    tick_value: float
    tick_size: float
    volume_min: float = 0.01
    volume_max: float = 1.0
    volume_step: float = 0.01
    point: float = 0.001


@dataclass(slots=True)
class MarketSnapshot:
    symbol: str
    bid: float
    ask: float
    balance: float
    equity: float | None = None


@dataclass(slots=True)
class PreTradePlan:
    allowed: bool
    action: str
    symbol: str
    mt5_symbol: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    bridge_rr: float
    actual_rr: float
    calculated_lot: float
    risk_percent: float
    risk_amount: float
    spread_points: float
    warnings: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def atomic_write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def read_signal(signal_dir: str | Path = DEFAULT_SIGNAL_DIR, signal_file: str = DEFAULT_SIGNAL_FILE) -> dict[str, Any]:
    path = Path(signal_dir) / signal_file
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_side(value: Any) -> str:
    return str(value or "hold").strip().lower()


def signal_symbols(payload: dict[str, Any]) -> tuple[str, str]:
    base = str(payload.get("symbol") or "").strip().upper()
    mt5_symbol = str(payload.get("mt5_symbol") or base).strip()
    return base, mt5_symbol


def validate_signal_payload(payload: dict[str, Any]) -> list[str]:
    """Return validation warnings for a bridge signal payload."""
    warnings: list[str] = []
    side = normalize_side(payload.get("signal"))
    if side not in {"buy", "sell", "hold"}:
        warnings.append("invalid_signal")

    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = -1.0
    if not 0.0 <= confidence <= 1.0:
        warnings.append("invalid_confidence")

    if side in {"buy", "sell"}:
        sl = float(payload.get("stop_loss") or 0.0)
        tp = float(payload.get("take_profit") or 0.0)
        if sl <= 0 or tp <= 0:
            warnings.append("invalid_sl_tp")
        elif side == "buy" and sl >= tp:
            warnings.append("invalid_buy_geometry")
        elif side == "sell" and sl <= tp:
            warnings.append("invalid_sell_geometry")
    return warnings


def calculate_lot_size(
    *,
    balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss: float,
    spec: SymbolSpec,
    max_lot: float | None = None,
) -> float:
    """Calculate MT5 lot size from risk percent and SL distance."""
    if balance <= 0 or risk_percent <= 0 or entry_price <= 0 or stop_loss <= 0:
        return spec.volume_min
    if spec.tick_value <= 0 or spec.tick_size <= 0 or spec.volume_step <= 0:
        return spec.volume_min

    risk_amount = balance * risk_percent / 100.0
    stop_distance = abs(entry_price - stop_loss)
    loss_per_lot = (stop_distance / spec.tick_size) * spec.tick_value
    if loss_per_lot <= 0:
        return spec.volume_min

    raw_lot = risk_amount / loss_per_lot
    cap = spec.volume_max if max_lot is None else min(spec.volume_max, max_lot)
    lot = max(spec.volume_min, min(cap, raw_lot))
    lot = math.floor(lot / spec.volume_step) * spec.volume_step
    return round(max(spec.volume_min, lot), 2)


def calculate_actual_rr(side: str, *, bid: float, ask: float, stop_loss: float, take_profit: float) -> float:
    side = normalize_side(side)
    if side == "buy":
        risk = ask - stop_loss
        reward = take_profit - ask
    elif side == "sell":
        risk = stop_loss - bid
        reward = bid - take_profit
    else:
        return 0.0
    if risk <= 0 or reward <= 0:
        return 0.0
    return round(reward / risk, 4)


def build_pretrade_plan(
    signal_payload: dict[str, Any],
    market: MarketSnapshot,
    spec: SymbolSpec,
    *,
    risk_percent: float = 2.5,
    max_lot: float = 1.0,
    min_confidence: float = 0.30,
    max_spread_points: float = 500.0,
    min_actual_rr: float = 1.0,
) -> PreTradePlan:
    """Build a safe pre-trade plan from bridge signal + live MT5 market data.

    The EA still owns actual execution. Trading Cafe calculates and explains the
    plan so dashboard/Telegram can show what will happen before the EA acts.
    """
    side = normalize_side(signal_payload.get("signal"))
    base_symbol, mt5_symbol = signal_symbols(signal_payload)
    confidence = float(signal_payload.get("confidence") or 0.0)
    stop_loss = float(signal_payload.get("stop_loss") or 0.0)
    take_profit = float(signal_payload.get("take_profit") or 0.0)
    bridge_entry = float(signal_payload.get("entry_price") or 0.0)
    bridge_rr = float(signal_payload.get("risk_reward_ratio") or 0.0)
    reasons = [str(item) for item in signal_payload.get("reasons", [])]
    warnings = validate_signal_payload(signal_payload)

    spread_points = round((market.ask - market.bid) / spec.point, 1) if spec.point > 0 else 0.0
    actual_entry = market.ask if side == "buy" else market.bid if side == "sell" else bridge_entry
    actual_rr = calculate_actual_rr(side, bid=market.bid, ask=market.ask, stop_loss=stop_loss, take_profit=take_profit)
    lot = 0.0
    risk_amount = round(market.balance * risk_percent / 100.0, 2) if risk_percent > 0 else 0.0

    if side in {"buy", "sell"} and not warnings:
        lot = calculate_lot_size(
            balance=market.balance,
            risk_percent=risk_percent,
            entry_price=actual_entry,
            stop_loss=stop_loss,
            spec=spec,
            max_lot=max_lot,
        )

    if side == "hold":
        warnings.append("signal_is_hold")
    if confidence < min_confidence:
        warnings.append("confidence_below_minimum")
    if spread_points > max_spread_points:
        warnings.append("spread_too_high")
    if side in {"buy", "sell"} and actual_rr < min_actual_rr:
        warnings.append("actual_rr_below_minimum")
    if mt5_symbol and market.symbol and mt5_symbol != market.symbol:
        warnings.append("symbol_mismatch")

    allowed = side in {"buy", "sell"} and not warnings

    return PreTradePlan(
        allowed=allowed,
        action=side,
        symbol=base_symbol,
        mt5_symbol=mt5_symbol,
        confidence=confidence,
        entry_price=round(actual_entry, 5),
        stop_loss=stop_loss,
        take_profit=take_profit,
        bridge_rr=bridge_rr,
        actual_rr=actual_rr,
        calculated_lot=lot,
        risk_percent=risk_percent,
        risk_amount=risk_amount,
        spread_points=spread_points,
        warnings=warnings,
        reasons=reasons,
    )


def plan_to_report(plan: PreTradePlan, signal_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "trading_cafe_report_v1",
        "timestamp": plan.timestamp,
        "source_signal": signal_payload.get("source", "unknown"),
        "plan": asdict(plan),
        "thai_summary": format_plan_thai(plan),
    }


def format_plan_thai(plan: PreTradePlan) -> str:
    if plan.action == "hold":
        return "ตอนนี้ Trading Cafe เห็นสัญญาณ HOLD ยังไม่ควรให้ EA เปิดไม้ใหม่"

    status = "อนุญาตตามเงื่อนไข" if plan.allowed else "ยังไม่ควรเข้า"
    lines = [
        f"Pre-trade plan: {plan.mt5_symbol} {plan.action.upper()} — {status}",
        f"confidence: {plan.confidence:.2f}",
        f"entry: {plan.entry_price}",
        f"SL/TP: {plan.stop_loss} / {plan.take_profit}",
        f"actual RR: {plan.actual_rr:.2f} (bridge RR: {plan.bridge_rr:.2f})",
        f"lot ที่คำนวณ: {plan.calculated_lot:.2f} จาก risk {plan.risk_percent:.2f}% (~{plan.risk_amount:.2f})",
        f"spread: {plan.spread_points:.1f} points",
    ]
    if plan.warnings:
        lines.append("ข้อควรระวัง: " + ", ".join(plan.warnings))
    lines.append("EA ยังเป็นตัว execute ส่วน Trading Cafe ทำหน้าที่คำนวณ/ตรวจ/อธิบายก่อนเข้า")
    return "\n".join(lines)

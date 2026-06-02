import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from atsawin_trading_cafe.mt5_contract import (
    MarketSnapshot,
    SymbolSpec,
    build_pretrade_plan,
    calculate_actual_rr,
    calculate_lot_size,
    format_plan_thai,
    validate_signal_payload,
)


spec = SymbolSpec(
    symbol="XAUUSDm",
    tick_value=1.0,
    tick_size=0.01,
    volume_min=0.01,
    volume_max=1.0,
    volume_step=0.01,
    point=0.001,
)

lot = calculate_lot_size(
    balance=500.0,
    risk_percent=2.5,
    entry_price=4480.0,
    stop_loss=4475.0,
    spec=spec,
    max_lot=1.0,
)
assert lot == 0.02

rr_buy = calculate_actual_rr("buy", bid=4479.9, ask=4480.0, stop_loss=4475.0, take_profit=4490.0)
assert rr_buy == 2.0

rr_sell = calculate_actual_rr("sell", bid=4480.0, ask=4480.1, stop_loss=4485.0, take_profit=4470.0)
assert rr_sell == 2.0

signal = {
    "signal": "sell",
    "confidence": 0.76,
    "entry_price": 4480.0,
    "stop_loss": 4485.0,
    "take_profit": 4470.0,
    "risk_reward_ratio": 2.0,
    "symbol": "XAUUSD",
    "mt5_symbol": "XAUUSDm",
    "reasons": ["trend_down", "confirm_down"],
    "source": "test",
}
assert validate_signal_payload(signal) == []
plan = build_pretrade_plan(
    signal,
    MarketSnapshot(symbol="XAUUSDm", bid=4480.0, ask=4480.1, balance=500.0),
    spec,
    risk_percent=2.5,
    max_lot=1.0,
    max_spread_points=500,
)
assert plan.allowed is True
assert plan.action == "sell"
assert plan.calculated_lot == 0.02
assert plan.actual_rr == 2.0
assert not plan.warnings
assert "lot ที่คำนวณ" in format_plan_thai(plan)

bad_plan = build_pretrade_plan(
    {**signal, "confidence": 0.1},
    MarketSnapshot(symbol="XAUUSDm", bid=4480.0, ask=4480.1, balance=500.0),
    spec,
)
assert bad_plan.allowed is False
assert "confidence_below_minimum" in bad_plan.warnings

hold_plan = build_pretrade_plan(
    {"signal": "hold", "confidence": 0.0, "symbol": "XAUUSD", "mt5_symbol": "XAUUSDm"},
    MarketSnapshot(symbol="XAUUSDm", bid=4480.0, ask=4480.1, balance=500.0),
    spec,
)
assert hold_plan.allowed is False
assert "signal_is_hold" in hold_plan.warnings

print("All MT5 contract tests passed.")

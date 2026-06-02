import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from atsawin_trading_cafe.mt5_contract import MarketSnapshot, SymbolSpec, build_pretrade_plan
from atsawin_trading_cafe.plan_analysis import analyze_pretrade_plan, format_analysis_thai

spec = SymbolSpec(
    symbol="XAUUSDm",
    tick_value=0.1,
    tick_size=0.001,
    volume_min=0.01,
    volume_max=200.0,
    volume_step=0.01,
    point=0.001,
)

signal = {
    "signal": "sell",
    "confidence": 0.85,
    "entry_price": 4480.0,
    "stop_loss": 4490.0,
    "take_profit": 4460.0,
    "risk_reward_ratio": 2.0,
    "symbol": "XAUUSD",
    "mt5_symbol": "XAUUSDm",
    "reasons": ["trend_down", "confirm_down", "in_session_soft"],
}
plan = build_pretrade_plan(
    signal,
    MarketSnapshot(symbol="XAUUSDm", bid=4480.0, ask=4480.3, balance=500.0),
    spec,
)
analysis = analyze_pretrade_plan(plan)
assert analysis.score >= 50
assert analysis.verdict in {"strong_research_candidate", "watchlist_candidate"}
assert analysis.strengths
assert any("setup" in item.lower() or "directional" in item.lower() for item in analysis.strengths)
text = format_analysis_thai(analysis)
assert "Plan analysis" in text
assert "แนวทางพัฒนาต่อ" in text or "จุดแข็ง" in text

hold_plan = build_pretrade_plan(
    {"signal": "hold", "confidence": 0.0, "symbol": "XAUUSD", "mt5_symbol": "XAUUSDm"},
    MarketSnapshot(symbol="XAUUSDm", bid=4480.0, ask=4480.3, balance=500.0),
    spec,
)
hold_analysis = analyze_pretrade_plan(hold_plan)
assert hold_analysis.verdict == "no_trade_observation"
assert any("HOLD" in item for item in hold_analysis.weaknesses)

print("All plan analysis tests passed.")

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from atsawin_trading_cafe.models import TradeEntry, TradeOutcome, TradeSide
from atsawin_trading_cafe.risk import check_trade_risk


trades = [
    TradeEntry("XAUUSDm", TradeSide.BUY, 2300.0, 0.01, datetime.now(), TradeOutcome.WIN, pnl=10, risk_percent=2.5),
]
for i in range(11):
    trades.append(
        TradeEntry("XAUUSDm", TradeSide.SELL, 2310.0 + i, 0.01, datetime.now(), TradeOutcome.LOSS, pnl=-3, risk_percent=6.0)
    )

warnings = check_trade_risk(trades, max_risk_percent=5.0, overtrade_limit=10, loss_streak_limit=3)
codes = {warning.code for warning in warnings}
assert "HIGH_RISK_PERCENT" in codes
assert "OVERTRADE" in codes
assert "LOSS_STREAK" in codes
assert any("ควรหยุดพัก" in warning.message for warning in warnings)

print("All risk tests passed.")

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from atsawin_trading_cafe.journal import format_summary_thai, summarize_trades
from atsawin_trading_cafe.models import TradeEntry, TradeOutcome, TradeSide


trades = [
    TradeEntry("XAUUSDm", TradeSide.BUY, 2300.0, 0.01, datetime.now(), TradeOutcome.WIN, pnl=12.5, risk_percent=2.5, setup="ema-rsi"),
    TradeEntry("XAUUSDm", TradeSide.SELL, 2310.0, 0.01, datetime.now(), TradeOutcome.LOSS, pnl=-5.0, risk_percent=2.5, setup="ema-rsi"),
    TradeEntry("BTCUSDT", TradeSide.BUY, 60000.0, 0.01, datetime.now(), TradeOutcome.BREAKEVEN, pnl=0.0, risk_percent=1.0, setup="breakout"),
]
summary = summarize_trades(trades)
assert summary.trade_count == 3
assert summary.win_count == 1
assert summary.loss_count == 1
assert summary.breakeven_count == 1
assert summary.total_pnl == 7.5
assert summary.win_rate == 33.33
assert summary.average_risk_percent == 2.0
assert summary.symbols == ["BTCUSDT", "XAUUSDm"]
assert summary.setups == {"ema-rsi": 2, "breakout": 1}

thai = format_summary_thai(summary)
assert "จำนวนไม้: 3" in thai
assert "Win rate: 33.33%" in thai
assert "เช็ก risk ก่อนเสมอ" in thai

print("All journal tests passed.")

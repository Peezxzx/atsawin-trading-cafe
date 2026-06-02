import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from atsawin_trading_cafe.history_store import append_history, evaluate_current_outcome, summarize_history

report = {
    "timestamp": "2026-06-02T01:30:00+00:00",
    "source_signal": "unit_test",
    "plan": {
        "action": "buy",
        "symbol": "XAUUSD",
        "mt5_symbol": "XAUUSDm",
        "confidence": 0.8,
        "entry_price": 4480.0,
        "stop_loss": 4475.0,
        "take_profit": 4490.0,
        "bridge_rr": 2.0,
        "actual_rr": 2.0,
        "calculated_lot": 0.02,
        "risk_percent": 2.5,
        "risk_amount": 12.5,
        "spread_points": 200.0,
        "warnings": [],
        "reasons": ["trend_up"],
    },
    "analysis": {
        "verdict": "watchlist_candidate",
        "score": 72.5,
    },
    "market": {
        "symbol": "XAUUSDm",
        "bid": 4481.0,
        "ask": 4481.2,
        "balance": 500.0,
    },
}

outcome = evaluate_current_outcome(report["plan"], report["market"])
assert outcome.outcome == "open_observation"
assert outcome.checked_price == 4481.0

tmp = Path(os.environ.get("TEMP", ".")) / "atsawin_trading_cafe_history_test"
tmp.mkdir(parents=True, exist_ok=True)
db = tmp / "history.sqlite"
csv = tmp / "history.csv"
for path in (db, csv):
    if path.exists():
        path.unlink()

meta = append_history(db, csv, report)
assert meta["history_id"] == 1
assert meta["outcome"]["outcome"] == "open_observation"
assert db.exists()
assert csv.exists()
summary = summarize_history(db)
assert summary["rows"] == 1
assert summary["by_action"] == {"buy": 1}
assert summary["by_outcome"] == {"open_observation": 1}
assert summary["average_score"] == 72.5

print("All history store tests passed.")

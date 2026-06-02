import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from atsawin_trading_cafe.history_store import (
    append_history,
    bucket_confidence,
    bucket_spread,
    evaluate_current_outcome,
    summarize_history,
    useful_insights,
    write_insights,
)

report = {
    "timestamp": "2026-06-02T01:30:00+00:00",
    "source_signal": "unit_test",
    "source_signal_timestamp": "2026-06-02T01:29:30+00:00",
    "source_signal_payload": {
        "timestamp": "2026-06-02T01:29:30+00:00",
        "source": "unit_test",
        "signal": "buy",
        "symbol": "XAUUSD",
        "mt5_symbol": "XAUUSDm",
        "confidence": 0.8,
        "entry_price": 4480.0,
        "stop_loss": 4475.0,
        "take_profit": 4490.0,
        "risk_reward_ratio": 2.0,
        "reasons": ["trend_up"],
    },
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
    "symbol_spec": {"point": 0.001},
}

outcome = evaluate_current_outcome(report["plan"], report["market"])
assert outcome.outcome == "open_observation"
assert outcome.checked_price == 4481.0
assert bucket_confidence(0.8) == "high"
assert bucket_confidence(0.52) == "medium"
assert bucket_spread(200) == "good"
assert bucket_spread(308) == "ok"


tmp = Path(os.environ.get("TEMP", ".")) / "atsawin_trading_cafe_history_test"
tmp.mkdir(parents=True, exist_ok=True)
db = tmp / "history.sqlite"
csv = tmp / "history.csv"
for path in (db, csv, tmp / "trading_cafe_insights.json", tmp / "trading_cafe_insights.txt"):
    if path.exists():
        path.unlink()

meta = append_history(db, csv, report)
assert meta["history_id"] == 1
assert meta["recorded"] is True
assert meta["record_reason"] == "first_observation"
assert meta["outcome"]["outcome"] == "open_observation"
assert db.exists()
assert csv.exists()
summary = summarize_history(db)
assert summary["rows"] == 1
assert summary["by_action"] == {"buy": 1}
assert summary["by_outcome"] == {"open_observation": 1}
assert summary["by_record_reason"] == {"first_observation": 1}
assert summary["average_score"] == 72.5

# Same source signal + no material change should not bloat the research table.
duplicate = dict(report)
duplicate["timestamp"] = "2026-06-02T01:30:30+00:00"
meta2 = append_history(db, csv, duplicate)
assert meta2["recorded"] is False
assert meta2["record_reason"] == "duplicate_same_signal_no_material_change"
assert summarize_history(db)["rows"] == 1

# Material RR change should be kept because it teaches us about live RR drift.
changed = dict(report)
changed["timestamp"] = "2026-06-02T01:31:00+00:00"
changed["plan"] = dict(report["plan"])
changed["plan"]["actual_rr"] = 1.5
meta3 = append_history(db, csv, changed)
assert meta3["recorded"] is True
assert meta3["record_reason"] == "actual_rr_changed"
assert summarize_history(db)["rows"] == 2

insights = useful_insights(db)
assert insights["rows"] == 2
assert insights["unique_source_signals"] == 1
assert insights["average_spread_points"] == 200.0
paths = write_insights(db, tmp)
assert Path(paths["insights_path"]).exists()
assert Path(paths["insights_text_path"]).exists()

print("All history store tests passed.")

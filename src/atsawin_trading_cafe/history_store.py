"""Persistent history storage for Trading Cafe research reports."""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_FILE = "trading_cafe_history.sqlite"
DEFAULT_CSV_FILE = "trading_cafe_history.csv"


@dataclass(slots=True)
class OutcomeCheck:
    outcome: str
    checked_price: float
    pnl_r_estimate: float
    note: str


def stable_signal_hash(signal_payload: dict[str, Any]) -> str:
    key = {
        "signal": signal_payload.get("signal"),
        "symbol": signal_payload.get("symbol"),
        "mt5_symbol": signal_payload.get("mt5_symbol"),
        "entry_price": signal_payload.get("entry_price"),
        "stop_loss": signal_payload.get("stop_loss"),
        "take_profit": signal_payload.get("take_profit"),
        "timestamp": signal_payload.get("timestamp"),
        "source": signal_payload.get("source"),
    }
    raw = json.dumps(key, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def evaluate_current_outcome(plan: dict[str, Any], market: dict[str, Any]) -> OutcomeCheck:
    """Evaluate whether current live price is already beyond TP/SL.

    This is not a full backtest. It is a lightweight live observation tag for
    research history. Full TP/SL/no-hit over future bars can be added later from
    MT5 candle history.
    """
    action = str(plan.get("action") or "hold").lower()
    sl = float(plan.get("stop_loss") or 0.0)
    tp = float(plan.get("take_profit") or 0.0)
    entry = float(plan.get("entry_price") or 0.0)
    bid = float(market.get("bid") or 0.0)
    ask = float(market.get("ask") or 0.0)

    if action == "buy":
        price = bid
        if tp > 0 and price >= tp:
            rr = abs(tp - entry) / abs(entry - sl) if entry and sl and entry != sl else 0.0
            return OutcomeCheck("tp_seen", price, round(rr, 4), "current bid has reached/touched TP")
        if sl > 0 and price <= sl:
            return OutcomeCheck("sl_seen", price, -1.0, "current bid has reached/touched SL")
        return OutcomeCheck("open_observation", price, 0.0, "current bid is between SL and TP")

    if action == "sell":
        price = ask
        if tp > 0 and price <= tp:
            rr = abs(entry - tp) / abs(sl - entry) if entry and sl and entry != sl else 0.0
            return OutcomeCheck("tp_seen", price, round(rr, 4), "current ask has reached/touched TP")
        if sl > 0 and price >= sl:
            return OutcomeCheck("sl_seen", price, -1.0, "current ask has reached/touched SL")
        return OutcomeCheck("open_observation", price, 0.0, "current ask is between SL and TP")

    return OutcomeCheck("no_trade_observation", bid or ask, 0.0, "plan is HOLD/no-trade")


def init_db(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observed_at TEXT NOT NULL,
                signal_hash TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                verdict TEXT,
                score REAL,
                confidence REAL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                bridge_rr REAL,
                actual_rr REAL,
                calculated_lot REAL,
                risk_percent REAL,
                risk_amount REAL,
                spread_points REAL,
                warnings_json TEXT,
                reasons_json TEXT,
                outcome TEXT,
                checked_price REAL,
                pnl_r_estimate REAL,
                outcome_note TEXT,
                report_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_history_observed_at ON plan_history(observed_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_history_symbol_action ON plan_history(symbol, action)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_history_outcome ON plan_history(outcome)")


def append_history(db_path: str | Path, csv_path: str | Path, report: dict[str, Any]) -> dict[str, Any]:
    plan = report.get("plan", {})
    market = report.get("market", {})
    analysis = report.get("analysis", {})
    signal_hash = stable_signal_hash({**plan, "source": report.get("source_signal"), "timestamp": report.get("timestamp")})
    outcome = evaluate_current_outcome(plan, market)
    observed_at = str(report.get("timestamp") or datetime.now(timezone.utc).isoformat())
    symbol = str(plan.get("mt5_symbol") or plan.get("symbol") or "")

    row = {
        "observed_at": observed_at,
        "signal_hash": signal_hash,
        "symbol": symbol,
        "action": str(plan.get("action") or ""),
        "verdict": str(analysis.get("verdict") or ""),
        "score": float(analysis.get("score") or 0.0),
        "confidence": float(plan.get("confidence") or 0.0),
        "entry_price": float(plan.get("entry_price") or 0.0),
        "stop_loss": float(plan.get("stop_loss") or 0.0),
        "take_profit": float(plan.get("take_profit") or 0.0),
        "bridge_rr": float(plan.get("bridge_rr") or 0.0),
        "actual_rr": float(plan.get("actual_rr") or 0.0),
        "calculated_lot": float(plan.get("calculated_lot") or 0.0),
        "risk_percent": float(plan.get("risk_percent") or 0.0),
        "risk_amount": float(plan.get("risk_amount") or 0.0),
        "spread_points": float(plan.get("spread_points") or 0.0),
        "warnings_json": json.dumps(plan.get("warnings", []), ensure_ascii=False),
        "reasons_json": json.dumps(plan.get("reasons", []), ensure_ascii=False),
        "outcome": outcome.outcome,
        "checked_price": outcome.checked_price,
        "pnl_r_estimate": outcome.pnl_r_estimate,
        "outcome_note": outcome.note,
        "report_json": json.dumps(report, ensure_ascii=False),
    }

    init_db(db_path)
    columns = list(row.keys())
    placeholders = ", ".join("?" for _ in columns)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            f"INSERT INTO plan_history ({', '.join(columns)}) VALUES ({placeholders})",
            [row[col] for col in columns],
        )
        history_id = int(cur.lastrowid)

    append_csv(csv_path, {"id": history_id, **row})
    return {"history_id": history_id, "outcome": asdict(outcome), "db_path": str(db_path), "csv_path": str(csv_path)}


def append_csv(csv_path: str | Path, row: dict[str, Any]) -> None:
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def summarize_history(db_path: str | Path, limit: int = 1000) -> dict[str, Any]:
    path = Path(db_path)
    if not path.exists():
        return {"rows": 0, "by_action": {}, "by_outcome": {}, "average_score": 0.0}
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT action, outcome, score FROM plan_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    by_action: dict[str, int] = {}
    by_outcome: dict[str, int] = {}
    scores: list[float] = []
    for row in rows:
        by_action[row["action"]] = by_action.get(row["action"], 0) + 1
        by_outcome[row["outcome"]] = by_outcome.get(row["outcome"], 0) + 1
        scores.append(float(row["score"] or 0.0))
    return {
        "rows": len(rows),
        "by_action": by_action,
        "by_outcome": by_outcome,
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
    }

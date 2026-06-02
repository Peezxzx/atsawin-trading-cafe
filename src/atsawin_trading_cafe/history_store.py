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
DEFAULT_INSIGHTS_FILE = "trading_cafe_insights.json"
DEFAULT_INSIGHTS_TEXT_FILE = "trading_cafe_insights.txt"

SIGNIFICANT_ACTUAL_RR_DELTA = 0.25
SIGNIFICANT_SCORE_DELTA = 5.0
SIGNIFICANT_PRICE_DELTA_POINTS = 120.0
SAME_SIGNAL_SAMPLE_SECONDS = 180.0


@dataclass(slots=True)
class OutcomeCheck:
    outcome: str
    checked_price: float
    pnl_r_estimate: float
    note: str


def rounded_price(value: Any, digits: int = 1) -> float:
    try:
        return round(float(value or 0.0), digits)
    except (TypeError, ValueError):
        return 0.0


def stable_signal_hash(signal_payload: dict[str, Any]) -> str:
    """Hash the setup fingerprint, not every 30-second tick.

    The bridge may refresh timestamp and entry price on every scan. Those are
    still stored in each row, but they should not make a repeated setup look like
    a brand-new strategy event. Material changes are captured separately by the
    sampling rules (RR drift, price movement, periodic sample, etc.).
    """
    confidence = float(signal_payload.get("confidence") or 0.0)
    key = {
        "signal": signal_payload.get("signal") or signal_payload.get("action"),
        "symbol": signal_payload.get("symbol"),
        "mt5_symbol": signal_payload.get("mt5_symbol"),
        "confidence_bucket": bucket_confidence(confidence),
        "stop_loss_rounded": rounded_price(signal_payload.get("stop_loss"), 1),
        "take_profit_rounded": rounded_price(signal_payload.get("take_profit"), 1),
        "source": signal_payload.get("source") or signal_payload.get("source_signal"),
        "reasons": signal_payload.get("reasons"),
    }
    raw = json.dumps(key, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def seconds_between(start: Any, end: Any) -> float:
    a = parse_dt(start)
    b = parse_dt(end)
    if a is None or b is None:
        return 0.0
    if a.tzinfo is None:
        a = a.replace(tzinfo=timezone.utc)
    if b.tzinfo is None:
        b = b.replace(tzinfo=timezone.utc)
    return max(0.0, round((b - a).total_seconds(), 1))


def bucket_confidence(value: float) -> str:
    if value >= 0.70:
        return "high"
    if value >= 0.50:
        return "medium"
    if value >= 0.30:
        return "low"
    return "very_low"


def bucket_spread(points: float) -> str:
    if points <= 250:
        return "good"
    if points <= 500:
        return "ok"
    return "high"


def setup_key(plan: dict[str, Any]) -> str:
    action = str(plan.get("action") or "hold").lower()
    reasons = [str(item) for item in plan.get("reasons", [])]
    return "+".join([action, *reasons[:4]])


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
                report_json TEXT NOT NULL,
                source_signal_timestamp TEXT,
                signal_age_seconds REAL,
                rr_drift REAL,
                spread_bucket TEXT,
                confidence_bucket TEXT,
                setup_key TEXT,
                record_reason TEXT
            )
            """
        )
        existing = {row[1] for row in conn.execute("PRAGMA table_info(plan_history)").fetchall()}
        migrations = {
            "source_signal_timestamp": "TEXT",
            "signal_age_seconds": "REAL",
            "rr_drift": "REAL",
            "spread_bucket": "TEXT",
            "confidence_bucket": "TEXT",
            "setup_key": "TEXT",
            "record_reason": "TEXT",
        }
        for column, col_type in migrations.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE plan_history ADD COLUMN {column} {col_type}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_history_observed_at ON plan_history(observed_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_history_symbol_action ON plan_history(symbol, action)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_history_outcome ON plan_history(outcome)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_history_signal_hash ON plan_history(signal_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_history_setup_key ON plan_history(setup_key)")


def build_history_row(report: dict[str, Any]) -> tuple[dict[str, Any], OutcomeCheck]:
    plan = report.get("plan", {})
    market = report.get("market", {})
    analysis = report.get("analysis", {})
    source_signal = report.get("source_signal_payload") or {
        **plan,
        "source_signal": report.get("source_signal"),
        "source_signal_timestamp": report.get("source_signal_timestamp"),
    }
    signal_hash = stable_signal_hash(source_signal)
    outcome = evaluate_current_outcome(plan, market)
    observed_at = str(report.get("timestamp") or datetime.now(timezone.utc).isoformat())
    source_signal_timestamp = str(report.get("source_signal_timestamp") or source_signal.get("timestamp") or "")
    symbol = str(plan.get("mt5_symbol") or plan.get("symbol") or "")
    confidence = float(plan.get("confidence") or 0.0)
    spread_points = float(plan.get("spread_points") or 0.0)
    bridge_rr = float(plan.get("bridge_rr") or 0.0)
    actual_rr = float(plan.get("actual_rr") or 0.0)

    row = {
        "observed_at": observed_at,
        "signal_hash": signal_hash,
        "symbol": symbol,
        "action": str(plan.get("action") or ""),
        "verdict": str(analysis.get("verdict") or ""),
        "score": float(analysis.get("score") or 0.0),
        "confidence": confidence,
        "entry_price": float(plan.get("entry_price") or 0.0),
        "stop_loss": float(plan.get("stop_loss") or 0.0),
        "take_profit": float(plan.get("take_profit") or 0.0),
        "bridge_rr": bridge_rr,
        "actual_rr": actual_rr,
        "calculated_lot": float(plan.get("calculated_lot") or 0.0),
        "risk_percent": float(plan.get("risk_percent") or 0.0),
        "risk_amount": float(plan.get("risk_amount") or 0.0),
        "spread_points": spread_points,
        "warnings_json": json.dumps(plan.get("warnings", []), ensure_ascii=False),
        "reasons_json": json.dumps(plan.get("reasons", []), ensure_ascii=False),
        "outcome": outcome.outcome,
        "checked_price": outcome.checked_price,
        "pnl_r_estimate": outcome.pnl_r_estimate,
        "outcome_note": outcome.note,
        "report_json": json.dumps(report, ensure_ascii=False),
        "source_signal_timestamp": source_signal_timestamp,
        "signal_age_seconds": seconds_between(source_signal_timestamp, observed_at),
        "rr_drift": round(bridge_rr - actual_rr, 4) if bridge_rr or actual_rr else 0.0,
        "spread_bucket": bucket_spread(spread_points),
        "confidence_bucket": bucket_confidence(confidence),
        "setup_key": setup_key(plan),
        "record_reason": "",
    }
    return row, outcome


def should_record_observation(conn: sqlite3.Connection, row: dict[str, Any], *, point: float = 0.001) -> tuple[bool, str]:
    previous = conn.execute(
        """
        SELECT * FROM plan_history
        WHERE symbol = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (row["symbol"],),
    ).fetchone()
    if previous is None:
        return True, "first_observation"

    prev = dict(previous)
    if prev.get("action") != row["action"]:
        return True, "action_changed"
    if prev.get("signal_hash") != row["signal_hash"]:
        return True, "new_setup_fingerprint"
    if prev.get("outcome") != row["outcome"]:
        return True, "outcome_changed"
    if prev.get("warnings_json") != row["warnings_json"]:
        return True, "warnings_changed"
    if prev.get("spread_bucket") != row["spread_bucket"]:
        return True, "spread_bucket_changed"
    if abs(float(prev.get("actual_rr") or 0.0) - row["actual_rr"]) >= SIGNIFICANT_ACTUAL_RR_DELTA:
        return True, "actual_rr_changed"
    if abs(float(prev.get("score") or 0.0) - row["score"]) >= SIGNIFICANT_SCORE_DELTA:
        return True, "score_changed"

    price_delta_points = abs(float(prev.get("entry_price") or 0.0) - row["entry_price"]) / point if point > 0 else 0.0
    if row["action"] in {"buy", "sell"} and price_delta_points >= SIGNIFICANT_PRICE_DELTA_POINTS:
        return True, "price_moved_significantly"

    elapsed = seconds_between(prev.get("observed_at"), row["observed_at"])
    if elapsed >= SAME_SIGNAL_SAMPLE_SECONDS:
        return True, "periodic_sample"

    return False, "duplicate_same_signal_no_material_change"


def append_history(db_path: str | Path, csv_path: str | Path, report: dict[str, Any]) -> dict[str, Any]:
    row, outcome = build_history_row(report)
    init_db(db_path)
    point = float((report.get("symbol_spec") or {}).get("point") or 0.001)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        should_record, reason = should_record_observation(conn, row, point=point)
        row["record_reason"] = reason
        if not should_record:
            latest = conn.execute("SELECT id FROM plan_history ORDER BY id DESC LIMIT 1").fetchone()
            return {
                "history_id": int(latest["id"]) if latest else None,
                "recorded": False,
                "record_reason": reason,
                "outcome": asdict(outcome),
                "db_path": str(db_path),
                "csv_path": str(csv_path),
            }

        columns = list(row.keys())
        placeholders = ", ".join("?" for _ in columns)
        cur = conn.execute(
            f"INSERT INTO plan_history ({', '.join(columns)}) VALUES ({placeholders})",
            [row[col] for col in columns],
        )
        history_id = int(cur.lastrowid)

    append_csv(csv_path, {"id": history_id, **row})
    return {
        "history_id": history_id,
        "recorded": True,
        "record_reason": row["record_reason"],
        "outcome": asdict(outcome),
        "db_path": str(db_path),
        "csv_path": str(csv_path),
    }


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
    init_db(path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT action, outcome, score, record_reason FROM plan_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    by_action: dict[str, int] = {}
    by_outcome: dict[str, int] = {}
    by_record_reason: dict[str, int] = {}
    scores: list[float] = []
    for row in rows:
        by_action[row["action"]] = by_action.get(row["action"], 0) + 1
        by_outcome[row["outcome"]] = by_outcome.get(row["outcome"], 0) + 1
        reason = row["record_reason"] or "legacy"
        by_record_reason[reason] = by_record_reason.get(reason, 0) + 1
        scores.append(float(row["score"] or 0.0))
    return {
        "rows": len(rows),
        "by_action": by_action,
        "by_outcome": by_outcome,
        "by_record_reason": by_record_reason,
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
    }


def useful_insights(db_path: str | Path, *, limit: int = 500) -> dict[str, Any]:
    path = Path(db_path)
    if not path.exists():
        return {"rows": 0, "insights": [], "recommendations": ["ยังไม่มีข้อมูลพอ"]}
    init_db(path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM plan_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    if not rows:
        return {"rows": 0, "insights": [], "recommendations": ["ยังไม่มีข้อมูลพอ"]}

    action_counts: dict[str, int] = {}
    warning_counts: dict[str, int] = {}
    setup_scores: dict[str, list[float]] = {}
    spread_values: list[float] = []
    rr_values: list[float] = []
    signal_hashes: set[str] = set()
    high_quality = 0

    for row in rows:
        action_counts[row["action"]] = action_counts.get(row["action"], 0) + 1
        signal_hashes.add(row["signal_hash"])
        score = float(row["score"] or 0.0)
        if score >= 50 and row["action"] in {"buy", "sell"}:
            high_quality += 1
        setup_scores.setdefault(row["setup_key"] or row["action"], []).append(score)
        spread_values.append(float(row["spread_points"] or 0.0))
        rr_values.append(float(row["actual_rr"] or 0.0))
        try:
            warnings = json.loads(row["warnings_json"] or "[]")
        except json.JSONDecodeError:
            warnings = []
        for warning in warnings:
            warning_counts[str(warning)] = warning_counts.get(str(warning), 0) + 1

    avg_score = round(sum(float(row["score"] or 0.0) for row in rows) / len(rows), 2)
    avg_spread = round(sum(spread_values) / len(spread_values), 1) if spread_values else 0.0
    avg_rr = round(sum(rr_values) / len(rr_values), 3) if rr_values else 0.0
    duplicate_ratio = round(1 - (len(signal_hashes) / len(rows)), 3) if rows else 0.0
    top_setups = sorted(
        (
            {
                "setup_key": key,
                "count": len(scores),
                "average_score": round(sum(scores) / len(scores), 2),
            }
            for key, scores in setup_scores.items()
        ),
        key=lambda item: (item["average_score"], item["count"]),
        reverse=True,
    )[:8]

    recommendations: list[str] = []
    if duplicate_ratio > 0.6:
        recommendations.append("ข้อมูลซ้ำจาก signal เดิมยังเยอะ ควรใช้ dedup/sampling ต่อไปเพื่อให้ dataset สะอาด")
    if action_counts.get("hold", 0) > (len(rows) * 0.5):
        recommendations.append("HOLD เยอะ: ควรวิเคราะห์ no-trade regime ว่าเกิดจาก trend ไม่ชัด, confidence ต่ำ หรือ spread")
    if avg_spread > 300:
        recommendations.append("spread เฉลี่ยค่อนข้างสูง ควรแยกผลลัพธ์ตาม spread bucket ก่อนสรุป strategy")
    if high_quality < 10:
        recommendations.append("ตัวอย่าง setup คุณภาพดีมีน้อย ยังไม่ควรสรุป winrate/strategy จากข้อมูลชุดนี้")
    if not recommendations:
        recommendations.append("ข้อมูลเริ่มใช้วิเคราะห์ได้: ต่อไปควรผูก outcome หลังผ่าน N แท่งเพื่อวัด TP/SL จริง")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "unique_source_signals": len(signal_hashes),
        "duplicate_ratio": duplicate_ratio,
        "action_counts": action_counts,
        "warning_counts": dict(sorted(warning_counts.items(), key=lambda item: item[1], reverse=True)),
        "average_score": avg_score,
        "average_spread_points": avg_spread,
        "average_actual_rr": avg_rr,
        "high_quality_directional_rows": high_quality,
        "top_setups": top_setups,
        "recommendations": recommendations,
    }


def format_insights_text(insights: dict[str, Any]) -> str:
    lines = [
        "Atsawin Trading Cafe Insights",
        f"generated_at: {insights.get('generated_at', '-')}",
        f"rows: {insights.get('rows', 0)}",
        f"unique_source_signals: {insights.get('unique_source_signals', 0)}",
        f"duplicate_ratio: {insights.get('duplicate_ratio', 0)}",
        f"average_score: {insights.get('average_score', 0)}",
        f"average_spread_points: {insights.get('average_spread_points', 0)}",
        f"average_actual_rr: {insights.get('average_actual_rr', 0)}",
        f"high_quality_directional_rows: {insights.get('high_quality_directional_rows', 0)}",
        "",
        "action_counts:",
    ]
    for key, value in (insights.get("action_counts") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("top_warnings:")
    for key, value in list((insights.get("warning_counts") or {}).items())[:8]:
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("top_setups:")
    for item in insights.get("top_setups") or []:
        lines.append(f"- {item['setup_key']}: count={item['count']} avg_score={item['average_score']}")
    lines.append("")
    lines.append("recommendations:")
    for item in insights.get("recommendations") or []:
        lines.append(f"- {item}")
    return "\n".join(lines)


def write_insights(db_path: str | Path, output_dir: str | Path, *, limit: int = 500) -> dict[str, Any]:
    insights = useful_insights(db_path, limit=limit)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / DEFAULT_INSIGHTS_FILE
    text_path = out_dir / DEFAULT_INSIGHTS_TEXT_FILE
    json_path.write_text(json.dumps(insights, ensure_ascii=False, indent=2), encoding="utf-8")
    text_path.write_text(format_insights_text(insights), encoding="utf-8")
    return {"insights_path": str(json_path), "insights_text_path": str(text_path), **insights}

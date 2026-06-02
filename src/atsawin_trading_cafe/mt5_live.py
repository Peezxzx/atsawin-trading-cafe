"""Live MT5 adapter for Atsawin Trading Cafe.

Reads the same `latest_signal.json` used by the EA, pulls live MT5 account/tick
info, calculates a pre-trade plan, and writes `trading_cafe_report.json` into the
same Common Files folder.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import asdict
from pathlib import Path

from .history_store import DEFAULT_CSV_FILE, DEFAULT_DB_FILE, append_history, summarize_history
from .mt5_contract import (
    DEFAULT_REPORT_FILE,
    DEFAULT_SIGNAL_DIR,
    MarketSnapshot,
    SymbolSpec,
    atomic_write_json,
    build_pretrade_plan,
    plan_to_report,
    read_signal,
)
from .plan_analysis import analysis_to_report, analyze_pretrade_plan, format_analysis_thai


def _import_mt5():
    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 package is not installed for this Python") from exc
    return mt5


def symbol_spec_from_mt5(mt5, symbol: str) -> SymbolSpec:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"MT5 symbol not found: {symbol}")
    return SymbolSpec(
        symbol=symbol,
        tick_value=float(info.trade_tick_value or 0.0),
        tick_size=float(info.trade_tick_size or 0.0),
        volume_min=float(info.volume_min or 0.01),
        volume_max=float(info.volume_max or 1.0),
        volume_step=float(info.volume_step or 0.01),
        point=float(info.point or 0.001),
    )


def market_snapshot_from_mt5(mt5, symbol: str) -> MarketSnapshot:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No live tick for {symbol}")
    account = mt5.account_info()
    if account is None:
        raise RuntimeError("No MT5 account info")
    return MarketSnapshot(
        symbol=symbol,
        bid=float(tick.bid),
        ask=float(tick.ask),
        balance=float(account.balance),
        equity=float(account.equity),
    )


def run_once(
    *,
    signal_dir: str | Path = DEFAULT_SIGNAL_DIR,
    login: int | None = None,
    server: str | None = None,
    risk_percent: float = 2.5,
    max_lot: float = 1.0,
    min_confidence: float = 0.30,
    max_spread_points: float = 500.0,
    min_actual_rr: float = 1.0,
    record_history: bool = True,
) -> dict:
    mt5 = _import_mt5()
    init_kwargs = {}
    if login is not None:
        init_kwargs["login"] = login
    if server:
        init_kwargs["server"] = server
    if not mt5.initialize(**init_kwargs):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    try:
        signal = read_signal(signal_dir)
        symbol = str(signal.get("mt5_symbol") or signal.get("symbol") or "XAUUSDm")
        spec = symbol_spec_from_mt5(mt5, symbol)
        market = market_snapshot_from_mt5(mt5, symbol)
        plan = build_pretrade_plan(
            signal,
            market,
            spec,
            risk_percent=risk_percent,
            max_lot=max_lot,
            min_confidence=min_confidence,
            max_spread_points=max_spread_points,
            min_actual_rr=min_actual_rr,
        )
        report = plan_to_report(plan, signal)
        analysis = analyze_pretrade_plan(plan)
        report["analysis"] = analysis_to_report(analysis)
        report["analysis_thai"] = format_analysis_thai(analysis)
        report["market"] = asdict(market)
        report["symbol_spec"] = asdict(spec)
        report_path = Path(signal_dir) / DEFAULT_REPORT_FILE
        atomic_write_json(report_path, report)
        if record_history:
            history_meta = append_history(
                Path(signal_dir) / DEFAULT_DB_FILE,
                Path(signal_dir) / DEFAULT_CSV_FILE,
                report,
            )
            report["history"] = history_meta
            report["history_summary"] = summarize_history(Path(signal_dir) / DEFAULT_DB_FILE)
            atomic_write_json(report_path, report)
        return {"report_path": str(report_path), **report}
    finally:
        mt5.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Atsawin Trading Cafe MT5 connector")
    parser.add_argument("--signal-dir", default=str(DEFAULT_SIGNAL_DIR))
    parser.add_argument("--login", type=int, default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--risk-percent", type=float, default=2.5)
    parser.add_argument("--max-lot", type=float, default=1.0)
    parser.add_argument("--min-confidence", type=float, default=0.30)
    parser.add_argument("--max-spread-points", type=float, default=500.0)
    parser.add_argument("--min-actual-rr", type=float, default=1.0)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--no-history", action="store_true", help="Do not append this observation to SQLite/CSV history")
    parser.add_argument("--summary", action="store_true", help="Print history summary after each run")
    args = parser.parse_args()

    while True:
        result = run_once(
            signal_dir=args.signal_dir,
            login=args.login,
            server=args.server,
            risk_percent=args.risk_percent,
            max_lot=args.max_lot,
            min_confidence=args.min_confidence,
            max_spread_points=args.max_spread_points,
            min_actual_rr=args.min_actual_rr,
            record_history=not args.no_history,
        )
        print(result["thai_summary"])
        if "analysis_thai" in result:
            print(result["analysis_thai"])
        if args.summary and "history_summary" in result:
            print(f"history_summary: {result['history_summary']}")
        print(f"report: {result['report_path']}")
        if not args.watch:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

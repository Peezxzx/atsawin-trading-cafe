"""Trade journal summary logic."""

from __future__ import annotations

from collections import Counter

from .models import JournalSummary, TradeEntry, TradeOutcome


def summarize_trades(trades: list[TradeEntry]) -> JournalSummary:
    """Summarize trade entries into dashboard-friendly metrics."""
    trade_count = len(trades)
    win_count = sum(1 for trade in trades if trade.outcome == TradeOutcome.WIN)
    loss_count = sum(1 for trade in trades if trade.outcome == TradeOutcome.LOSS)
    breakeven_count = sum(1 for trade in trades if trade.outcome == TradeOutcome.BREAKEVEN)
    closed_count = win_count + loss_count + breakeven_count
    total_pnl = round(sum(trade.pnl for trade in trades), 2)
    win_rate = round((win_count / closed_count) * 100, 2) if closed_count else 0.0
    average_risk = round(sum(trade.risk_percent for trade in trades) / trade_count, 2) if trade_count else 0.0
    setups = Counter(trade.setup for trade in trades if trade.setup)
    symbols = sorted({trade.symbol for trade in trades})

    return JournalSummary(
        trade_count=trade_count,
        win_count=win_count,
        loss_count=loss_count,
        breakeven_count=breakeven_count,
        total_pnl=total_pnl,
        win_rate=win_rate,
        average_risk_percent=average_risk,
        symbols=symbols,
        setups=dict(setups),
    )


def format_summary_thai(summary: JournalSummary) -> str:
    """Format a journal summary in Thai for Telegram/dashboard."""
    lines = [
        "สรุป Trading Journal",
        f"จำนวนไม้: {summary.trade_count}",
        f"Win/Loss/BE: {summary.win_count}/{summary.loss_count}/{summary.breakeven_count}",
        f"Win rate: {summary.win_rate:.2f}%",
        f"Total PnL: {summary.total_pnl:.2f}",
        f"Risk เฉลี่ย: {summary.average_risk_percent:.2f}%",
    ]
    if summary.symbols:
        lines.append(f"Symbols: {', '.join(summary.symbols)}")
    if summary.setups:
        setup_text = ", ".join(f"{name} x{count}" for name, count in summary.setups.items())
        lines.append(f"Setups: {setup_text}")
    lines.append("เช็ก risk ก่อนเสมอ แล้วค่อยตัดสินใจด้วยตัวเองครับ")
    return "\n".join(lines)

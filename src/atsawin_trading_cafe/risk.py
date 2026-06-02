"""Risk warning rules for Trading Cafe."""

from __future__ import annotations

from .models import RiskWarning, TradeEntry, TradeOutcome


def check_trade_risk(
    trades: list[TradeEntry],
    *,
    max_risk_percent: float = 5.0,
    overtrade_limit: int = 10,
    loss_streak_limit: int = 3,
) -> list[RiskWarning]:
    """Return risk warnings from recent trade behavior."""
    warnings: list[RiskWarning] = []

    high_risk = [trade for trade in trades if trade.risk_percent > max_risk_percent]
    if high_risk:
        warnings.append(
            RiskWarning(
                code="HIGH_RISK_PERCENT",
                severity="high",
                message=f"มี {len(high_risk)} ไม้ที่ risk เกิน {max_risk_percent:.1f}% ควรลดขนาดไม้ก่อน",
            )
        )

    if len(trades) > overtrade_limit:
        warnings.append(
            RiskWarning(
                code="OVERTRADE",
                severity="medium",
                message=f"จำนวนไม้ {len(trades)} เกิน limit {overtrade_limit} ไม้ ตรวจว่ากำลัง overtrade หรือไม่",
            )
        )

    recent_closed = [trade for trade in trades if trade.outcome != TradeOutcome.OPEN]
    streak = 0
    for trade in reversed(recent_closed):
        if trade.outcome == TradeOutcome.LOSS:
            streak += 1
        else:
            break

    if streak >= loss_streak_limit:
        warnings.append(
            RiskWarning(
                code="LOSS_STREAK",
                severity="high",
                message=f"แพ้ติดกัน {streak} ไม้ ควรหยุดพักและทบทวน setup ก่อนเทรดต่อ",
            )
        )

    return warnings

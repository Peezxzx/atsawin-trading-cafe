"""Plan analysis helpers for improving strategy without executing trades."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .mt5_contract import PreTradePlan


@dataclass(slots=True)
class PlanAnalysis:
    verdict: str
    score: float
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    next_questions: list[str] = field(default_factory=list)
    improvement_notes: list[str] = field(default_factory=list)


def analyze_pretrade_plan(plan: PreTradePlan) -> PlanAnalysis:
    """Analyze a calculated pre-trade plan for journal/research purposes.

    This function does not decide to execute. It turns numeric plan fields into
    a research-friendly explanation so future tuning can compare plan quality.
    """
    score = 0.0
    strengths: list[str] = []
    weaknesses: list[str] = []
    next_questions: list[str] = []
    improvement_notes: list[str] = []

    if plan.action in {"buy", "sell"}:
        score += 15
        strengths.append(f"มี directional setup: {plan.action.upper()}")
    else:
        weaknesses.append("ยังเป็น HOLD จึงใช้เป็นตัวอย่าง no-trade regime")
        next_questions.append("ช่วง HOLD นี้เกิดจาก trend ไม่ชัด, spread สูง, หรือ confidence ต่ำ?")

    if plan.confidence >= 0.70:
        score += 25
        strengths.append("confidence สูง เหมาะเก็บเป็นตัวอย่าง setup ที่ระบบมั่นใจ")
    elif plan.confidence >= 0.30:
        score += 12
        improvement_notes.append("confidence กลาง ๆ ควรดู confirmation เพิ่มก่อนปรับให้เข้าไม้จริง")
    else:
        weaknesses.append("confidence ต่ำ ไม่ควรใช้เป็นแผนเข้าไม้")

    if plan.actual_rr >= 2.0:
        score += 25
        strengths.append("actual RR ดีมากเมื่อเทียบกับราคา live")
    elif plan.actual_rr >= 1.2:
        score += 16
        strengths.append("actual RR พอใช้ได้ แต่ยังควรเทียบกับ win rate จริง")
    elif plan.actual_rr > 0:
        score += 6
        weaknesses.append("actual RR ต่ำ อาจไม่คุ้มถ้า win rate ไม่สูงพอ")
    else:
        weaknesses.append("actual RR ใช้งานไม่ได้หรือ signal เป็น HOLD")

    if plan.bridge_rr and plan.actual_rr:
        rr_drift = plan.bridge_rr - plan.actual_rr
        if rr_drift > 0.5:
            weaknesses.append(f"RR drift สูง: bridge RR {plan.bridge_rr:.2f} แต่ live RR {plan.actual_rr:.2f}")
            improvement_notes.append("ควรบันทึก delay ระหว่างสร้าง signal กับตอนประเมิน live price")
        elif abs(rr_drift) <= 0.25:
            strengths.append("bridge RR กับ live RR ใกล้กัน แปลว่าสัญญาณไม่ stale มาก")

    if plan.spread_points <= 250:
        score += 10
        strengths.append("spread อยู่ในระดับสบายสำหรับ XAUUSDm")
    elif plan.spread_points <= 500:
        score += 4
        improvement_notes.append("spread ยังผ่านได้ แต่ควรบันทึกผลลัพธ์แยกตาม spread bucket")
    else:
        weaknesses.append("spread สูง อาจทำให้ entry คุณภาพลดลง")

    if plan.calculated_lot > 0:
        score += 10
        strengths.append(f"คำนวณ lot ได้: {plan.calculated_lot:.2f}")
    else:
        weaknesses.append("ยังไม่มี lot เพราะแผนไม่ใช่ buy/sell หรือข้อมูล SL/TP ไม่ครบ")

    if plan.warnings:
        score -= min(25, 8 * len(plan.warnings))
        weaknesses.append("มี warning: " + ", ".join(plan.warnings))
        improvement_notes.append("ใช้ warning เป็น tag เวลารีวิวว่า filter ไหน block แผนบ่อยที่สุด")
    else:
        strengths.append("ไม่มี warning จาก risk/geometry checks")

    if plan.reasons:
        next_questions.append("เหตุผลของ setup นี้: " + ", ".join(plan.reasons[:6]))
    next_questions.extend([
        "ถ้าเข้าไม้ตามแผนนี้ ผลลัพธ์หลัง N แท่งเป็น TP, SL หรือ no-hit?",
        "setup แบบนี้เกิดช่วง session ไหน และ spread เฉลี่ยเท่าไร?",
        "ควรเก็บภาพก่อนเข้าไม้/หลังเข้าไม้เพื่อเทียบกับ journal หรือไม่?",
    ])

    score = max(0.0, min(100.0, round(score, 2)))
    if score >= 75:
        verdict = "strong_research_candidate"
    elif score >= 50:
        verdict = "watchlist_candidate"
    elif plan.action == "hold":
        verdict = "no_trade_observation"
    else:
        verdict = "weak_candidate"

    return PlanAnalysis(
        verdict=verdict,
        score=score,
        strengths=strengths,
        weaknesses=weaknesses,
        next_questions=next_questions,
        improvement_notes=improvement_notes,
    )


def analysis_to_report(analysis: PlanAnalysis) -> dict[str, Any]:
    return asdict(analysis)


def format_analysis_thai(analysis: PlanAnalysis) -> str:
    lines = [
        f"Plan analysis: {analysis.verdict}",
        f"research score: {analysis.score:.0f}/100",
    ]
    if analysis.strengths:
        lines.append("จุดแข็ง:")
        lines.extend(f"- {item}" for item in analysis.strengths)
    if analysis.weaknesses:
        lines.append("จุดอ่อน/สิ่งที่ต้องระวัง:")
        lines.extend(f"- {item}" for item in analysis.weaknesses)
    if analysis.improvement_notes:
        lines.append("แนวทางพัฒนาต่อ:")
        lines.extend(f"- {item}" for item in analysis.improvement_notes)
    return "\n".join(lines)

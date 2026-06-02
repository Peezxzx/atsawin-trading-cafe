# Integration contract draft

เอกสารนี้เป็น contract สำหรับเชื่อม Atsawin Trading Cafe กับ EA/MT5 ภายหลัง

## Trade event payload

```json
{
  "event_type": "trade_closed",
  "source": "mt5_ea",
  "symbol": "XAUUSDm",
  "side": "BUY",
  "entry_price": 2300.0,
  "exit_price": 2312.5,
  "volume": 0.01,
  "pnl": 12.5,
  "risk_percent": 2.5,
  "setup": "ema-rsi",
  "opened_at": "2026-06-02T10:00:00",
  "closed_at": "2026-06-02T10:30:00",
  "note": "manual execution, journal import only"
}
```

## Bot status payload

```json
{
  "source": "bridge_mt5_pro",
  "state": "running",
  "last_seen": "2026-06-02T10:30:00",
  "error": "",
  "raw_log": "latest signal SELL confidence=0.76"
}
```

## Safety rules

- Trading Cafe รับข้อมูลได้ทันที แต่ไม่ควรส่ง order โดยตรงใน phase แรก
- ถ้ามี future order flow ต้องมี manual confirmation
- ทุก signal/order suggestion ต้องมี invalidation, risk, and reason
- ห้ามรับประกันกำไรหรือบอกว่า AI ตัดสินใจแทนผู้ใช้

## Trading Cafe report payload

Trading Cafe อ่าน signal + MT5 live account/tick แล้วเขียนรายงานนี้กลับไปใน Common Files:

```json
{
  "schema_version": "trading_cafe_report_v1",
  "timestamp": "2026-06-02T10:31:00+00:00",
  "source_signal": "bridge_mt5_pro_v2",
  "plan": {
    "allowed": true,
    "action": "sell",
    "symbol": "XAUUSD",
    "mt5_symbol": "XAUUSDm",
    "confidence": 0.76,
    "entry_price": 4480.0,
    "stop_loss": 4485.0,
    "take_profit": 4470.0,
    "bridge_rr": 2.0,
    "actual_rr": 2.0,
    "calculated_lot": 0.02,
    "risk_percent": 2.5,
    "risk_amount": 12.5,
    "spread_points": 308.0,
    "warnings": [],
    "reasons": ["trend_down", "confirm_down"]
  },
  "thai_summary": "Pre-trade plan: XAUUSDm SELL — คุณภาพแผนผ่านเกณฑ์...",
  "analysis": {
    "verdict": "watchlist_candidate",
    "score": 65,
    "strengths": ["มี directional setup: SELL"],
    "weaknesses": [],
    "next_questions": ["ถ้าเข้าไม้ตามแผนนี้ ผลลัพธ์หลัง N แท่งเป็น TP, SL หรือ no-hit?"],
    "improvement_notes": ["ควรบันทึกผลลัพธ์แยกตาม spread bucket"]
  },
  "analysis_thai": "Plan analysis: watchlist_candidate..."
}
```

รายงานนี้ใช้ได้กับ dashboard/Telegram/journal/research ทันที โดยยังไม่ใช่คำสั่งให้ EA เปิดไม้ และยังไม่ใช้เป็น gate ของ EA ใน phase นี้

## History storage

ทุกครั้งที่ `mt5_live` รันโดยไม่ใส่ `--no-history` ระบบจะบันทึก observation ลง SQLite และ CSV:

```text
trading_cafe_history.sqlite
trading_cafe_history.csv
```

ตาราง `plan_history` เก็บ field สำคัญ เช่น:

- observed_at
- signal_hash
- symbol/action
- verdict/score
- confidence
- entry_price / stop_loss / take_profit
- bridge_rr / actual_rr
- calculated_lot / risk_percent / risk_amount
- spread_points
- warnings/reasons
- outcome แบบ live observation: `open_observation`, `tp_seen`, `sl_seen`, `no_trade_observation`
- full report_json

หมายเหตุ: outcome ตอนนี้เป็นการตรวจจากราคาปัจจุบันตอนรัน ไม่ใช่ full backtest จาก future bars ยังเหมาะสำหรับสะสม journal/research ก่อน แล้วค่อยเพิ่ม evaluator จาก candle history ใน phase ต่อไป

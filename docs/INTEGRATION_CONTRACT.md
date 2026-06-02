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

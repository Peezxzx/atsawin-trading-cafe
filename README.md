# Atsawin Trading Cafe

โปรเจกต์ใหม่สำหรับระบบ Trading Journal / Trading Cafe ของ Meawbin Investor

โปรเจกต์นี้แยกจาก EA และ MT5 execution layer ตั้งใจให้เป็นพื้นที่กลางสำหรับ:

- จด trade journal
- รวมข้อมูล trade, bot, account, risk, report, log
- สรุป performance รายวัน/สัปดาห์/เดือน
- แปล bot log และข้อมูล technical ให้อ่านง่าย
- เตือนพฤติกรรมเสี่ยง เช่น overtrade, revenge trade, risk เกินแผน
- เตรียม contract สำหรับเชื่อมกับ EA/MT5 ภายหลัง

## Positioning

ระบบนี้ไม่ใช่บอทเทรด ไม่ใช่ระบบทำนายตลาด และไม่ใช่เครื่องมือรับประกันกำไร

AI ในโปรเจกต์นี้คือผู้ช่วยจัดระเบียบชีวิตเทรดเดอร์:

> จด สรุป เตือน แปล log และทำให้เห็นภาพรวมชัดขึ้น

หลักคิด:

> กลยุทธ์ที่ดีต้องทำกำไรได้ และนอนหลับสบาย

## โครงสร้าง

```text
atsawin-trading-cafe/
├── src/atsawin_trading_cafe/
│   ├── prompts.py        # Project system prompt / guardrails
│   ├── models.py         # Data models for journal, bot status, reports
│   ├── journal.py        # Journal summary logic
│   ├── risk.py           # Risk warning rules
│   └── app.py            # Optional FastAPI app
├── tests/
│   ├── test_prompts.py
│   ├── test_journal.py
│   └── test_risk.py
└── docs/
    ├── PROJECT_CONTEXT.md
    └── INTEGRATION_CONTRACT.md
```

## Quick test

```bash
cd C:\Users\Administrator\repos\atsawin-trading-cafe
python -m py_compile src/atsawin_trading_cafe/*.py tests/*.py
python tests/test_prompts.py
python tests/test_journal.py
python tests/test_risk.py
```

## Run API แบบ optional

ถ้ามี fastapi/uvicorn แล้ว:

```bash
uvicorn atsawin_trading_cafe.app:app --reload --host 127.0.0.1 --port 8010
```

Endpoint หลัก:

- `GET /health`
- `GET /context`
- `POST /journal/summarize`
- `POST /risk/check`

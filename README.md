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

## เชื่อมกับ EA / MT5

โปรเจกต์นี้เชื่อมกับ EA ผ่านไฟล์ Common เดียวกับที่ EA ใช้อยู่:

```text
C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common\Files\atsawin\latest_signal.json
```

Trading Cafe จะอ่าน `latest_signal.json`, ดึงข้อมูล live account/tick จาก MT5, คำนวณ pre-trade plan แล้วเขียนรายงานกลับไปที่:

```text
C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common\Files\atsawin\trading_cafe_report.json
```

และบันทึก history เพื่อใช้พัฒนากลยุทธ์ต่อที่:

```text
C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common\Files\atsawin\trading_cafe_history.sqlite
C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common\Files\atsawin\trading_cafe_history.csv
```

รันแบบครั้งเดียว:

```bash
cd C:\Users\Administrator\repos\atsawin-trading-cafe
python -m atsawin_trading_cafe.mt5_live --login 433684944 --server Exness-MT5Trial7 --risk-percent 2.5 --max-lot 1.0 --summary
```

รันแบบ watch ทุก 30 วินาที:

```bash
python -m atsawin_trading_cafe.mt5_live --login 433684944 --server Exness-MT5Trial7 --risk-percent 2.5 --max-lot 1.0 --watch --interval 30
```

หน้าที่ตอนนี้:

- EA/bridge เดิมยังเป็นตัวสร้าง signal และ execute order ตามระบบเดิม
- Trading Cafe อ่าน signal เดียวกันเพื่อคำนวณ entry, lot, actual RR, spread, warning และวิเคราะห์คุณภาพแผน
- `trading_cafe_report.json` ใช้เพื่อ dashboard/Telegram/journal/research เท่านั้น ยังไม่ใช้เป็นคำสั่งหรือ gate ให้ EA
- อนาคตถ้าจะให้ EA เอาผลวิเคราะห์ไปใช้ค่อยออกแบบเพิ่มอีกที

## Quick test

```bash
cd C:\Users\Administrator\repos\atsawin-trading-cafe
python -m py_compile src/atsawin_trading_cafe/*.py tests/*.py
python tests/test_prompts.py
python tests/test_journal.py
python tests/test_risk.py
python tests/test_mt5_contract.py
python tests/test_plan_analysis.py
python tests/test_history_store.py
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

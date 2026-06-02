# Project context: Atsawin Trading Cafe

Atsawin Trading Cafe เป็นโปรเจกต์ใหม่ แยกจาก EA/MT5 execution layer

เป้าหมายแรกคือสร้างระบบกลางสำหรับชีวิตเทรดเดอร์:

- Journal: จด trade และเหตุผล
- Report: สรุป performance
- Risk Watch: เตือนพฤติกรรมเสี่ยง
- Bot Log: แปล log ให้อ่านง่าย
- Dashboard Contract: เตรียมข้อมูลให้ frontend / Telegram / EA integration

## Boundary

โปรเจกต์นี้ยังไม่ส่ง order และไม่ยุ่งกับ execution โดยตรง

EA/MT5 จะยังอยู่แยกต่างหาก จนกว่าจะเชื่อมผ่าน contract ที่ปลอดภัย เช่น read-only status, journal import, report sync หรือ manual confirmation workflow

## Future integration idea

1. EA ส่ง trade events/logs เข้ามา Trading Cafe
2. Trading Cafe สรุป journal และ risk
3. ผู้ใช้ดู dashboard หรือ Telegram report
4. ถ้าจะส่ง signal/order ต้องมี human confirmation และ risk guardrails ก่อนเสมอ

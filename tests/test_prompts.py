import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from atsawin_trading_cafe.prompts import ATSAWIN_TRADING_CAFE_SYSTEM_PROMPT, build_messages


assert "Atsawin Trading Cafe" in ATSAWIN_TRADING_CAFE_SYSTEM_PROMPT
assert "ห้ามรับประกันกำไร" in ATSAWIN_TRADING_CAFE_SYSTEM_PROMPT
assert "ห้ามออกคำสั่ง BUY/SELL แบบฟันธง" in ATSAWIN_TRADING_CAFE_SYSTEM_PROMPT
assert "กลยุทธ์ที่ดีต้องทำกำไรได้ และนอนหลับสบาย" in ATSAWIN_TRADING_CAFE_SYSTEM_PROMPT

messages = build_messages("ควรเข้า BUY ไหม", "XAUUSD อยู่ใกล้ key level")
assert messages[0]["role"] == "system"
assert messages[1]["role"] == "user"
assert "บริบทเพิ่มเติม" in messages[1]["content"]
assert "ควรเข้า BUY ไหม" in messages[1]["content"]

print("All prompt tests passed.")

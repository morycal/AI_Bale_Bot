import requests
import time
from core.config import BALE_TOKEN
from bot.handlers import handle

BASE = f"https://tapi.bale.ai/bot{BALE_TOKEN}"
offset = 0

def send(chat_id, text):
    requests.post(BASE + "/sendMessage",
                  json={"chat_id": chat_id, "text": text})

while True:
    try:
        res = requests.get(BASE + "/getUpdates",
                           params={"offset": offset, "timeout": 30}).json()

        for u in res.get("result", []):
            offset = u["update_id"] + 1

            msg = u.get("message")
            if not msg:
                continue

            chat_id = msg["chat"]["id"]
            uid = msg["from"]["id"]
            text = msg.get("text", "")

            if text == "/start":
                send(chat_id, "🤖 سلام! من ربات AI حرفه‌ای هستم.")
                continue

            reply = handle(uid, text)
            send(chat_id, reply)

    except Exception as e:
        print(e)

    time.sleep(1)
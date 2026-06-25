import requests
import asyncio
import aiosqlite
import time
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BALE_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

BASE = f"https://tapi.bale.ai/bot{TOKEN}"

offset = None


# ================= SEND MESSAGE =================

def send(chat_id, text):
    try:
        requests.post(BASE + "/sendMessage", json={
            "chat_id": chat_id,
            "text": text
        }, timeout=10)
    except:
        pass


# ================= GET UPDATES =================

def get_updates():
    global offset
    try:
        r = requests.get(BASE + "/getUpdates", params={"offset": offset}, timeout=30)
        return r.json()
    except:
        return {"result": []}


# ================= AI =================

def ask_ai(text):
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "deepseek/deepseek-r1:free",
                "messages": [
                    {"role": "system", "content": "تو یک دستیار هوشمند هستی."},
                    {"role": "user", "content": text}
                ]
            },
            timeout=30
        )

        data = res.json()

        if "choices" not in data:
            return f"❌ API ERROR: {data}"

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ AI ERROR: {str(e)}"


# ================= LOOP =================

async def main():

    global offset

    print("🤖 BOT STARTED (FIXED MODE)")

    while True:

        data = get_updates()

        for update in data.get("result", []):

            offset = update["update_id"] + 1

            msg = update.get("message", {})
            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id")

            if not text:
                continue

            # START
            if text == "/start":
                send(chat_id, "👋 ربات فعال شد")
                continue

            # RESET
            if text == "/reset":
                send(chat_id, "🧹 انجام شد")
                continue

            # THINKING
            send(chat_id, "⏳ در حال فکر کردن...")

            # AI
            answer = ask_ai(text)

            send(chat_id, answer[:3500])

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())

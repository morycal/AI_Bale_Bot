import requests
import asyncio
import aiosqlite
import time
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BALE_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
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
        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "model": "Qwen/Qwen3-32B",
                "messages": [
                    {
                        "role": "system",
                        "content": "تو یک دستیار هوش مصنوعی حرفه‌ای هستی و به فارسی پاسخ می‌دهی."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            },
            timeout=60
        )

        data = response.json()

        print("HF RESPONSE:", data)

        if "choices" in data:
            return data["choices"][0]["message"]["content"]

        if "error" in data:
            return f"❌ HF Error: {data['error']}"

        return "❌ پاسخ نامعتبر از Hugging Face"

    except Exception as e:
        return f"❌ AI Error: {str(e)}"


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

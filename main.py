import requests
import asyncio
import os
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

BALE_TOKEN = os.getenv("BALE_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

BASE = f"https://tapi.bale.ai/bot{BALE_TOKEN}"

offset = None


# ================= SEND MESSAGE =================

def send(chat_id, text):
    try:
        r = requests.post(
            BASE + "/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            },
            timeout=20
        )

        print("SEND:", r.status_code)

    except Exception as e:
        print("SEND ERROR:", e)


# ================= SEND PHOTO =================

def send_photo(chat_id, image_bytes):
    try:
        r = requests.post(
            BASE + "/sendPhoto",
            data={
                "chat_id": chat_id
            },
            files={
                "photo": ("image.png", image_bytes)
            },
            timeout=120
        )

        print("PHOTO:", r.status_code)
        print(r.text)

    except Exception as e:
        print("PHOTO ERROR:", e)


# ================= GET UPDATES =================

def get_updates():
    global offset

    try:
        r = requests.get(
            BASE + "/getUpdates",
            params={
                "offset": offset
            },
            timeout=30
        )

        return r.json()

    except Exception as e:
        print("UPDATE ERROR:", e)
        return {"result": []}


# ================= AI =================

def ask_ai(text):
    try:

        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-oss-120b",
                "messages": [
                    {
                        "role": "system",
                        "content": "تو یک دستیار هوش مصنوعی فارسی حرفه‌ای هستی."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            },
            timeout=60
        )

        data = r.json()

        print("GROQ STATUS:", r.status_code)
        print("GROQ RESPONSE:", data)

        if "choices" not in data:
            return f"❌ GROQ ERROR\n{data}"

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ AI ERROR: {e}"


# ================= IMAGE =================

def generate_image(prompt):
    try:

        url = f"https://image.pollinations.ai/prompt/{quote(prompt)}"

        r = requests.get(
            url,
            timeout=120
        )

        print("IMG STATUS:", r.status_code)

        if r.status_code == 200:
            return r.content

        return None

    except Exception as e:
        print("IMG ERROR:", e)
        return None


# ================= MAIN =================

async def main():

    global offset

    print("🤖 FREE AI BOT ONLINE")

    while True:

        data = get_updates()

        for update in data.get("result", []):

            try:

                offset = update["update_id"] + 1

                msg = update.get("message", {})

                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")

                if not chat_id:
                    continue

                # ===== START =====

                if text == "/start":

                    send(
                        chat_id,
                        "👋 سلام\n\n"
                        "دستورات:\n"
                        "/img متن تصویر\n"
                        "/help"
                    )

                    continue

                # ===== HELP =====

                if text == "/help":

                    send(
                        chat_id,
                        "🧠 چت هوش مصنوعی\n"
                        "🎨 ساخت تصویر:\n"
                        "/img گربه فضانورد"
                    )

                    continue

                # ===== IMAGE =====

                if text.startswith("/img"):

                    prompt = text.replace("/img", "").strip()

                    if not prompt:

                        send(
                            chat_id,
                            "❌ بعد از /img توضیح تصویر را بنویس"
                        )

                        continue

                    send(
                        chat_id,
                        "🎨 در حال ساخت تصویر..."
                    )

                    img = generate_image(prompt)

                    if img:
                        send_photo(chat_id, img)
                    else:
                        send(
                            chat_id,
                            "❌ تصویر ساخته نشد"
                        )

                    continue

                # ===== CHAT =====

                if not text:
                    continue

                send(
                    chat_id,
                    "⏳ در حال فکر کردن..."
                )

                answer = ask_ai(text)

                send(
                    chat_id,
                    answer[:3500]
                )

            except Exception as e:

                print("MESSAGE ERROR:", e)

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())

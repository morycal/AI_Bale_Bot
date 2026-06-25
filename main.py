import requests
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

BALE_TOKEN = os.getenv("BALE_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

BASE = f"https://tapi.bale.ai/bot{BALE_TOKEN}"
offset = None


# ================= SEND =================

def send(chat_id, text):
    try:
        requests.post(BASE + "/sendMessage", json={
            "chat_id": chat_id,
            "text": text
        })
    except:
        pass


def send_photo(chat_id, img_bytes):
    try:
        requests.post(
            BASE + "/sendPhoto",
            data={"chat_id": chat_id},
            files={"photo": ("img.png", img_bytes)}
        )
    except:
        pass


# ================= UPDATES =================

def get_updates():
    global offset
    try:
        r = requests.get(BASE + "/getUpdates", params={"offset": offset}, timeout=30)
        return r.json()
    except:
        return {"result": []}


# ================= AI (GROQ - FAST CHATGPT) =================

def ask_ai(text):
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "system", "content": "تو یک دستیار هوش مصنوعی فارسی حرفه‌ای هستی."},
                    {"role": "user", "content": text}
                ]
            },
            timeout=30
        )

        data = res.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ AI Error: {e}"


# ================= IMAGE (REPLICATE) =================

def generate_image(prompt):
    try:
        res = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers={
                "Authorization": f"Token {REPLICATE_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "version": "db21e45c...stable-diffusion-xl",  # SDXL model id
                "input": {"prompt": prompt}
            }
        )

        data = res.json()

        if "urls" in data:
            get_url = data["urls"]["get"]

            # poll
            for _ in range(20):
                r = requests.get(get_url, headers={
                    "Authorization": f"Token {REPLICATE_API_TOKEN}"
                }).json()

                if r.get("status") == "succeeded":
                    img_url = r["output"][0]
                    return requests.get(img_url).content

        return None

    except Exception as e:
        print("IMG ERROR:", e)
        return None


# ================= VOICE (REPLICATE WHISPER) =================

def voice_to_text(audio):
    try:
        res = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers={
                "Authorization": f"Token {REPLICATE_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "version": "whisper-version-id",
                "input": {
                    "audio": audio
                }
            }
        )

        data = res.json()

        if "urls" in data:
            get_url = data["urls"]["get"]

            for _ in range(20):
                r = requests.get(get_url, headers={
                    "Authorization": f"Token {REPLICATE_API_TOKEN}"
                }).json()

                if r.get("status") == "succeeded":
                    return r["output"]["text"]

        return ""

    except Exception as e:
        print("VOICE ERROR:", e)
        return ""


# ================= MAIN LOOP =================

async def main():

    global offset

    print("🤖 GROQ + REPLICATE BOT ONLINE")

    while True:

        data = get_updates()

        for update in data.get("result", []):

            offset = update["update_id"] + 1

            msg = update.get("message", {})
            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id")

            voice = msg.get("voice")

            if not chat_id:
                continue

            # ================= VOICE =================
            if voice:
                send(chat_id, "🎧 در حال تبدیل ویس...")

                # فعلاً ساده (بعداً فایل کامل می‌کنیم)
                send(chat_id, "⚠️ ویس در نسخه بعد کامل می‌شود")
                continue

            # ================= IMAGE =================
            if text.startswith("/img"):
                prompt = text.replace("/img", "").strip()

                send(chat_id, "🎨 در حال ساخت تصویر...")

                img = generate_image(prompt)

                if img:
                    send_photo(chat_id, img)
                else:
                    send(chat_id, "❌ تصویر ساخته نشد")

                continue

            # ================= CHAT =================
            if not text:
                continue

            send(chat_id, "⏳ فکر می‌کنم...")

            answer = ask_ai(text)

            send(chat_id, answer[:3500])


if __name__ == "__main__":
    asyncio.run(main())

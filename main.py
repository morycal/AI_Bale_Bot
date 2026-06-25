import requests
import asyncio
import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BALE_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

BASE = f"https://tapi.bale.ai/bot{TOKEN}"
offset = None


# ================= SEND =================

def send(chat_id, text):
    try:
        requests.post(BASE + "/sendMessage", json={
            "chat_id": chat_id,
            "text": text
        }, timeout=15)
    except Exception as e:
        print("SEND ERROR:", e)


def send_photo(chat_id, img_bytes):
    try:
        requests.post(
            BASE + "/sendPhoto",
            data={"chat_id": chat_id},
            files={"photo": ("img.png", img_bytes)},
            timeout=30
        )
    except Exception as e:
        print("PHOTO ERROR:", e)


# ================= UPDATES =================

def get_updates():
    global offset
    try:
        r = requests.get(BASE + "/getUpdates", params={"offset": offset}, timeout=30)
        return r.json()
    except Exception as e:
        print("UPDATE ERROR:", e)
        return {"result": []}


# ================= AI CHAT (HF ROUTER) =================

def ask_ai(text):
    try:
        res = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={
                "model": "Qwen/Qwen3-32B",
                "messages": [
                    {"role": "system", "content": "تو یک دستیار هوش مصنوعی فارسی هستی."},
                    {"role": "user", "content": text}
                ]
            },
            timeout=60
        )

        data = res.json()
        print("AI:", data)

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ AI Error: {e}"


# ================= IMAGE (SAFE MODE) =================

def generate_image(prompt):
    try:
        res = requests.post(
            "https://router.huggingface.co/v1/images/generations",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={
                "model": "stabilityai/stable-diffusion-xl-base-1.0",
                "prompt": prompt
            },
            timeout=120
        )

        print("IMG:", res.text[:200])

        data = res.json()

        # اگر لینک داد
        if "data" in data and len(data["data"]) > 0:
            url = data["data"][0].get("url")
            if url:
                return requests.get(url).content

        return None

    except Exception as e:
        print("IMG ERROR:", e)
        return None


# ================= VOICE (FALLBACK SAFE) =================

def download_voice(file_id):
    try:
        file = requests.get(BASE + f"/getFile?file_id={file_id}").json()
        path = file["result"]["file_path"]

        url = f"https://tapi.bale.ai/file/bot{TOKEN}/{path}"

        return requests.get(url).content

    except:
        return None


def voice_to_text(audio):
    try:
        res = requests.post(
            "https://router.huggingface.co/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            files={"file": audio},
            data={"model": "openai/whisper-small"},
            timeout=120
        )

        print("VOICE:", res.text[:200])

        data = res.json()

        return data.get("text", "")

    except Exception as e:
        print("VOICE ERROR:", e)
        return ""


# ================= MAIN LOOP =================

async def main():

    global offset

    print("🤖 ROBUST BOT ONLINE")

    while True:

        data = get_updates()

        for update in data.get("result", []):

            offset = update["update_id"] + 1

            msg = update.get("message", {})
            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id")
            user_id = msg.get("from", {}).get("id")
            voice = msg.get("voice")

            if not chat_id:
                continue

            # ================= RESET =================
            if text == "/reset":
                send(chat_id, "🧹 انجام شد")
                continue

            # ================= VOICE =================
            if voice:
                send(chat_id, "🎧 در حال پردازش...")

                audio = download_voice(voice["file_id"])

                if not audio:
                    send(chat_id, "❌ ویس دانلود نشد")
                    continue

                vtext = voice_to_text(audio)

                if not vtext:
                    send(chat_id, "❌ ویس قابل تشخیص نیست")
                    continue

                send(chat_id, f"📝 {vtext}")

                answer = ask_ai(vtext)

                send(chat_id, answer[:3500])
                continue

            # ================= IMAGE =================
            if text.startswith("/img"):
                prompt = text.replace("/img", "").strip()

                if not prompt:
                    send(chat_id, "❌ متن بده")
                    continue

                send(chat_id, "🎨 در حال ساخت تصویر...")

                img = generate_image(prompt)

                if img:
                    send_photo(chat_id, img)
                else:
                    send(chat_id, "❌ ساخت تصویر فعلاً ممکن نیست")

                continue

            # ================= CHAT =================
            if not text:
                continue

            send(chat_id, "⏳ فکر می‌کنم...")

            answer = ask_ai(text)

            send(chat_id, answer[:3500])


if __name__ == "__main__":
    asyncio.run(main())

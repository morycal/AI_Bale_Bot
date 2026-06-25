import requests
import asyncio
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
            timeout=60
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


# ================= CHAT AI =================

def ask_ai(text):
    try:
        res = requests.post(
            "https://api-inference.huggingface.co/models/Qwen/Qwen3-32B",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": text},
            timeout=60
        )

        print("AI STATUS:", res.status_code)
        print("AI TEXT:", res.text[:200])

        data = res.json()

        # بعضی مدل‌ها لیست میدن
        if isinstance(data, list):
            return data[0].get("generated_text", "")

        if isinstance(data, dict):
            return data.get("generated_text", str(data))

        return "❌ پاسخ نامعتبر"

    except Exception as e:
        return f"❌ AI Error: {e}"


# ================= IMAGE (CORRECT HF METHOD) =================

def generate_image(prompt):
    try:
        res = requests.post(
            "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": prompt},
            timeout=120
        )

        print("IMG STATUS:", res.status_code)
        print("IMG TEXT:", res.text[:200])

        if res.status_code != 200:
            return None

        return res.content

    except Exception as e:
        print("IMG ERROR:", e)
        return None


# ================= VOICE (CORRECT HF METHOD) =================

def download_voice(file_id):
    try:
        file = requests.get(BASE + f"/getFile?file_id={file_id}").json()
        path = file["result"]["file_path"]

        url = f"https://tapi.bale.ai/file/bot{TOKEN}/{path}"

        return requests.get(url).content

    except Exception as e:
        print("VOICE DOWNLOAD ERROR:", e)
        return None


def voice_to_text(audio):
    try:
        res = requests.post(
            "https://api-inference.huggingface.co/models/openai/whisper-small",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            data=audio,
            timeout=120
        )

        print("VOICE STATUS:", res.status_code)
        print("VOICE TEXT:", res.text[:200])

        if res.status_code != 200:
            return ""

        data = res.json()

        if isinstance(data, dict):
            return data.get("text", "")

        return ""

    except Exception as e:
        print("VOICE ERROR:", e)
        return ""


# ================= MAIN LOOP =================

async def main():

    global offset

    print("🤖 BOT FIXED VERSION ONLINE")

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
                send(chat_id, "🎧 در حال پردازش ویس...")

                audio = download_voice(voice["file_id"])

                if not audio:
                    send(chat_id, "❌ ویس دانلود نشد")
                    continue

                text_v = voice_to_text(audio)

                if not text_v:
                    send(chat_id, "❌ ویس قابل تشخیص نیست")
                    continue

                send(chat_id, f"📝 متن: {text_v}")

                answer = ask_ai(text_v)

                send(chat_id, answer[:3500])
                continue

            # ================= IMAGE =================
            if text.startswith("/img"):
                prompt = text.replace("/img", "").strip()

                if not prompt:
                    send(chat_id, "❌ متن تصویر بده")
                    continue

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

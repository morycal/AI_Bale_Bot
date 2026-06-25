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
                "model": "openai/gpt-oss-120b",
                "messages": [
                    {
                        "role": "system",
                        "content": "تو یک دستیار هوش مصنوعی فارسی هستی."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            },
            timeout=60
        )

        data = res.json()

        print("GROQ STATUS:", res.status_code)
        print("GROQ RESPONSE:", data)

        if "choices" not in data:
            return f"❌ GROQ ERROR: {data}"

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ AI ERROR: {e}"

# ================= IMAGE (REPLICATE) =================

def generate_image(prompt):

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    create = requests.post(
        "https://api.replicate.com/v1/predictions",
        headers=headers,
        json={
            "model": "black-forest-labs/flux-schnell",
            "input": {
                "prompt": prompt
            }
        },
        timeout=30
    )

    data = create.json()

    if "urls" not in data:
        print(data)
        return None

    get_url = data["urls"]["get"]

    for _ in range(30):

        result = requests.get(
            get_url,
            headers=headers,
            timeout=30
        ).json()

        if result["status"] == "succeeded":

            output = result.get("output")

            if isinstance(output, list):
                img_url = output[0]
            else:
                img_url = output

            return requests.get(img_url).content

        if result["status"] in ["failed", "canceled"]:
            print(result)
            return None

        time.sleep(2)

    return None

# ================= VOICE (REPLICATE WHISPER) =================

def voice_to_text(audio_url):

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    create = requests.post(
        "https://api.replicate.com/v1/predictions",
        headers=headers,
        json={
            "model": "openai/whisper",
            "input": {
                "audio": audio_url
            }
        },
        timeout=30
    )

    data = create.json()

    if "urls" not in data:
        print(data)
        return ""

    get_url = data["urls"]["get"]

    for _ in range(30):

        result = requests.get(
            get_url,
            headers=headers,
            timeout=30
        ).json()

        if result["status"] == "succeeded":

            output = result.get("output")

            if isinstance(output, str):
                return output

            if isinstance(output, dict):
                return output.get("text", "")

            return str(output)

        if result["status"] in ["failed", "canceled"]:
            print(result)
            return ""

        time.sleep(2)

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

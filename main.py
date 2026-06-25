import requests
import asyncio
import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BALE_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

BASE = f"https://tapi.bale.ai/bot{TOKEN}"

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


def send_photo(chat_id, image_bytes):
    try:
        requests.post(
            BASE + "/sendPhoto",
            data={"chat_id": chat_id},
            files={"photo": ("img.png", image_bytes)}
        )
    except:
        pass


# ================= UPDATE =================

def get_updates():
    global offset
    try:
        r = requests.get(BASE + "/getUpdates", params={"offset": offset}, timeout=30)
        return r.json()
    except:
        return {"result": []}


# ================= DB =================

async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS memory(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT
        )
        """)
        await db.commit()


async def save_memory(uid, role, content):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "INSERT INTO memory(user_id,role,content) VALUES(?,?,?)",
            (uid, role, content)
        )
        await db.commit()


async def get_memory(uid):
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute(
            "SELECT role,content FROM memory WHERE user_id=? ORDER BY id DESC LIMIT 20",
            (uid,)
        )
        rows = await cur.fetchall()

    rows.reverse()

    return [{"role": r[0], "content": r[1]} for r in rows]


# ================= AI CHAT =================

async def ask_ai(uid, text):

    history = await get_memory(uid)

    messages = [
        {"role": "system", "content": "تو یک دستیار حرفه‌ای فارسی هستی."}
    ] + history + [
        {"role": "user", "content": text}
    ]

    try:
        res = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "model": "Qwen/Qwen3-32B",
                "messages": messages
            },
            timeout=60
        )

        data = res.json()

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ AI Error: {e}"


# ================= IMAGE =================

def generate_image(prompt):
    try:
        res = requests.post(
            "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": prompt},
            timeout=120
        )

        if res.status_code != 200:
            return None

        return res.content

    except:
        return None


# ================= VOICE =================

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
            "https://api-inference.huggingface.co/models/openai/whisper-large-v3",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            data=audio,
            timeout=120
        )

        data = res.json()

        return data.get("text", "")

    except:
        return ""


# ================= LOOP =================

async def main():

    global offset

    await init_db()

    print("🤖 MULTI CHATGPT BOT ONLINE")

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
                async with aiosqlite.connect("bot.db") as db:
                    await db.execute("DELETE FROM memory WHERE user_id=?", (user_id,))
                    await db.commit()
                send(chat_id, "🧹 حافظه پاک شد")
                continue

            # ================= VOICE =================
            if voice:
                send(chat_id, "🎧 در حال پردازش ویس...")

                audio = download_voice(voice["file_id"])

                if not audio:
                    send(chat_id, "❌ خطا در دریافت ویس")
                    continue

                text = voice_to_text(audio)

                if not text:
                    send(chat_id, "❌ ویس قابل تشخیص نبود")
                    continue

                send(chat_id, f"📝 متن:\n{text}")

                answer = await ask_ai(user_id, text)

                send(chat_id, answer[:3500])

                await save_memory(user_id, "user", text)
                await save_memory(user_id, "assistant", answer)

                continue

            # ================= IMAGE =================
            if text.startswith("/img"):
                prompt = text.replace("/img", "").strip()

                if not prompt:
                    send(chat_id, "❌ متن تصویر را بنویس")
                    continue

                send(chat_id, "🎨 در حال ساخت تصویر...")

                img = generate_image(prompt)

                if img:
                    send_photo(chat_id, img)
                else:
                    send(chat_id, "❌ خطا در ساخت تصویر")

                continue

            # ================= CHAT =================
            if not text:
                continue

            send(chat_id, "⏳ در حال فکر کردن...")

            answer = await ask_ai(user_id, text)

            send(chat_id, answer[:3500])

            await save_memory(user_id, "user", text)
            await save_memory(user_id, "assistant", answer)


if __name__ == "__main__":
    asyncio.run(main())

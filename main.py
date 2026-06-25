import os
import asyncio
import aiosqlite
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BALE_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}/"

FREE_LIMIT = 30
VIP_LIMIT = 300


# ================= HTTP SEND =================

def send(chat_id, text):
    try:
        requests.post(BASE_URL + "sendMessage", json={
            "chat_id": chat_id,
            "text": text
        })
    except:
        pass


# ================= DATABASE =================

async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            count INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0,
            vip INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS memory(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT
        )
        """)

        await db.commit()


async def get_user(uid, name):
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute(
            "SELECT user_id,name,count,banned,vip FROM users WHERE user_id=?",
            (uid,)
        )
        u = await cur.fetchone()

        if not u:
            await db.execute(
                "INSERT INTO users(user_id,name,count,banned,vip) VALUES(?,?,0,0,0)",
                (uid, name)
            )
            await db.commit()
            return {"count": 0, "banned": 0, "vip": 0}

        return {"count": u[2], "banned": u[3], "vip": u[4]}


async def add_count(uid):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "UPDATE users SET count=count+1 WHERE user_id=?",
            (uid,)
        )
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
            "SELECT role,content FROM memory WHERE user_id=? ORDER BY id ASC",
            (uid,)
        )
        rows = await cur.fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows][-20:]


# ================= AI ENGINES =================

def engine_deepseek(messages):
    return requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "model": "deepseek/deepseek-r1:free",
            "messages": messages
        },
        timeout=30
    )


def engine_llama(messages):
    return requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "model": "meta-llama/llama-3-8b-instruct:free",
            "messages": messages
        },
        timeout=30
    )


def engine_fallback():
    return "⚠️ الان همه AI ها در دسترس نیستند، دوباره تلاش کنید."


# ================= AI ROUTER =================

def ask_ai(messages):

    engines = [engine_deepseek, engine_llama]

    for engine in engines:
        try:
            res = engine(messages)
            data = res.json()

            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]

        except:
            continue

    return engine_fallback()


# ================= MAIN LOOP =================

async def main():
    await init_db()

    print("🤖 CHATGPT MULTI-ENGINE BOT ONLINE")

    offset = None

    while True:
        try:
            r = requests.get(BASE_URL + "getUpdates", params={"offset": offset}).json()

            for update in r.get("result", []):

                offset = update["update_id"] + 1

                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")
                user = msg.get("from", {})
                uid = user.get("id")
                name = user.get("first_name", "user")

                if not text:
                    continue

                db_user = await get_user(uid, name)

                if db_user["banned"]:
                    continue

                # START
                if text == "/start":
                    send(chat_id, "👋 سلام! من ChatGPT چندموتوره هستم 🤖")
                    continue

                # RESET
                if text == "/reset":
                    async with aiosqlite.connect("bot.db") as db:
                        await db.execute("DELETE FROM memory WHERE user_id=?", (uid,))
                        await db.commit()
                    send(chat_id, "🧹 حافظه پاک شد")
                    continue

                # LIMIT
                limit = VIP_LIMIT if db_user["vip"] else FREE_LIMIT

                if uid != ADMIN_ID and db_user["count"] >= limit:
                    send(chat_id, "❌ سهمیه شما تمام شد")
                    continue

                await add_count(uid)

                send(chat_id, "⏳ در حال فکر کردن...")

                memory = await get_memory(uid)

                system = {
                    "role": "system",
                    "content": "تو یک دستیار هوشمند حرفه‌ای مثل ChatGPT هستی."
                }

                messages = [system] + memory + [{"role": "user", "content": text}]

                answer = ask_ai(messages)

                send(chat_id, answer[:3500])

                await save_memory(uid, "user", text)
                await save_memory(uid, "assistant", answer)

        except Exception as e:
            print("ERROR:", e)
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())

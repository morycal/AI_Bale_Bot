import os
import asyncio
import aiosqlite
import requests
import bale
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BALE_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

FREE_LIMIT = 30

bot = bale.Bot(TOKEN)

# ---------------- DATABASE ----------------

async def init_db():
    async with aiosqlite.connect("bot.db") as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            count INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0
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
            "SELECT user_id,name,count,banned FROM users WHERE user_id=?",
            (uid,)
        )

        user = await cur.fetchone()

        if not user:
            await db.execute(
                "INSERT INTO users(user_id,name,count,banned) VALUES(?,?,0,0)",
                (uid, name)
            )
            await db.commit()

            return {"user_id": uid, "count": 0, "banned": 0}

        return {
            "user_id": user[0],
            "name": user[1],
            "count": user[2],
            "banned": user[3]
        }


async def add_count(uid):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "UPDATE users SET count = count + 1 WHERE user_id=?",
            (uid,)
        )
        await db.commit()


async def reset_memory(uid):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "DELETE FROM memory WHERE user_id=?",
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

        cur = await db.execute(
            "SELECT id FROM memory WHERE user_id=? ORDER BY id DESC",
            (uid,)
        )

        rows = await cur.fetchall()

        if len(rows) > 10:
            for r in rows[10:]:
                await db.execute("DELETE FROM memory WHERE id=?", (r[0],))

        await db.commit()


async def get_memory(uid):
    async with aiosqlite.connect("bot.db") as db:

        cur = await db.execute(
            "SELECT role,content FROM memory WHERE user_id=? ORDER BY id ASC",
            (uid,)
        )

        rows = await cur.fetchall()

        return [{"role": r[0], "content": r[1]} for r in rows]


# ---------------- AI ----------------

async def ask_ai(uid, text):

    memory = await get_memory(uid)

    memory.append({"role": "user", "content": text})

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        },
        json={
            "model": "deepseek/deepseek-r1:free",
            "messages": memory
        },
        timeout=60
    )

    data = response.json()

    answer = data["choices"][0]["message"]["content"]

    await save_memory(uid, "user", text)
    await save_memory(uid, "assistant", answer)

    return answer


# ---------------- BOT EVENTS ----------------

@bot.event
async def on_ready():
    print("BOT ONLINE")


@bot.event
async def on_message(message):

    if not message.content:
        return

    text = message.content.strip()

    uid = message.author.user_id
    name = message.author.first_name

    user = await get_user(uid, name)

    if user["banned"] == 1:
        return

    # ---------- COMMANDS ----------

    if text == "/start":
        await message.reply(
            "👋 سلام!\n"
            "من دستیار هوش مصنوعی هستم.\n"
            "هر سوالی داری بپرس."
        )
        return

    if text == "/reset":
        await reset_memory(uid)
        await message.reply("🧠 حافظه پاک شد.")
        return

    # ---------- ADMIN ----------
    if uid == ADMIN_ID:

        if text == "/stats":
            async with aiosqlite.connect("bot.db") as db:
                cur = await db.execute("SELECT COUNT(*) FROM users")
                users = (await cur.fetchone())[0]

            await message.reply(f"👥 کاربران: {users}")
            return

    # ---------- LIMIT ----------
    if uid != ADMIN_ID and user["count"] >= FREE_LIMIT:
        await message.reply("❌ سهمیه روزانه شما تمام شده است.")
        return

    await add_count(uid)

    await message.reply("⏳ در حال فکر کردن...")

    try:
        answer = await ask_ai(uid, text)

        if len(answer) > 3500:
            answer = answer[:3500]

        await message.reply(answer)

    except Exception as e:
        await message.reply(f"خطا: {str(e)}")


# ---------------- RUN ----------------

if __name__ == "__main__":
    asyncio.run(init_db())
    bot.run()

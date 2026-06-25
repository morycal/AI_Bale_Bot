import os
import json
import requests
import aiosqlite
import bale
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BALE_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

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
            "SELECT * FROM users WHERE user_id=?",
            (uid,)
        )

        user = await cur.fetchone()

        if not user:
            await db.execute(
                "INSERT INTO users(user_id,name) VALUES(?,?)",
                (uid, name)
            )
            await db.commit()

            return {
                "user_id": uid,
                "count": 0,
                "banned": 0
            }

        return {
            "user_id": user[0],
            "count": user[2],
            "banned": user[3]
        }


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

        cur = await db.execute(
            """
            SELECT id FROM memory
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (uid,)
        )

        rows = await cur.fetchall()

        if len(rows) > 10:
            for row in rows[10:]:
                await db.execute(
                    "DELETE FROM memory WHERE id=?",
                    (row[0],)
                )

        await db.commit()


async def get_memory(uid):
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute(
            """
            SELECT role,content
            FROM memory
            WHERE user_id=?
            ORDER BY id ASC
            """,
            (uid,)
        )

        rows = await cur.fetchall()

        msgs = []

        for role, content in rows:
            msgs.append({
                "role": role,
                "content": content
            })

        return msgs


# ---------------- AI ----------------

async def ask_ai(uid, text):

    memory = await get_memory(uid)

    memory.append({
        "role": "user",
        "content": text
    })

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization":
            f"Bearer {OPENROUTER_API_KEY}"
        },
        json={
            "model": "deepseek/deepseek-r1:free",
            "messages": memory
        },
        timeout=120
    )

    data = response.json()

    answer = data["choices"][0]["message"]["content"]

    await save_memory(uid, "user", text)
    await save_memory(uid, "assistant", answer)

    return answer


# ---------------- COMMANDS ----------------

@bot.event
async def on_ready():
    print("BOT ONLINE")


@bot.event
async def on_message(message):

    if not message.content:
        return

    text = message.content

    uid = message.author.user_id
    name = message.author.first_name

    user = await get_user(uid, name)

    if user["banned"] == 1:
        return

    if text == "/start":
        await message.reply(
            "سلام 👋\n"
            "من دستیار هوش مصنوعی هستم.\n"
            "سوالت رو بپرس."
        )
        return

    if text == "/reset":
        async with aiosqlite.connect("bot.db") as db:
            await db.execute(
                "DELETE FROM memory WHERE user_id=?",
                (uid,)
            )
            await db.commit()

        await message.reply("حافظه پاک شد.")
        return

    if uid != ADMIN_ID and user["count"] >= FREE_LIMIT:
        await message.reply(
            "سهمیه روزانه شما تمام شده است."
        )
        return

    if uid == ADMIN_ID and text == "/stats":

        async with aiosqlite.connect("bot.db") as db:

            cur = await db.execute(
                "SELECT COUNT(*) FROM users"
            )

            users = (await cur.fetchone())[0]

        await message.reply(
            f"تعداد کاربران: {users}"
        )

        return

    await add_count(uid)

    await message.reply("⏳ در حال پردازش...")

    try:
        answer = await ask_ai(uid, text)

        if len(answer) > 4000:
            answer = answer[:4000]

        await message.reply(answer)

    except Exception as e:
        await message.reply(
            f"خطا:\n{str(e)}"
        )


bot.run()

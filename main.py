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

bot = bale.Bot(TOKEN)

FREE_LIMIT = 30
VIP_LIMIT = 300


# ---------------- DB ----------------

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


# ---------------- USER ----------------

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

        return {
            "count": u[2],
            "banned": u[3],
            "vip": u[4]
        }


async def add_count(uid):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "UPDATE users SET count=count+1 WHERE user_id=?",
            (uid,)
        )
        await db.commit()


async def set_vip(uid, value):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "UPDATE users SET vip=? WHERE user_id=?",
            (value, uid)
        )
        await db.commit()


async def ban(uid):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "UPDATE users SET banned=1 WHERE user_id=?",
            (uid,)
        )
        await db.commit()


# ---------------- MEMORY ----------------

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

        if len(rows) > 15:
            for r in rows[15:]:
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

    system = {
        "role": "system",
        "content": "تو یک دستیار هوشمند، دقیق، خلاصه و کاربردی هستی."
    }

    messages = [system] + memory + [{"role": "user", "content": text}]

    res = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "model": "deepseek/deepseek-r1:free",
            "messages": messages
        },
        timeout=60
    )

    data = res.json()
    answer = data["choices"][0]["message"]["content"]

    await save_memory(uid, "user", text)
    await save_memory(uid, "assistant", answer)

    return answer


# ---------------- KEYBOARDS ----------------

def main_menu():
    return {
        "inline_keyboard": [
            [{"text": "💬 شروع چت", "callback_data": "chat"}],
            [{"text": "🧹 پاک کردن حافظه", "callback_data": "reset"}],
            [{"text": "👑 پنل ادمین", "callback_data": "admin"}]
        ]
    }


def admin_menu():
    return {
        "inline_keyboard": [
            [{"text": "📊 آمار", "callback_data": "stats"}],
            [{"text": "⭐ VIP دادن", "callback_data": "vip"}],
            [{"text": "🚫 بن کاربر", "callback_data": "ban"}]
        ]
    }


# ---------------- EVENTS ----------------

@bot.event
async def on_ready():
    print("🚀 BOT PRO MAX ONLINE")


@bot.event
async def on_message(message):

    if not message.content:
        return

    text = message.content.strip()
    uid = message.author.user_id
    name = message.author.first_name

    user = await get_user(uid, name)

    if user["banned"]:
        return

    # START
    if text == "/start":
        await message.reply("👋 خوش آمدی", reply_markup=main_menu())
        return

    # RESET
    if text == "/reset":
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("DELETE FROM memory WHERE user_id=?", (uid,))
            await db.commit()

        await message.reply("🧹 حافظه پاک شد")
        return

    # LIMIT
    limit = VIP_LIMIT if user["vip"] else FREE_LIMIT

    if uid != ADMIN_ID and user["count"] >= limit:
        await message.reply("❌ سهمیه تمام شد")
        return

    await add_count(uid)

    await message.reply("⏳ در حال پردازش...")

    try:
        answer = await ask_ai(uid, text)
        await message.reply(answer[:3500])

    except Exception as e:
        await message.reply(f"خطا: {e}")


# ---------------- CALLBACKS ----------------

@bot.event
async def on_callback_query(call):

    uid = call.from_user.user_id
    data = call.data

    # CHAT
    if data == "chat":
        await call.message.reply("💬 سوالت رو بپرس")

    # RESET
    elif data == "reset":
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("DELETE FROM memory WHERE user_id=?", (uid,))
            await db.commit()

        await call.message.reply("🧹 حافظه پاک شد")

    # ADMIN
    elif data == "admin" and uid == ADMIN_ID:
        await call.message.reply("👑 پنل ادمین", reply_markup=admin_menu())

    # STATS
    elif data == "stats" and uid == ADMIN_ID:
        async with aiosqlite.connect("bot.db") as db:
            cur = await db.execute("SELECT COUNT(*) FROM users")
            users = (await cur.fetchone())[0]

        await call.message.reply(f"👥 کاربران: {users}")

    # VIP (دمو)
    elif data == "vip" and uid == ADMIN_ID:
        await call.message.reply("برای VIP باید نسخه کامل‌تر اضافه شود")

    # BAN (دمو)
    elif data == "ban" and uid == ADMIN_ID:
        await call.message.reply("این بخش در نسخه بعدی کامل می‌شود")


# ---------------- RUN ----------------

if __name__ == "__main__":
    asyncio.run(init_db())
    bot.run()

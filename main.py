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
            return {"vip": 0, "count": 0, "banned": 0}

        return {
            "vip": u[4],
            "count": u[2],
            "banned": u[3]
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


async def ban_user(uid):
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

        if len(rows) > 12:
            for r in rows[12:]:
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

    system_prompt = {
        "role": "system",
        "content": "تو یک دستیار هوش مصنوعی حرفه‌ای، دقیق و خلاصه هستی."
    }

    messages = [system_prompt] + memory + [{"role": "user", "content": text}]

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "model": "deepseek/deepseek-r1:free",
            "messages": messages
        },
        timeout=60
    )

    data = response.json()
    answer = data["choices"][0]["message"]["content"]

    await save_memory(uid, "user", text)
    await save_memory(uid, "assistant", answer)

    return answer


# ---------------- MENU ----------------

def main_menu():
    return bale.InlineKeyboardMarkup([
        [bale.InlineKeyboardButton("🧠 چت", callback_data="chat")],
        [bale.InlineKeyboardButton("🧹 پاک کردن حافظه", callback_data="reset")],
        [bale.InlineKeyboardButton("👑 پنل ادمین", callback_data="admin")]
    ])


def admin_menu():
    return bale.InlineKeyboardMarkup([
        [bale.InlineKeyboardButton("📊 آمار", callback_data="stats")],
        [bale.InlineKeyboardButton("🚫 بن کاربر", callback_data="ban")],
        [bale.InlineKeyboardButton("⭐ VIP", callback_data="vip")]
    ])


# ---------------- EVENTS ----------------

@bot.event
async def on_ready():
    print("BOT ONLINE (PRO VERSION)")


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

    if call.data == "chat":
        await call.message.reply("💬 سوالت رو بپرس")

    elif call.data == "reset":
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("DELETE FROM memory WHERE user_id=?", (uid,))
            await db.commit()

        await call.message.reply("🧹 پاک شد")

    elif call.data == "admin" and uid == ADMIN_ID:
        await call.message.reply("👑 پنل ادمین", reply_markup=admin_menu())

    elif call.data == "stats" and uid == ADMIN_ID:
        async with aiosqlite.connect("bot.db") as db:
            cur = await db.execute("SELECT COUNT(*) FROM users")
            users = (await cur.fetchone())[0]

        await call.message.reply(f"👥 کاربران: {users}")

    elif call.data == "vip" and uid == ADMIN_ID:
        await call.message.reply("برای VIP باید دستی فعال شود (قابل توسعه)")

    elif call.data == "ban" and uid == ADMIN_ID:
        await call.message.reply("ارسال ID کاربر برای بن (نسخه بعدی توسعه می‌دهیم)")


# ---------------- RUN ----------------

if __name__ == "__main__":
    asyncio.run(init_db())
    bot.run()

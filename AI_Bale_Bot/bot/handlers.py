from core.database import save_msg, get_history
from bot.ai import ask_ai

def handle(uid, text):

    save_msg(uid, "user", text)

    history = get_history(uid, 10)

    reply = ask_ai(history)

    save_msg(uid, "assistant", reply)

    return reply
import requests
import random

# پاسخ‌های آماده هوشمند
FALLBACK_ANSWERS = [
    "سوالت جالبه 👀 بیشتر توضیح میدی؟",
    "الان دقیق متوجه نشدم، واضح‌تر بگو 🙂",
    "من دارم یاد می‌گیرم، میشه ساده‌تر بپرسی؟",
    "به نظرم بهتره اینو مرحله‌به‌مرحله بررسی کنیم 🔍"
]

# سرچ رایگان از ویکی‌پدیا
def wiki_search(query):
    try:
        url = f"https://fa.wikipedia.org/api/rest_v1/page/summary/{query}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("extract")
    except:
        pass
    return None


# هوش مصنوعی رایگان ترکیبی
def ask_ai(messages):
    # آخرین پیام کاربر
    user_text = messages[-1]["content"] if messages else ""

    # 1. تلاش از ویکی‌پدیا
    wiki = wiki_search(user_text.replace(" ", "_"))
    if wiki:
        return wiki

    # 2. پاسخ‌های ساده هوشمند
    if "سلام" in user_text:
        return "سلام 👋 خوش اومدی! چطور می‌تونم کمکت کنم؟"

    if "اسم" in user_text:
        return "من یک ربات هوش مصنوعی رایگان هستم 🤖"

    if "خداحافظ" in user_text:
        return "فعلاً 👋 هر وقت خواستی برگرد"

    # 3. fallback هوشمند
    return random.choice(FALLBACK_ANSWERS)
from flask import Flask
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import nest_asyncio
import asyncio
import threading
import os

# مفاتيح من Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# إعداد Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# إصلاح event loop
nest_asyncio.apply()

# Flask server
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 AI Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

# تخزين أسماء المستخدمين
user_names = {}

# بوت تلغرام
async def chat_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_message = update.message.text.strip()

    # لو المستخدم ما عندوش اسم، نسقسيه
    if user_id not in user_names:
        user_names[user_id] = None

    if user_names[user_id] is None:
        user_names[user_id] = user_message
        await update.message.reply_text(f"تشرفت بمعرفتك يا {user_message}! 🌟\nاكتبلي أي سؤال تحب.")
        return

    username = user_names[user_id]
    print(f"{username}: {user_message}")

    # ✅ نحفظ الرسالة فـ ملف
    try:
        with open("messages.txt", "a", encoding="utf-8") as f:
            f.write(f"{username}:\n  🧠 User: {user_message}\n")
    except Exception as e:
        print(f"⚠️ خطأ في حفظ الرسالة: {e}")

    # ✅ الرد من Gemini
    try:
        response = model.generate_content(user_message)
        bot_reply = response.text
    except Exception as e:
        bot_reply = f"⚠️ خطأ في الاتصال بالذكاء الاصطناعي: {e}"

    # نرد عليه
    await update.message.reply_text(bot_reply)

    # ✅ نحفظ الرد ديال البوت في نفس الملف
    try:
        with open("messages.txt", "a", encoding="utf-8") as f:
            f.write(f"  🤖 Bot: {bot_reply}\n\n")
    except Exception as e:
        print(f"⚠️ خطأ في حفظ رد البوت: {e}")

# إعداد تطبيق البوت
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_ai))

# تشغيل Flask server + البوت
threading.Thread(target=run_flask).start()

async def run_bot():
    await app.run_polling()

asyncio.run(run_bot())


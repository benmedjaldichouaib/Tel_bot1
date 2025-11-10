from flask import Flask
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import nest_asyncio
import asyncio
import threading
import os
import sqlite3

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

# ✅ route باش تشوف آخر الرسائل فالمتصفح
@web_app.route('/messages')
def show_messages():
    try:
        cursor.execute("SELECT username, message, bot_reply, timestamp FROM messages ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        content = ""
        for row in rows:
            content += f"<b>{row[0]}</b> ({row[3]}):<br>🧠 User: {row[1]}<br>🤖 Bot: {row[2]}<br><br>"
        return content if content else "⚠️ No messages yet."
    except Exception as e:
        return f"⚠️ Error reading database: {e}"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

# ===========================
# SQLite setup
# ===========================
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    bot_reply TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# ===========================
# Telegram Bot
# ===========================
user_names = {}

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

    # ✅ الرد من Gemini
    try:
        response = model.generate_content(user_message)
        bot_reply = response.text
    except Exception as e:
        bot_reply = f"⚠️ خطأ في الاتصال بالذكاء الاصطناعي: {e}"

    await update.message.reply_text(bot_reply)

    # ✅ حفظ الرسالة و الرد فـ SQLite
    try:
        cursor.execute("""
            INSERT INTO messages (user_id, username, message, bot_reply)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, user_message, bot_reply))
        conn.commit()
        print(f"💾 Message saved for {username}")
    except Exception as e:
        print(f"⚠️ خطأ في حفظ البيانات: {e}")

# إعداد تطبيق البوت
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_ai))

# تشغيل Flask server + البوت
threading.Thread(target=run_flask).start()

async def run_bot():
    await app.run_polling()

asyncio.run(run_bot())





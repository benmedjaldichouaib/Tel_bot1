from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import google.generativeai as genai
import os
import psycopg2
import nest_asyncio
import asyncio
import threading

# =======================
# Environment Variables
# =======================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATABASE_URL = os.environ.get("postgresql://bot_db_dbjz_user:iWzIodRLt4GaQJWVGt030LQM45817Pgi@dpg-d491rr95pdvs73cm68rg-a/bot_db_dbjz")  # PostgreSQL URL from Render

# =======================
# Gemini setup
# =======================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# =======================
# PostgreSQL setup
# =======================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    username TEXT,
    message TEXT,
    bot_reply TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# =======================
# Flask setup
# =======================
nest_asyncio.apply()
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 AI Bot is running!"

# =======================
# Telegram Bot
# =======================
user_names = {}

async def chat_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_message = update.message.text.strip()

    # سؤال الاسم إذا جديد
    if user_id not in user_names or user_names[user_id] is None:
        user_names[user_id] = user_message
        await update.message.reply_text(f"تشرفت بمعرفتك يا {user_message}! 🌟\nاكتبلي أي سؤال تحب.")
        return

    username = user_names[user_id]

    # ✅ الرد من Gemini
    try:
        response = model.generate_content(user_message)
        bot_reply = response.text
    except Exception as e:
        bot_reply = f"⚠️ خطأ في الاتصال بالذكاء الاصطناعي: {e}"

    await update.message.reply_text(bot_reply)

    # ✅ حفظ الرسالة و الرد فـ PostgreSQL
    try:
        cursor.execute("""
            INSERT INTO messages (user_id, username, message, bot_reply)
            VALUES (%s, %s, %s, %s)
        """, (user_id, username, user_message, bot_reply))
        conn.commit()
        print(f"💾 Message saved for {username}")
    except Exception as e:
        print(f"⚠️ خطأ في حفظ البيانات: {e}")

# =======================
# Telegram Webhook route
# =======================
@web_app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    asyncio.get_event_loop().create_task(app.process_update(update))
    return "ok", 200

# =======================
# Run Flask server
# =======================
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

# =======================
# Telegram application
# =======================
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_ai))

# =======================
# Start Flask + Bot
# =======================
threading.Thread(target=run_flask).start()

async def set_webhook():
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
    await app.bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")

asyncio.run(set_webhook())
asyncio.run(app.run_polling())
# Route باش تشوف آخر الرسائل فالويب
@web_app.route('/messages')
def show_messages():
    try:
        cursor.execute("SELECT username, message, bot_reply, timestamp FROM messages ORDER BY id DESC LIMIT 50")
        rows = cursor.fetchall()
        if not rows:
            return "⚠️ مازال ما كاين حتى رسالة."

        # نخلق HTML بسيط باش نعرض الرسائل
        content = "<h2>آخر الرسائل</h2><hr>"
        for row in rows:
            content += f"<b>{row[0]}</b> ({row[3]}):<br>🧠 User: {row[1]}<br>🤖 Bot: {row[2]}<br><br>"
        return content
    except Exception as e:
        return f"⚠️ خطأ فـ قراءة الـ database: {e}"




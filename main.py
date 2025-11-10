from flask import Flask, request, send_file, render_template_string
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import google.generativeai as genai
import os
import psycopg2
import nest_asyncio
import asyncio
import threading
import io
import csv

# =======================
# Environment Variables
# =======================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")  # PostgreSQL Internal URL

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

    # إذا المستخدم جديد أو الاسم مازال ما تعرفش
    if user_id not in user_names:
        user_names[user_id] = None

    if user_names[user_id] is None:
        await update.message.reply_text("مرحبا! 🌟 شنو سميتك؟")
        user_names[user_id] = "waiting_for_name"
        return

    if user_names[user_id] == "waiting_for_name":
        user_names[user_id] = user_message
        await update.message.reply_text(f"تشرفت بمعرفتك يا {user_message}! اكتبلي أي سؤال تحب.")
        return

    username = user_names[user_id]

    # الرد من Gemini
    try:
        response = model.generate_content(user_message)
        bot_reply = response.text
    except Exception as e:
        bot_reply = f"⚠️ خطأ في الاتصال بالذكاء الاصطناعي: {e}"

    await update.message.reply_text(bot_reply)

    # حفظ الرسالة و الرد فـ PostgreSQL
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

# =======================
# Route عرض جميع الرسائل + زر تحميل CSV
# =======================
@web_app.route('/messages')
def messages_page():
    try:
        cursor.execute("SELECT username, message, bot_reply, timestamp FROM messages ORDER BY id ASC")
        rows = cursor.fetchall()
        if not rows:
            return "⚠️ مازال ما كاين حتى رسالة."

        html_content = """
        <h2>📄 جميع الرسائل</h2>
        <a href="/export_csv"><button>⬇️ تحميل CSV</button></a>
        <hr>
        {% for row in rows %}
            <b>{{row[0]}}</b> ({{row[3]}}):<br>
            🧠 User: {{row[1]}}<br>
            🤖 Bot: {{row[2]}}<br><br>
        {% endfor %}
        """
        return render_template_string(html_content, rows=rows)

    except Exception as e:
        return f"⚠️ خطأ فـ قراءة الـ database: {e}"

# =======================
# Route لتصدير CSV
# =======================
@web_app.route('/export_csv')
def export_csv():
    try:
        cursor.execute("SELECT username, message, bot_reply, timestamp FROM messages ORDER BY id ASC")
        rows = cursor.fetchall()
        if not rows:
            return "⚠️ مازال ما كاين حتى رسالة."

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Username", "User Message", "Bot Reply", "Timestamp"])
        for row in rows:
            writer.writerow(row)

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8")),
            mimetype='text/csv',
            as_attachment=True,
            download_name='all_messages.csv'
        )
    except Exception as e:
        return f"⚠️ خطأ فـ تصدير CSV: {e}"






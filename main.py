from flask import Flask, request
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
import os
import nest_asyncio
import asyncio

# مفاتيح من Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# إعداد Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# Flask app
web_app = Flask(__name__)

# Telegram application
app = Application.builder().token(BOT_TOKEN).build()

# دالة الرد من Gemini
async def chat_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    print(f"User: {user_message}")

    try:
        response = model.generate_content(user_message)
        bot_reply = response.text
    except Exception as e:
        bot_reply = f"⚠️ خطأ في الاتصال بالذكاء الاصطناعي: {e}"

    await update.message.reply_text(bot_reply)

# إضافة الهاندلر
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_ai))

# المسارات في Flask
@web_app.route('/')
def home():
    return "🤖 AI Bot is running with Webhook!", 200

@web_app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    asyncio.get_event_loop().create_task(app.process_update(update))
    return "ok", 200

async def set_webhook():
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
    await app.bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")

async def main():
    # تعيين الـWebhook
    await set_webhook()
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())


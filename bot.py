import os
import logging
import asyncio
from threading import Thread
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import aiohttp

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "<h2>✅ Bot is Running Successfully</h2>"

# Webhook معالجة متزامنة (مهم جداً)
@flask_app.route('/webhook', methods=['POST'])
def webhook():
    global application
    try:
        update_dict = request.get_json(force=True)
        update = Update.de_json(update_dict, application.bot)
        # تشغيل الـ update بشكل غير متزامن
        asyncio.create_task(application.process_update(update))
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook Error: {e}")
        return "ERROR", 500


async def ask_gemini(text: str):
    if not GEMINI_API_KEY:
        return "⚠️ الذكاء الاصطناعي غير مفعل.\nتواصل معنا: +967775012242"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "contents": [{"parts": [{"text": text}]}],
                "generationConfig": {"temperature": 0.75, "maxOutputTokens": 1000}
            }, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    return "الخدمة مزدحمة، يرجى الاتصال على +967775012242"
    except:
        return "حدث خطأ، يرجى التواصل على +967775012242"


def get_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛂 تأشيرات العمل", callback_data="visa")],
        [InlineKeyboardButton("✈️ حجوزات طيران", callback_data="flights")],
        [InlineKeyboardButton("📞 اتصل بنا", callback_data="contact")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً وسهلاً بك في مكتب أبو مجد الحداد\nكيف يمكنني خدمتك؟", reply_markup=get_keyboard())

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    response = await ask_gemini(update.message.text)
    await update.message.reply_text(response, reply_markup=get_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ تم الاختيار\nأرسل التفاصيل المطلوبة...", reply_markup=get_keyboard())


application = None

async def main():
    global application
    if not TOKEN:
        logger.error("TOKEN مفقود!")
        return

    application = Application.builder().token(TOKEN).updater(None).build()

    await application.bot.delete_webhook(drop_pending_updates=True)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    application.add_handler(CallbackQueryHandler(button_handler))

    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        await application.bot.set_webhook(f"{render_url}/webhook")
        logger.info(f"Webhook set: {render_url}/webhook")

    await application.initialize()
    await application.start()
    logger.info("✅ Bot Started Successfully!")


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())

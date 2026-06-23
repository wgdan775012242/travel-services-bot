import os
import logging
from threading import Thread
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import aiohttp
import asyncio
import time

# ====================== Logging ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")

# ====================== Flask ======================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "<h2>✅ البوت يعمل الآن</h2><p>مكتب أبو مجد الحداد</p>"

@flask_app.route('/webhook', methods=['POST'])
async def webhook():
    if not application:
        logger.error("Application not initialized")
        return "Not ready", 503
    
    try:
        update_dict = request.get_json(force=True)
        update = Update.de_json(update_dict, application.bot)
        await application.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook Error: {e}")
        return "ERROR", 500


# ====================== Gemini ======================
async def ask_gemini(user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ الذكاء الاصطناعي غير مفعل حالياً."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
أنت مساعد مكتب أبو مجد الحداد للسفريات.
معلومات: هاتف +967775012242
أجب بلباقة واحترافية على الرسالة التالية:

الرسالة: {user_message}
"""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000}
            }, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    return "عذراً، الخدمة مزدحمة. يرجى الاتصال على +967775012242"
    except:
        return "حدث خطأ. يرجى التواصل على +967775012242"


# ====================== Keyboards & Handlers ======================
def get_main_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("🛂 تأشيرات العمل", callback_data="visa")],
        [InlineKeyboardButton("✈️ حجوزات طيران", callback_data="flights")],
        [InlineKeyboardButton("📞 اتصل بنا", callback_data="contact")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً وسهلاً بك في مكتب أبو مجد الحداد\n\nكيف يمكنني خدمتك؟",
        reply_markup=get_main_keyboard()
    )


async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    text = update.message.text.strip()
    
    if len(text) < 3:
        await update.message.reply_text("أرسل استفسارك بالتفصيل...")
        return
    
    response = await ask_gemini(text)
    await update.message.reply_text(response, reply_markup=get_main_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "visa":
        text = "🛂 أرسل:\n- الاسم الكامل\n- رقم الجواز\n- المهنة"
    elif query.data == "flights":
        text = "✈️ أرسل تفاصيل الحجز (المدينة - الوجهة - التاريخ)"
    elif query.data == "contact":
        text = "📞 +967775012242"
    else:
        text = "اختر من القائمة"
    
    await query.edit_message_text(text=text, reply_markup=get_main_keyboard())


# ====================== Main ======================
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
        webhook_url = f"{render_url.rstrip('/')}/webhook"
        await application.bot.set_webhook(webhook_url, allowed_updates=Update.ALL_TYPES)
        logger.info(f"✅ Webhook set to: {webhook_url}")
    else:
        logger.warning("No RENDER_EXTERNAL_URL found")

    await application.initialize()
    await application.start()
    logger.info("🚀 Bot started successfully!")


# ====================== Run ======================
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    
    try:
        asyncio.run(main())
        while True:
            time.sleep(3600)
    except Exception as e:
        logger.error(f"Critical Error: {e}")

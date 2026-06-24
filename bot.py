import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import aiohttp
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# ====================== Flask ======================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Bot is running successfully! | مكتب أبو مجد الحداد"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

# ====================== Gemini ======================
async def ask_gemini(user_message: str) -> str:
    if not API_KEY:
        logger.error("❌ API_KEY مفقود في Environment Variables!")
        return "⚠️ الذكاء الاصطناعي غير مفعل.\nيرجى التواصل على: +967775012242"

    logger.info(f"✅ API_KEY موجود | طوله = {len(API_KEY)} حرف")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

    prompt = f"""
أنت مساعد مكتب أبو مجد الحداد للسفريات.
معلومات: +967775012242
أجب بلباقة واحترافية.

الرسالة: {user_message}
"""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.75, "maxOutputTokens": 1000}
            }, timeout=35) as resp:
                
                if resp.status == 200:
                    data = await resp.json()
                    return data['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    return "عذراً، الخدمة مزدحمة حالياً."
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return "حدث خطأ في الاتصال بالذكاء الاصطناعي.\nيرجى التواصل على +967775012242"


def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛂 تأشيرات العمل", callback_data="visa")],
        [InlineKeyboardButton("✈️ حجوزات طيران", callback_data="flights")],
        [InlineKeyboardButton("📞 اتصل بنا", callback_data="contact")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً وسهلاً بك في مكتب أبو مجد الحداد\n\nكيف يمكنني خدمتك اليوم؟",
        reply_markup=get_main_keyboard()
    )


async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    response = await ask_gemini(update.message.text)
    await update.message.reply_text(response, reply_markup=get_main_keyboard())


# ====================== Run ======================
if __name__ == '__main__':
    if not TOKEN:
        logger.error("❌ TOKEN مفقود!")
    else:
        logger.info("✅ TOKEN موجود")

    if not API_KEY:
        logger.error("❌ API_KEY مفقود!")
    else:
        logger.info(f"✅ API_KEY موجود | طوله = {len(API_KEY)}")

    Thread(target=run_flask, daemon=True).start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))

    logger.info("🚀 Bot is running with Polling...")
    application.run_polling(drop_pending_updates=True)

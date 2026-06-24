import os
import json
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import aiohttp
import asyncio

# ====================== Logging ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== Environment Variables ======================
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# ====================== Flask (لـ Render) ======================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Bot is running successfully! | مكتب أبو مجد الحداد"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

# ====================== Office Info & System Prompt ======================
OFFICE_INFO = """
مكتب أبو مجد الحداد للسفريات والتأشيرات:
- الهاتف: +967775012242
- التخصص: تأشيرات عمل يمن → سعودية، حجوزات طيران، خدمات سياحية.
"""

SYSTEM_PROMPT = f"""
{OFFICE_INFO}
أنت مساعد متخصص ومحترف لمكتب أبو مجد الحداد.
أجب بلباقة واحترافية، وركز فقط على خدمات السفر والتأشيرات.
إذا كان السؤال خارج النطاق، اعتذر واقترح التواصل المباشر.
استخدم إيموجي بشكل مناسب.
"""

# ====================== Gemini AI (محسن) ======================
async def ask_gemini(user_message: str) -> str:
    if not API_KEY:
        return "⚠️ الذكاء الاصطناعي غير مفعل حالياً.\nيرجى التواصل على: +967775012242"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

    full_prompt = f"{SYSTEM_PROMPT}\n\nرسالة العميل: {user_message}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {"temperature": 0.75, "maxOutputTokens": 1200}
            }, timeout=35) as resp:
                
                if resp.status == 200:
                    data = await resp.json()
                    return data['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    logger.error(f"Gemini Status: {resp.status}")
                    return "عذراً، الخدمة مزدحمة حالياً.\nيرجى التواصل على +967775012242"
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return "حدث خطأ في الاتصال بالذكاء الاصطناعي.\nيرجى التواصل مباشرة على: +967775012242"


# ====================== Keyboard ======================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛂 تأشيرات العمل", callback_data="visa")],
        [InlineKeyboardButton("✈️ حجوزات طيران", callback_data="flights")],
        [InlineKeyboardButton("📞 اتصل بنا", callback_data="contact")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ====================== Handlers ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً وسهلاً بك في مكتب أبو مجد الحداد\n\n"
        "كيف يمكنني خدمتك اليوم؟",
        reply_markup=get_main_keyboard()
    )


async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    user_text = update.message.text.strip()
    response = await ask_gemini(user_text)
    
    try:
        await update.message.reply_text(response, reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Reply Error: {e}")
        await update.message.reply_text("عذراً، حدث خطأ أثناء معالجة طلبك.")


# ====================== Main ======================
if __name__ == '__main__':
    if not TOKEN:
        logger.error("❌ TOKEN مفقود في Environment Variables!")
        exit(1)
    
    if not API_KEY:
        logger.warning("⚠️ API_KEY (Gemini) غير موجود - سيتم استخدام ردود محدودة")

    # تشغيل Flask في الخلفية
    Thread(target=run_flask, daemon=True).start()

    # تشغيل البوت
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))

    logger.info("🚀 Bot started successfully with Gemini AI!")
    application.run_polling(drop_pending_updates=True)

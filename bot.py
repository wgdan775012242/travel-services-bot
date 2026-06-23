import os
import json
import asyncio
import logging
from threading import Thread
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import aiohttp
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
    return """
    <h2>✅ البوت يعمل بنجاح 24/7</h2>
    <p><strong>مكتب أبو مجد الحداد للسفريات والتأشيرات</strong></p>
    <p>الرابط: https://travel-services-bot.onrender.com</p>
    <small>تم تحديث الذكاء الاصطناعي بنجاح • Gemini 1.5 Flash</small>
    """

# ====================== Gemini AI (محسن) ======================
async def ask_gemini(user_message: str, max_retries: int = 4) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ لم يتم إعداد مفتاح API. يرجى التواصل مع الإدارة."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    OFFICE_INFO = """
مكتب أبو مجد الحداد للسفريات والتأشيرات:
- الهاتف: +967775012242
- البريد: what775012242@outlook.sa
- التخصص: تأشيرات عمل (يمن → سعودية)، حجوزات طيران، خدمات سياحية، تأشيرات زيارة وعمرة.
"""

    SYSTEM_PROMPT = f"""
{OFFICE_INFO}
أنت مساعد ذكي واحترافي جداً لمكتب أبو مجد الحداد.
- أجب بلباقة واحترام وود.
- ركز على خدماتنا فقط.
- إذا كان السؤال خارج نطاق الخدمات، اعتذر واقترح التواصل المباشر.
- استخدم إيموجي بشكل مناسب لتحسين التجربة.
"""

    full_prompt = f"{SYSTEM_PROMPT}\n\nالعميل: {user_message}"

    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1200,
            "topP": 0.95
        }
    }

    async with aiohttp.ClientSession() as session:
        for attempt in range(max_retries):
            try:
                async with session.post(url, json=data, timeout=40) as response:
                    if response.status == 429:
                        await asyncio.sleep(2 ** attempt * 3)
                        continue
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"Gemini Error {response.status}: {text}")
                        if attempt == max_retries - 1:
                            return "عذراً، الخدمة مزدحمة حالياً.\n\nيرجى التواصل مباشرة على: +967775012242"
                        continue

                    result = await response.json()
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()

            except asyncio.TimeoutError:
                logger.warning(f"Gemini Timeout - Attempt {attempt+1}")
            except Exception as e:
                logger.error(f"Gemini Error: {e}")
                if attempt == max_retries - 1:
                    return "حدث خطأ في الاتصال بالذكاء الاصطناعي.\n\nالرجاء المحاولة لاحقاً أو التواصل على: +967775012242"

    return "عذراً، لا أستطيع الرد حالياً. يرجى الاتصال على +967775012242"


# ====================== Keyboards ======================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛂 تأشيرات العمل", callback_data="visa")],
        [InlineKeyboardButton("✈️ حجوزات الطيران", callback_data="flights")],
        [InlineKeyboardButton("🕋 خدمات الحج والعمرة", callback_data="umrah")],
        [InlineKeyboardButton("📞 اتصل بنا", callback_data="contact")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ====================== Handlers ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *أهلاً وسهلاً بك في مكتب أبو مجد الحداد*\n\n"
        "نقدم لك خدمات التأشيرات والسفر بكل احترافية.\n"
        "كيف يمكنني خدمتك اليوم؟",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )


async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    user_message = update.message.text.strip()
    response = await ask_gemini(user_message)
    
    try:
        await update.message.reply_text(response, reply_markup=get_main_keyboard(), parse_mode='Markdown')
    except:
        await update.message.reply_text(response, reply_markup=get_main_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    texts = {
        "visa": "🛂 *تأشيرات العمل*\n\nأرسل لي التفاصيل التالية:\n• الاسم الكامل\n• رقم الجواز\n• المهنة\n• الجنسية",
        "flights": "✈️ *حجوزات الطيران*\n\nأخبرني بـ:\n• مدينة المغادرة\n• الوجهة\n• التاريخ المقترح\n• عدد المسافرين",
        "umrah": "🕋 *خدمات الحج والعمرة*\n\nنقدم باقات متكاملة (تأشيرة + سكن + نقل).\nأرسل لي استفسارك.",
        "contact": "📞 *التواصل المباشر*\n\n• الهاتف: +967775012242\n• الواتساب: +967775012242",
    }

    text = texts.get(query.data, "اختر من القائمة 👇")
    await query.edit_message_text(text=text, reply_markup=get_main_keyboard(), parse_mode='Markdown')


# ====================== Webhook ======================
application = None

@flask_app.route('/webhook', methods=['POST'])
async def webhook():
    global application
    if not application:
        return "Not ready", 503
    try:
        update_dict = request.get_json(force=True)
        update = Update.de_json(update_dict, application.bot)
        await application.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook Error: {e}")
        return "ERROR", 500


# ====================== Main ======================
async def main():
    global application
    if not TOKEN or not GEMINI_API_KEY:
        logger.error("❌ TOKEN أو GEMINI_API_KEY مفقود في المتغيرات البيئية!")
        return

    application = Application.builder().token(TOKEN).updater(None).build()

    await application.bot.delete_webhook(drop_pending_updates=True)

    # إضافة الـ Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    application.add_handler(CallbackQueryHandler(button_handler))

    # إعداد Webhook على Render
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        webhook_url = f"{render_url.rstrip('/')}/webhook"
        await application.bot.set_webhook(webhook_url, allowed_updates=Update.ALL_TYPES)
        logger.info(f"✅ Webhook set successfully: {webhook_url}")

    await application.initialize()
    await application.start()
    logger.info("🚀 Bot started successfully with improved Gemini integration!")


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    
    try:
        asyncio.run(main())
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")

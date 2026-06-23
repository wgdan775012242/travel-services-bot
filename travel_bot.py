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

# ====================== Flask App ======================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return """
    <h2>✅ البوت يعمل بنجاح 24/7</h2>
    <p><strong>مكتب أبو مجد الحداد للسفريات والتأشيرات</strong></p>
    <p>تم تطوير البوت بذكاء اصطناعي متقدم</p>
    """

# ====================== Local Quick Responses ======================
LOCAL_RESPONSES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته 👋\nكيف يمكنني خدمتك اليوم؟",
    "مرحبا": "مرحبا بك! 👋 كيف أقدر أساعدك في خدمات السفر والتأشيرات؟",
    "كم سعر التأشيرة": "🛂 أسعار التأشيرات تختلف حسب المهنة والمدة.\nأرسل لي المهنة + الجنسية لأعطيك السعر الدقيق.",
    "شكرا": "عفواً، في خدمتك دائماً ❤️",
    "تحياتي": "تحياتي لك! 😊",
    "ايش خدماتكم": "نقدم:\n• تأشيرات عمل يمن → سعودية\n• حجوزات طيران\n• تأشيرات زيارة وعمرة\n• خدمات سياحية",
}

# ====================== Gemini AI ======================
async def ask_gemini(user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ خدمة الذكاء الاصطناعي غير متوفرة حالياً."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    system_prompt = """
أنت مساعد متخصص ومحترف جداً لمكتب أبو مجد الحداد للسفريات والتأشيرات في اليمن.
معلومات المكتب:
- الهاتف / الواتساب: +967775012242
- البريد: what775012242@outlook.sa
- التخصص: تأشيرات عمل (يمن-سعودية)، حجوزات طيران، تأشيرات زيارة، عمرة وحج، خدمات سياحية.

قواعد الرد:
- كن لبقاً، محترماً وودوداً.
- استخدم إيموجي بشكل مناسب.
- إذا كان السؤال عن أسعار أو إجراءات، اطلب التفاصيل المطلوبة.
- إذا كان خارج الخدمات، اقترح التواصل المباشر.
"""

    data = {
        "contents": [{"parts": [{"text": f"{system_prompt}\n\nالعميل: {user_message}"}]}],
        "generationConfig": {
            "temperature": 0.75,
            "maxOutputTokens": 1200,
            "topP": 0.95
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=35) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    logger.error(f"Gemini Status: {resp.status}")
                    return "عذراً، الخدمة مزدحمة حالياً. يرجى التواصل على +967775012242"
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return "حدث خطأ في الاتصال بالذكاء الاصطناعي.\nالرجاء المحاولة مرة أخرى أو الاتصال على: +967775012242"


# ====================== Keyboards ======================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛂 تأشيرات العمل", callback_data="visa")],
        [InlineKeyboardButton("✈️ حجوزات طيران", callback_data="flights")],
        [InlineKeyboardButton("🕋 حج وعمرة", callback_data="umrah")],
        [InlineKeyboardButton("📞 اتصل بنا", callback_data="contact")],
        [InlineKeyboardButton("❓ أسئلة شائعة", callback_data="faq")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ====================== Handlers ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *أهلاً وسهلاً بك في مكتب أبو مجد الحداد*\n\n"
        "نقدم خدمات التأشيرات والسفر باحترافية عالية.\n"
        "اختر الخدمة أو اكتب استفسارك:",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )


async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    text = update.message.text.strip()
    
    # ردود محلية سريعة
    lower_text = text.lower()
    for key in LOCAL_RESPONSES:
        if key in lower_text or lower_text in key:
            response = LOCAL_RESPONSES[key]
            await update.message.reply_text(response, reply_markup=get_main_keyboard())
            return

    # استخدام Gemini للباقي
    response = await ask_gemini(text)
    try:
        await update.message.reply_text(response, reply_markup=get_main_keyboard(), parse_mode='Markdown')
    except:
        await update.message.reply_text(response, reply_markup=get_main_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    responses = {
        "visa": "🛂 *تأشيرات العمل*\n\nللحصول على عرض سعر، أرسل:\n• الاسم الكامل\n• رقم الجواز\n• المهنة\n• الجنسية",
        "flights": "✈️ *حجوزات الطيران*\n\nأرسل التفاصيل:\n• مدينة المغادرة\n• الوجهة\n• التاريخ\n• عدد المسافرين",
        "umrah": "🕋 *خدمات الحج والعمرة*\n\nنقدم باقات متكاملة (تأشيرة + سكن + نقل).\nأخبرني بتفاصيل طلبك.",
        "contact": "📞 *التواصل المباشر*\n\n• واتساب / هاتف: +967775012242",
        "faq": "❓ *أسئلة شائعة*\n\n• اكتب 'كم سعر التأشيرة' أو 'شروط التأشيرة'\n• أو اكتب استفسارك مباشرة"
    }

    text = responses.get(query.data, "اختر من القائمة 👇")
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


# ====================== Main Function ======================
async def main():
    global application
    if not TOKEN:
        logger.error("TOKEN مفقود!")
        return
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY غير موجود - سيتم الاعتماد على الردود المحلية فقط")

    application = Application.builder().token(TOKEN).updater(None).build()

    await application.bot.delete_webhook(drop_pending_updates=True)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    application.add_handler(CallbackQueryHandler(button_handler))

    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        webhook_url = f"{render_url.rstrip('/')}/webhook"
        await application.bot.set_webhook(webhook_url)
        logger.info(f"Webhook set: {webhook_url}")

    await application.initialize()
    await application.start()
    logger.info("✅ Bot is running successfully with Hybrid AI System!")


# ====================== Run Flask ======================
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    debug_mode = os.environ.get("RENDER_EXTERNAL_URL") is None  # True فقط محلياً
    flask_app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=False)


if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    
    try:
        asyncio.run(main())
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Critical error: {e}")

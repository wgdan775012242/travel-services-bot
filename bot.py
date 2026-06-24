import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import aiohttp

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# ====================== Flask ======================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Bot is running | مكتب أبو مجد الحداد"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

# ====================== ردود محلية سريعة ======================
LOCAL_RESPONSES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته 👋\nكيف يمكنني خدمتك اليوم؟",
    "مرحبا": "مرحبا بك! 👋 كيف أقدر أساعدك في خدمات السفر؟",
    "كم سعر التأشيرة": "🛂 أسعار التأشيرات تختلف حسب المهنة والجنسية.\nأرسل لي المهنة + الجنسية لأعطيك السعر التقريبي.",
    "شروط التأشيرة": "🛂 أهم الشروط:\n• جواز سفر ساري الصلاحية\n• صور شخصية\n• عقد عمل\n• شهادة عدم محكومية\n\nأرسل تفاصيلك لأفحصها لك.",
    "شكرا": "عفواً، في خدمتك دائماً ❤️",
    "تحياتي": "تحياتي لك! 😊",
    "ايش خدماتكم": "نقدم خدمات:\n• تأشيرات عمل يمن → سعودية\n• حجوزات طيران\n• تأشيرات زيارة وعمرة\n• خدمات سياحية",
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"


# ====================== Gemini AI ======================
async def ask_gemini(user_message: str) -> str:
    if not API_KEY:
        return "⚠️ الذكاء الاصطناعي غير مفعل.\nيرجى التواصل على: +967775012242"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

    prompt = f"""
أنت مساعد مكتب أبو مجد الحداد للسفريات والتأشيرات.
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
    except:
        pass
    return "عذراً، الخدمة مزدحمة حالياً.\nيرجى الاتصال على +967775012242"


# ====================== Keyboard ======================
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
        "👋 أهلاً وسهلاً بك في مكتب أبو مجد الحداد\n\n"
        "كيف يمكنني خدمتك اليوم؟",
        reply_markup=get_main_keyboard()
    )


async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    
    text = update.message.text.strip()
    
    # التحقق من الردود المحلية أولاً
    for key in LOCAL_RESPONSES:
        if key in text or text in key:
            await update.message.reply_text(LOCAL_RESPONSES[key], reply_markup=get_main_keyboard())
            return

    # إذا لم يجد رد محلي → يستخدم Gemini
    response = await ask_gemini(text)
    await update.message.reply_text(response, reply_markup=get_main_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    responses = {
        "visa": "🛂 لتأشيرة العمل أرسل:\n• الاسم الكامل\n• رقم الجواز\n• المهنة\n• الجنسية",
        "flights": "✈️ أرسل تفاصيل الحجز:\n• مدينة المغادرة\n• الوجهة\n• التاريخ المطلوب",
        "umrah": "🕋 خدمات الحج والعمرة متوفرة\nأرسل عدد الأشخاص والتاريخ المقترح",
        "contact": "📞 التواصل المباشر:\n+967775012242",
        "faq": "❓ أكتب أي سؤال مثل:\n- كم سعر التأشيرة\n- شروط التأشيرة\n- ايش خدماتكم"
    }

    text = responses.get(query.data, "اختر من القائمة 👇")
    await query.edit_message_text(text=text, reply_markup=get_main_keyboard())


# ====================== Main ======================
if __name__ == '__main__':
    if not TOKEN:
        logger.error("TOKEN مفقود!")
    if not API_KEY:
        logger.warning("API_KEY مفقود - Gemini غير مفعل")

    Thread(target=run_flask, daemon=True).start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    application.add_handler(CallbackQueryHandler(button_handler))   # ← مهم

    logger.info("🚀 Bot Started Successfully with Local Responses + Gemini")
    application.run_polling(drop_pending_updates=True)

import nest_asyncio
nest_asyncio.apply()
import os
import logging
import asyncio
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# التكوين الأساسي للتسجيل (Logging)
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# جلب مفاتيح البيئة
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# إعداد تطبيق Flask
flask_app = Flask(__name__)

# إعداد الـ المتغير العالمي للبوت
application = None

# إعداد ذكاء Gemini الاصطناعي
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-pro")
else:
    logger.warning("GEMINI_API_KEY environment variable not set. AI responses will be disabled.")
    model = None

# الردود المحلية التلقائية لخدمات السفر
LOCAL_RESPONSES = {
    "مرحبا": "أهلاً بك! كيف يمكنني مساعدتك في خدمات السفر؟",
    "أهلاً": "أهلاً بك! كيف يمكنني مساعدتك في خدمات السفر؟",
    "خدماتكم": "نقدم خدمات شاملة تشمل: التأشيرات، حج وعمرة، تذاكر طيران، حجز فنادق، باقات سياحية، جوازات، وخدمات توظيف. ما الذي تبحث عنه بالتحديد؟",
    "تأشيرات": "نقدم خدمات استخراج التأشيرات لمختلف الدول. يرجى تزويدنا بالدولة التي ترغب بالسفر إليها لنقدم لك التفاصيل.",
    "فيزا": "نقدم خدمات استخراج التأشيرات لمختلف الدول. يرجى تزويدنا بالدولة التي ترغب بالسفر إليها لنقدم لك التفاصيل.",
    "حج وعمرة": "لدينا باقات مميزة للحج والعمرة. هل ترغب بمعرفة المزيد عن باقات العمرة أو الحج؟",
    "تذاكر طيران": "يمكننا مساعدتك في حجز تذاكر الطيران لأي وجهة. يرجى تزويدنا بمدينة المغادرة والوصول وتواريخ السفر المفضلة.",
    "حجز فنادق": "نساعدك في حجز أفضل الفنادق حول العالم. ما هي وجهتك المفضلة ومدة الإقامة؟",
    "باقات سياحية": "لدينا مجموعة واسعة من الباقات السياحية التي تناسب جميع الأذواق والميزانيات. هل لديك وجهة معينة في ذهنك؟",
    "جوازات": "نقدم خدمات تجديد واستخراج الجوازات. يرجى التواصل معنا لمزيد من التفاصيل حول المتطلبات.",
    "خدمات توظيف": "نساعد في توفير فرص عمل في قطاع السفر والسياحة. يرجى إرسال سيرتك الذاتية إلينا.",
    "شكرا": "على الرحب والسعة! يسعدنا خدمتك.",
    "مع السلامة": "مع السلامة! نتمنى لك رحلة سعيدة."
}

async def start(update: Update, context) -> None:
    """Sends a message when the command /start is issued."""
    if update.message:
        user = update.effective_user
        await update.message.reply_html(
            f"مرحباً {user.mention_html()}! أنا بوت خدمات السفر الخاص بك. كيف يمكنني مساعدتك اليوم؟",
        )

async def help_command(update: Update, context) -> None:
    """Sends a message when the command /help is issued."""
    if update.message:
        await update.message.reply_text("يمكنني مساعدتك في البحث عن خدمات السفر. فقط اسألني عن التأشيرات، تذاكر الطيران، الحج والعمرة، أو أي خدمة أخرى!")

async def ai_response(update: Update, context) -> None:
    """Generates an AI response using Google Gemini."""
    if model and update.message and update.message.text:
        try:
            response = model.generate_content(update.message.text)
            await update.message.reply_text(response.text)
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            await update.message.reply_text("عذراً، حدث خطأ أثناء محاولة توليد الرد. يرجى المحاولة مرة أخرى لاحقاً.")
    else:
        if update.message:
            await update.message.reply_text("عذراً، وظيفة الذكاء الاصطناعي غير متاحة حالياً.")

async def handle_message(update: Update, context) -> None:
    """Handles all incoming messages, prioritizing local responses then AI."""
    if not update.message or not update.message.text:
        return
        
    user_message = update.message.text.lower()

    # التحقق من الردود المحلية أولاً
    for keyword, response_text in LOCAL_RESPONSES.items():
        if keyword in user_message:
            await update.message.reply_text(response_text)
            return

    # إذا لم يطابق أي رد محلي، يتم التوجه للذكاء الاصطناعي
    await ai_response(update, context)


# =====================================================================
# إدارة حلقة الأحداث (Event Loop) بالخلفية بشكل آمن 100%
# =====================================================================

bot_loop = asyncio.new_event_loop()

async def init_bot_inside_loop():
    """بناء وتشغيل البوت بالكامل من داخل الحلقة المخصصة لمنع تضارب الـ Locks"""
    global application
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        return
        
    # البناء يتم هنا داخلياً لربط كل أدوات الاتصال بـ bot_loop
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # إضافة الـ Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تهيئة وبدء تشغيل البوت
    await application.initialize()
    await application.start()
    logger.info("Telegram Application built and initialized successfully inside background loop.")

def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    # تشغيل دالة التهيئة أولاً داخل الحلقة
    loop.run_until_complete(init_bot_inside_loop())
    # جعل الحلقة تعمل بشكل دائم لاستقبال رسائل الـ Webhook
    loop.run_forever()

# إطلاق خيط الخلفية عند تشغيل الملف
loop_thread = threading.Thread(target=start_background_loop, args=(bot_loop,), daemon=True)
loop_thread.start()


@flask_app.route("/")
def index():
    return "Bot is running perfectly!"

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    """مستقبل الـ Webhook (دالة متزامنة متوافقة تماماً مع سيرفر Flask و Render)"""
    if application is None:
        return "Application not initialized", 503
        
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)
        
        # تمرير التحديث ليعالج بأمان داخل حلقة البوت وبدون أي تداخل مع سيرفرات الويب
        asyncio.run_coroutine_threadsafe(application.process_update(update), bot_loop)
        return "ok", 200
    except Exception as e:
        logger.error(f"Error processing update in webhook: {e}")
        return "error", 500

if __name__ == "__main__":
    # تشغيل محلي (في حال رغبت بالتجربة المحلية)
    flask_app.run(port=5000)


import nest_asyncio
nest_asyncio.apply()
import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token and AI API Key from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Flask app setup
flask_app = Flask(__name__)

# Telegram Bot Application setup
application = None

# Configure Google Gemini
if GEMINI_API_KEY:
    genai.configure("api_key=GEMINI_API_KEY")
    model = genai.GenerativeModel("google-generativeai>=0.8.3
")
    
else:
    logger.warning("GEMINI_API_KEY environment variable not set. AI responses will be disabled.")
    model = None

# Expanded local responses for travel services
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
    user = update.effective_user
    await update.message.reply_html(
        f"مرحباً {user.mention_html()}! أنا بوت خدمات السفر الخاص بك. كيف يمكنني مساعدتك اليوم؟",
    )

async def help_command(update: Update, context) -> None:
    """Sends a message when the command /help is issued."""
    await update.message.reply_text("يمكنني مساعدتك في البحث عن خدمات السفر. فقط اسألني عن التأشيرات، تذاكر الطيران، الحج والعمرة، أو أي خدمة أخرى!")

async def ai_response(update: Update, context) -> None:
    """Generates an AI response using Google Gemini."""
    if model:
        try:
            response = model.generate_content(update.message.text)
            await update.message.reply_text(response.text)
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            await update.message.reply_text("عذراً، حدث خطأ أثناء محاولة توليد الرد. يرجى المحاولة مرة أخرى لاحقاً.")
    else:
        await update.message.reply_text("عذراً، وظيفة الذكاء الاصطناعي غير متاحة حالياً.")

async def handle_message(update: Update, context) -> None:
    """Handles all incoming messages, prioritizing local responses then AI."""
    user_message = update.message.text.lower()

    # Check for local responses first
    for keyword, response_text in LOCAL_RESPONSES.items():
        if keyword in user_message:
            await update.message.reply_text(response_text)
            return

    # Fallback to AI response if no local response matches
    await ai_response(update, context)

def setup_application():
    """Initializes the Telegram application."""
    global application
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        return None
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run initialization in the background loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(app.initialize())
    
    return app

# Initialize application once when the module is loaded
if application is None:
    application = setup_application()

@flask_app.route("/")
def index():
    return "Bot is running!"

@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    """Webhook endpoint for Telegram updates."""
    if application is None:
        return "Application not initialized", 503
        
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), application.bot)
            # Use the running loop to process update
            loop = asyncio.get_event_loop()
            loop.run_until_complete(application.process_update(update))
            return "ok"
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            return "error", 500
    return ""

if __name__ == "__main__":
    # For local testing
    if application:
        application.run_polling()

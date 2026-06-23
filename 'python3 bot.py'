import os
import logging
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
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    logger.warning("GEMINI_API_KEY environment variable not set. AI responses will be disabled.")
    model = None

async def start(update: Update, context) -> None:
    """Sends a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"مرحباً {user.mention_html()}! أنا بوت خدمات السفر الخاص بك. كيف يمكنني مساعدتك اليوم؟",
    )

async def help_command(update: Update, context) -> None:
    """Sends a message when the command /help is issued."""
    await update.message.reply_text("يمكنني مساعدتك في البحث عن خدمات السفر. فقط اسألني!")

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
    user_message = update.message.text

    # Simple local responses (can be expanded with a dictionary or database)
    if "مرحبا" in user_message.lower() or "أهلاً" in user_message.lower():
        await update.message.reply_text("أهلاً بك! كيف يمكنني مساعدتك في خدمات السفر؟")
    elif "خدماتكم" in user_message.lower():
        await update.message.reply_text("نقدم خدمات تأشيرات، حج وعمرة، تذاكر طيران، جوازات، وخدمات توظيف.")
    elif "شكرا" in user_message.lower():
        await update.message.reply_text("على الرحب والسعة!")
    else:
        # Fallback to AI response if no local response matches
        await ai_response(update, context)

@flask_app.route("/")
def index():
    return "Bot is running!"

@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    """Webhook endpoint for Telegram updates."""
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return "ok"
    return ""

def main() -> None:
    """Start the bot."""
    global application
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        exit(1)

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram bot application initialized.")

if __name__ == '__main__':
    main()

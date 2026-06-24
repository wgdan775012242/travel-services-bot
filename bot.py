import os
import logging
import threading
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Optional Gemini (Google) generative AI
try:
    import google.generativeai as genai
except Exception:
    genai = None

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger('bot')

# Environment
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') or os.environ.get('TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('API_KEY')
PORT = int(os.environ.get('PORT', 8080))

if not TOKEN:
    logger.error('TELEGRAM_BOT_TOKEN (or TOKEN) is not set. Exiting.')
    raise SystemExit('Missing TELEGRAM_BOT_TOKEN')

# Configure Gemini if available
model = None
if genai and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info('Configured Gemini generative model')
    except Exception:
        logger.exception('Failed to configure Gemini')
else:
    if not genai:
        logger.warning('google-generativeai package not available; AI responses will be disabled')
    if not GEMINI_API_KEY:
        logger.warning('GEMINI_API_KEY (or API_KEY) is not set; AI responses will be disabled')

# Build the telegram application
application = ApplicationBuilder().token(TOKEN).build()

# Handlers
async def start(update: Update, context):
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد!')

async def ai_reply(update: Update, context):
    user_message = update.message.text or ''
    logger.info('Received message from %s: %s', update.effective_user.id if update.effective_user else 'unknown', user_message)
    try:
        if model:
            # Call Gemini and extract text safely
            resp = model.generate_content(f"أنت مساعد مكتب أبو مجد الحداد. أجب: {user_message}")
            # Different SDK versions may return different shapes; try common attributes
            text = getattr(resp, 'text', None)
            if not text:
                # try nested
                try:
                    text = resp.output[0].content[0].text
                except Exception:
                    text = str(resp)
        else:
            text = 'خدمة الذكاء الاصطناعي غير مفعلة حالياً. تواصل مع المطوّر.'
        await update.message.reply_text(text)
    except Exception:
        logger.exception('Error while processing AI reply')
        try:
            await update.message.reply_text('عذراً، حدث خطأ أثناء معالجة رسالتك.')
        except Exception:
            logger.exception('Failed to send error message to user')

application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))

# Provide a simple Flask health endpoint (Gunicorn/Render expects a web server)
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return 'OK', 200

# Run the telegram polling in a background thread so the Flask server can run in the main thread
def run_polling():
    """Run the telegram bot polling in a dedicated asyncio event loop."""
    try:
        asyncio.run(application.run_polling())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Polling stopped')
    except Exception:
        logger.exception('Polling terminated with an exception')

if __name__ == '__main__':
    # Start polling in background
    t = threading.Thread(target=run_polling, daemon=True)
    t.start()

    # Start Flask app (will bind to $PORT provided by Render/Heroku)
    logger.info('Starting Flask web server on port %s', PORT)
    flask_app.run(host='0.0.0.0', port=PORT)

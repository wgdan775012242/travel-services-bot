import os
import logging
import threading
import asyncio
import traceback
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
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')
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
    # Defensive checks
    try:
        user_message = getattr(update.message, 'text', '') if update and update.message else ''
    except Exception:
        user_message = ''

    logger.info('Received message from %s: %s', update.effective_user.id if update and update.effective_user else 'unknown', user_message)

    resp = None
    try:
        if model:
            # Call Gemini and extract text safely
            resp = model.generate_content(f"أنت مساعد مكتب أبو مجد الحداد. أجب: {user_message}")
            # Different SDK versions may return different shapes; try common attributes
            text = getattr(resp, 'text', None)
            if not text:
                try:
                    text = resp.output[0].content[0].text
                except Exception:
                    text = str(resp)
        else:
            text = 'خدمة الذكاء الاصطناعي غير مفعلة حالياً. تواصل مع المطوّر.'

        await update.message.reply_text(text)

    except Exception as e:
        # Log full traceback and debug info
        tb = traceback.format_exc()
        logger.error('Exception in ai_reply: %s', e)
        logger.error('Traceback:\n%s', tb)
        try:
            # Log update object for debugging (may be large)
            logger.debug('Update object: %s', update)
            if resp is not None:
                logger.debug('AI response object: %s', resp)
        except Exception:
            logger.exception('Failed to log debug info')

        # Send a friendly message to the user
        try:
            await update.message.reply_text('عذراً، حدث خطأ أثناء معالجة رسالتك.')
        except Exception:
            logger.exception('Failed to send error message to user')

        # Optionally notify admin if ADMIN_CHAT_ID is set
        if ADMIN_CHAT_ID:
            try:
                from telegram import Bot
                bot = Bot(token=TOKEN)
                notify_text = f"Bot error for user {update.effective_user.id if update and update.effective_user else 'unknown'}:\n{str(e)}\nSee logs for traceback."
                bot.send_message(chat_id=ADMIN_CHAT_ID, text=notify_text)
            except Exception:
                logger.exception('Failed to notify admin about the error')

application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))

# Provide a simple Flask health endpoint (Gunicorn/Render expects a web server)
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return 'OK', 200

# Run Flask in a background thread so the telegram polling can run in the main thread
def run_flask():
    logger.info('Starting Flask web server in background thread on port %s', PORT)
    # Use Flask's built-in server; Render/Gunicorn will manage production differently
    flask_app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Run the telegram polling in the main thread (so signal handlers can be registered)
    logger.info('Starting telegram polling (this will block the main thread)')
    try:
        # If run_polling is a coroutine, run it with asyncio.run in the main thread
        # Otherwise, call it directly. We handle both cases.
        run_poll = application.run_polling
        if asyncio.iscoroutinefunction(run_poll):
            asyncio.run(run_poll())
        else:
            run_poll()
    except (KeyboardInterrupt, SystemExit):
        logger.info('Polling stopped by KeyboardInterrupt/SystemExit')
    except Exception:
        logger.exception('Polling terminated with an exception')

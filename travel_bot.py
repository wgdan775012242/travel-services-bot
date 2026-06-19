import os
import json
import asyncio
import logging
from threading import Thread
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import urllib.request
import time
from asyncio import Semaphore

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
    <p>الرابط: <a href="https://travel-services-bot.onrender.com">https://travel-services-bot.onrender.com</a></p>
    <small>Free Tier • قد يستغرق الرد 10-40 ثانية بعد الخمول</small>
    """

# ====================== Gemini ======================
async def ask_gemini(user_message: str, max_retries: int = 5) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ خطأ في الإعدادات. يرجى التواصل مع الإدارة."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    OFFICE_INFO = """
معلومات مكتب أبو مجد الحداد للسفريات:
- الهاتف: +967775012242
- البريد: what775012242@outlook.sa
- التخصص: تأشيرات عمل يمن → سعودية، حجوزات طيران، خدمات سياحية.
"""

    SYSTEM_PROMPT = f"""
{OFFICE_INFO}
أنت مساعد ذكي ومحترف لمكتب أبو مجد الحداد.
أجب بلباقة واحترافية، وركز على خدمات السفر والتأشيرات.
إذا كان السؤال خارج النطاق، اعتذر واقترح التواصل المباشر.
"""

    full_prompt = f"{SYSTEM_PROMPT}\n\nرسالة العميل: {user_message}"

    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.75, "maxOutputTokens": 1000}
    }

    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=35) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['candidates'][0]['content']['parts'][0]['text'].strip()

        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"Gemini attempt {attempt+1} failed: {e}")
            
            if "429" in error_str or "resourceexhausted" in error_str:
                wait = (2 ** attempt) * 2.5
                await asyncio.sleep(wait)
                continue
            elif attempt == max_retries - 1:
                return "عذراً، الخدمة مزدحمة حالياً.\nيرجى التواصل مباشرة على: +967775012242"
            await asyncio.sleep(2)

    return "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى أو الاتصال على +967775012242"


# ====================== Keyboard ======================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛂 تأشيرات العمل", callback_data="visa")],
        [InlineKeyboardButton("✈️ حجوزات طيران", callback_data="flights")],
        [InlineKeyboardButton("📞 اتصل بنا", callback_data="contact")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ====================== Handlers ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً وسهلاً بك في *مكتب أبو مجد الحداد للسفريات والتأشيرات*\n\n"
        "كيف يمكنني خدمتك اليوم؟",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )


semaphore = Semaphore(4)

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    user_message = update.message.text.strip()
    
    async with semaphore:
        response = await ask_gemini(user_message)
        try:
            await update.message.reply_text(response, reply_markup=get_main_keyboard())
        except:
            await update.message.reply_text(response)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "visa":
        text = "🛂 للحصول على تأشيرة عمل إلى السعودية، يرجى إرسال:\n- اسمك الكامل\n- رقم الجواز\n- المهنة\n- مدة العقد"
    elif query.data == "flights":
        text = "✈️ للحجوزات الجوية، أخبرني بـ:\n- المدينة المغادرة\n- المدينة الوجهة\n- التاريخ المفضل"
    elif query.data == "contact":
        text = "📞 يمكنك التواصل مباشرة:\n+967775012242"
    else:
        text = "اختر من القائمة أدناه 👇"
    
    await query.edit_message_text(text=text, reply_markup=get_main_keyboard())


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
        logger.error("TOKEN أو API_KEY مفقود!")
        return

    application = Application.builder().token(TOKEN).build()

    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook deleted")

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, ai_reply))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Set Webhook
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        webhook_url = f"{render_url.rstrip('/')}/webhook"
        await application.bot.set_webhook(webhook_url)
        logger.info(f"Webhook set: {webhook_url}")
    else:
        logger.warning("No RENDER_EXTERNAL_URL - using polling fallback")

    await application.initialize()
    await application.start()
    logger.info("✅ Bot is fully running!")


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False)


# ====================== Run ======================
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

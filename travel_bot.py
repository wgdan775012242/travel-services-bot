import os
import json
import asyncio
import logging
from threading import Thread
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import urllib.request
import time
from asyncio import Semaphore

# ====================== إعدادات ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")  # غيرت الاسم للوضوح

# Flask للـ Keep Alive + Webhook
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Bot is running successfully!"

# ====================== Gemini ======================
async def ask_gemini(user_message: str, max_retries=5) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    OFFICE_INFO = """
معلومات مكتب أبو مجد الحداد للسفريات:
- الهاتف: +967775012242
- البريد: what775012242@outlook.sa
- التخصص: تأشيرات عمل يمن → سعودية، حجوزات طيران، خدمات سياحية.
"""

    SYSTEM_PROMPT = f"""
{OFFICE_INFO}
أنت مساعد مكتب أبو مجد الحداد. 
أجب بأسلوب مهني ولطيف. إذا كان السؤال خارج مجال السفر والتأشيرات والسياحة، اعتذر بلباقة واقترح التواصل المباشر.
"""

    full_prompt = f"{SYSTEM_PROMPT}\n\nرسالة العميل: {user_message}"

    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800,
        }
    }

    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url, 
                data=json.dumps(data).encode('utf-8'), 
                headers=headers, 
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['candidates'][0]['content']['parts'][0]['text']

        except Exception as e:
            error_str = str(e)
            logger.error(f"Gemini attempt {attempt+1} failed: {error_str}")
            
            if "429" in error_str or "ResourceExhausted" in error_str:
                wait = (2 ** attempt) + 1  # Exponential backoff
                logger.warning(f"Rate limit hit. Waiting {wait} seconds...")
                await asyncio.sleep(wait)
                continue
            elif attempt == max_retries - 1:
                return "عذراً، الخدمة مزدحمة حالياً. يرجى التواصل مباشرة على: +967775012242"
            else:
                await asyncio.sleep(2)
    
    return "عذراً، حدث خطأ. يرجى المحاولة مرة أخرى أو الاتصال على +967775012242"


# ====================== Telegram Handlers ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً وسهلاً بك في مكتب أبو مجد الحداد للسفريات والتأشيرات 👋\n"
        "كيف يمكنني مساعدتك اليوم؟"
    )


semaphore = Semaphore(3)  # حد أقصى 3 طلبات متزامنة

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    user_message = update.message.text.strip()
    
    async with semaphore:
        response = await ask_gemini(user_message)
        await update.message.reply_text(response)


# ====================== Flask Webhook ======================
@flask_app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        update_dict = request.get_json(force=True)
        update = Update.de_json(update_dict, application.bot)
        await application.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "ERROR", 500


# ====================== التشغيل الرئيسي ======================
application = None

async def main():
    global application
    if not TOKEN or not GEMINI_API_KEY:
        logger.error("TOKEN أو API_KEY غير موجودين!")
        return

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # حذف webhook قديم
    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhook deleted successfully")

    # إضافة Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, ai_reply))

    # إعداد Webhook
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL")
    if webhook_url:
        webhook_url = f"{webhook_url.rstrip('/')}/webhook"
        await application.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook set to: {webhook_url}")
    else:
        logger.warning("RENDER_EXTERNAL_URL غير موجود - سيعمل بالـ polling احتياطياً")

    await application.initialize()
    await application.start()


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    # تشغيل Flask في Thread منفصل
    Thread(target=run_flask, daemon=True).start()
    
    # تشغيل Telegram Application
    asyncio.run(main())
    
    # إبقاء البرنامج حياً
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        asyncio.run(application.stop())

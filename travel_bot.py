import os
import json
import asyncio
import logging
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import httpx  # تم استبدال urllib بـ httpx لدعم الأكواد غير المتزامنة

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
    <small>Free Tier • تم إصلاح استقرار الاتصال</small>
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

    # استخدام httpx.AsyncClient لضمان عدم حدوث Block أو CancelledError
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(url, json=data, headers=headers, timeout=35.0)
                if response.status_code == 200:
                    result = response.json()
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
                elif response.status_code == 429:
                    logger.warning(f"Gemini rate limit hit, retrying...")
                    wait = (2 ** attempt) * 2.5
                    await asyncio.sleep(wait)
                    continue
                else:
                    logger.error(f"Gemini API error {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"Gemini attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    return "عذراً، الخدمة مزدحمة حالياً.\nيرجى التواصل مباشرة على: +967775012242"
                await asyncio.sleep(2)

    return "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."

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
        "👋 أهلاً وسهلاً بك في *مكتب أبو مجد الحداد*\n\nكيف يمكنني خدمتك اليوم؟",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

semaphore = asyncio.Semaphore(4)

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # حماية من الرسائل الفارغة أو التحديثات الغريبة
    if not update.message or not update.message.text:
        return
        
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    user_message = update.message.text.strip()
    
    # استخدام معالجة الأخطاء والـ Semaphore لحماية الاتصال من الإلغاء
    try:
        async with semaphore:
            response = await ask_gemini(user_message)
            await update.message.reply_text(response, reply_markup=get_main_keyboard())
    except asyncio.CancelledError:
        logger.warning("المهمة تم إلغاؤها بشكل طبيعي بواسطة النظام.")
        raise
    except Exception as e:
        logger.error(f"Error in ai_reply: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "visa":
        text = "🛂 لتأشيرة العمل أرسل:\n- الاسم الكامل\n- رقم الجواز\n- المهنة"
    elif query.data == "flights":
        text = "✈️ أخبرني بتفاصيل الحجز:\n- المدينة المغادرة\n- الوجهة\n- التاريخ"
    elif query.data == "contact":
        text = "📞 التواصل المباشر:\n+967775012242"
    else:
        text = "اختر من القائمة 👇"
    
    try:
        await query.edit_message_text(text=text, reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Error updating message text: {e}")

# ====================== Webhook Setup ======================
application = None

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    global application
    if not application:
        return "Bot Not Ready", 503
    
    try:
        update_dict = request.get_json(force=True)
        # نقوم بجدولة التحديث داخل الـ Event loop الخاص بالبوت لمنع الـ CancelledError
        asyncio.run_coroutine_threadsafe(
            application.update_queue.put(Update.de_json(update_dict, application.bot)),
            application.loop
        )
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook Route Error: {e}")
        return "ERROR", 500

# ====================== Main Logic ======================
async def main():
    global application
    if not TOKEN or not GEMINI_API_KEY:
        logger.error("TOKEN أو API_KEY مفقود!")
        return

    # إنشاء التطبيق باستخدام نظام الـ Webhook المدمج الآمن
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    application.add_handler(CallbackQueryHandler(button_handler))

    # تهيئة وقراءة حالة البوت بالكامل
    await application.initialize()
    
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        webhook_url = f"{render_url.rstrip('/')}/webhook"
        await application.bot.set_webhook(webhook_url, drop_pending_updates=True)
        logger.info(f"Webhook successfully registered to: {webhook_url}")
    
    await application.start()
    
    # إبقاء الـ Event Loop يعمل بالتوازي مع الـ Webhook Queue
    async with application:
        while True:
            await asyncio.sleep(3600)

def run_flask():
    from werkzeug.serving import make_server
    port = int(os.environ.get("PORT", 8080))
    # تشغيل Flask كخادم مستقل وآمن بدون خيوط متعارضة
    server = make_server('0.0.0.0', port, flask_app)
    server.serve_forever()

if __name__ == '__main__':
    # 1. تشغيل Flask في الخلفية (Thread منفصل)
    import threading
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # 2. تشغيل البوت في الـ Main Thread لإدارة الـ Async بشكل سليم
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot execution stopped safely.")

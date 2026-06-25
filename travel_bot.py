import nest_asyncio
nest_asyncio.apply()

# الآن يمكنك إكمال باقي الاستدعاءات وكود البوت الخاص بك بشكل طبيعي...
import asyncio
import os
import logging
from threading import Thread
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# ====================== الإعدادات ======================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")

flask_app = Flask(__name__)
application = None

# ====================== الردود المحلية ======================
LOCAL_RESPONSES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته 👋\nكيف يمكنني خدمتك اليوم؟",
    "مرحبا": "مرحبا بك! 👋 كيف أقدر أساعدك في خدمات السفر والتأشيرات؟",
    "كم سعر التأشيرة": "🛂 أسعار التأشيرات تختلف حسب المهنة والمدة.\nأرسل لي المهنة + الجنسية لأعطيك السعر الدقيق.",
    "ايش خدماتكم": "نقدم:\n• تأشيرات عمل يمن → سعودية\n• حجوزات طيران\n• تأشيرات زيارة وعمرة\n• خدمات سياحية",
}

# ====================== النظام المرن للذكاء الاصطناعي ======================
MODELS_LIST = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]

async def ask_gemini(user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ خدمة الذكاء الاصطناعي غير متوفرة حالياً."

    genai.configure(api_key=GEMINI_API_KEY)
    system_prompt = "أنت مساعد متخصص لمكتب أبو مجد الحداد للسفريات والتأشيرات. كن لبقاً، استخدم الإيموجي، واطلب التفاصيل إذا كان السؤال عن الأسعار."

    for model_name in MODELS_LIST:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                f"{system_prompt}\n\nالعميل: {user_message}",
                generation_config={"temperature": 0.75}
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"فشل النموذج {model_name}: {e}. جاري التجربة...")
            await asyncio.sleep(1)
            continue
    
    return "عذراً، الخدمة مزدحمة حالياً. تواصل معنا على +967775012242"

# ====================== دوال البوت ======================
async def start(update: Update, context):
    await update.message.reply_text("👋 أهلاً بك في مكتب أبو مجد الحداد للسفريات والتأشيرات.")

async def ai_reply(update: Update, context):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    text = update.message.text.strip()
    
    for key in LOCAL_RESPONSES:
        if key in text:
            await update.message.reply_text(LOCAL_RESPONSES[key])
            return
            
    response = await ask_gemini(text)
    await update.message.reply_text(response)

# ====================== سيرفر Flask (Webhook) ======================
@flask_app.route('/', methods=['GET'])
def home():
    return "البوت يعمل بنجاح 24/7"

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    global application
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run_coroutine_threadsafe(application.process_update(update), asyncio.get_event_loop())
        return "OK", 200
    return "Method Not Allowed", 405

# ====================== التشغيل الأساسي ======================
async def main():
    global application
    application = Application.builder().token(TOKEN).updater(None).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    
    await application.initialize()
    await application.start()
    
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        webhook_url = f"{render_url.rstrip('/')}/webhook"
        await application.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook set to: {webhook_url}")
        
    stop_event = asyncio.Event()
    await stop_event.wait()

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, use_reloader=False)

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())

import sys
import time
import os
import logging
import asyncio
from threading import Thread

print("🚀 [1] جاري بدء تشغيل السيرفر...", flush=True)

try:
    import nest_asyncio
    nest_asyncio.apply()
    from flask import Flask, request
    from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
    from telegram.ext import Application, CommandHandler, MessageHandler, filters
    from google import genai  
    print("✅ [2] تم استدعاء جميع المكتبات بنجاح!", flush=True)
except Exception as e:
    print(f"❌ [خطأ] فشل في استدعاء المكتبات: {e}", flush=True)
    time.sleep(10)
    sys.exit(1)

# ================= الإعدادات =================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")

if not TOKEN:
    print("❌ خطأ قاتل: متغير TOKEN الخاص بتيليجرام مفقود في منصة Render!", flush=True)
    time.sleep(10)
    sys.exit(1)

if not GEMINI_API_KEY:
    print("⚠️ تحذير: متغير API_KEY الخاص بجوجل غير موجود في إعدادات Render!", flush=True)

flask_app = Flask(__name__)
application = None
main_loop = None

# ================= لوحة الأزرار الرئيسية =================
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🛂 خدماتنا"), KeyboardButton("💰 أسعارنا")],
        [KeyboardButton("📞 تواصل معنا"), KeyboardButton("✈️ حجز طيران")],
        [KeyboardButton("🕋 عمرة وزيارة")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# ================= الردود المحلية =================
LOCAL_RESPONSES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته 👋\nمرحباً بك في **مكتب أبو مجد الحداد** للسفريات والتأشيرات.",
    "مرحبا": "مرحباً بك! 👋 كيف أقدر أساعدك اليوم؟",
    "كم سعر": "🛂 الأسعار تختلف حسب المهنة والجنسية.\nأرسل لي (المهنة + الجنسية) لأعطيك السعر الدقيق.",
    "ايش خدماتكم": "يسعدنا تقديم الخدمات التالية:\n• تأشيرات عمل\n• حجز طيران\n• زيارة وعمرة\n• خدمات سياحية\n\n📞 للتواصل المباشر:\n• 775012242\n• 738465200",
}

# ================= الذكاء الاصطناعي (Gemini) =================
async def ask_gemini(user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ خدمة الذكاء الاصطناعي غير متوفرة حالياً."
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        system_prompt = """أنت مساعد ذكي مخصص لمكتب أبو مجد الحداد للسفريات والتأشيرات في اليمن.
كن لبقاً، محترفاً، واستخدم الإيموجي بشكل مناسب.
ركز على تقديم الخدمات: تأشيرات، حجوزات طيران، عمرة وزيارة.
أذكر أرقام التواصل دائمًا: 775012242 و 738465200"""
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{system_prompt}\n\nالعميل: {user_message}",
            config={'temperature': 0.7}
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return "عذراً، الخدمة مزدحمة حالياً.\n\n📞 تواصل معنا مباشرة:\n775012242\n738465200"

# ================= رسائل تيليجرام =================
async def start(update: Update, context):
    await update.message.reply_text(
        "👋 أهلاً بك في مكتب أبو مجد الحداد للسفريات والتأشيرات.\nالرجاء اختيار الخدمة المطلوبة من القائمة بالأسفل:",
        reply_markup=get_main_keyboard()
    )

async def ai_reply(update: Update, context):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    text = update.message.text.strip()
    
    # التعامل مع ضغطات الأزرار
    if text == "🛂 خدماتنا":
        await update.message.reply_text(LOCAL_RESPONSES["ايش خدماتكم"], reply_markup=get_main_keyboard())
        return
    elif text == "💰 أسعارنا":
        await update.message.reply_text(LOCAL_RESPONSES["كم سعر"], reply_markup=get_main_keyboard())
        return
    elif text == "📞 تواصل معنا":
        await update.message.reply_text("📞 للتواصل المباشر:\n• 775012242\n• 738465200", reply_markup=get_main_keyboard())
        return
    elif text == "✈️ حجز طيران" or text == "🕋 عمرة وزيارة":
        await update.message.reply_text("يسعدنا خدمتك! الرجاء تزويدنا بتفاصيل طلبك (التواريخ، الوجهة) وسنقوم بالرد عليك فوراً، أو تواصل معنا عبر الأرقام الموضحة.", reply_markup=get_main_keyboard())
        return

    # فحص الردود المحلية الأخرى
    for key in LOCAL_RESPONSES:
        if key in text:
            await update.message.reply_text(LOCAL_RESPONSES[key], reply_markup=get_main_keyboard())
            return
            
    # إذا لم يكن هناك رد محلي، أرسل الطلب للذكاء الاصطناعي
    response = await ask_gemini(text)
    await update.message.reply_text(response, reply_markup=get_main_keyboard())

# ================= سيرفر الويب (Webhook) =================
@flask_app.route('/', methods=['GET'])
def home():
    return "البوت يعمل بنجاح 24/7"

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    global application, main_loop
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        if main_loop:
            asyncio.run_coroutine_threadsafe(application.process_update(update), main_loop)
        return "OK", 200
    return "Method Not Allowed", 405

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 [3] جاري تشغيل سيرفر الويب على المنفذ {port}...", flush=True)
    try:
        flask_app.run(host='0.0.0.0', port=port, use_reloader=False)
    except Exception as e:
        print(f"❌ فشل تشغيل السيرفر: {e}", flush=True)

# ================= التشغيل الأساسي =================
async def main():
    global application, main_loop
    try:
        print("⚙️ [4] جاري إعداد البوت وربط التيليجرام...", flush=True)
        main_loop = asyncio.get_running_loop()
        application = Application.builder().token(TOKEN).updater(None).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
        
        await application.initialize()
        await application.start()
        
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_url:
            webhook_url = f"{render_url.rstrip('/')}/webhook"
            await application.bot.set_webhook(webhook_url)
            print(f"✅ [5] تم الربط بنجاح! الرابط: {webhook_url}", flush=True)
        
        # تشغيل Flask في Thread منفصل
        flask_thread = Thread(target=run_flask)
        flask_thread.start()
        
        # إبقاء البوت قيد التشغيل
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        print(f"❌ [خطأ] حدثت مشكلة أثناء التشغيل: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())

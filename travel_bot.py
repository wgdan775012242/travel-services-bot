import os
import asyncio
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import google.generativeai as genai
import time

# إعدادات الـ Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# الإعدادات
TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")

# القائمة الذكية للنماذج (Fallback Strategy)
MODELS_LIST = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]

async def ask_gemini(user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ خدمة الذكاء الاصطناعي غير متوفرة."

    # محاولة الاتصال عبر النماذج بالترتيب عند فشل أحدها
    for model_name in MODELS_LIST:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                f"أنت مساعد لمكتب أبو مجد الحداد. العميل: {user_message}",
                generation_config={"temperature": 0.7}
            )
            return response.text
        except Exception as e:
            logger.warning(f"فشل النموذج {model_name}: {e}. جاري تجربة النموذج التالي...")
            await asyncio.sleep(1) # تأخير بسيط قبل تجربة النموذج التالي
            continue
    
    return "عذراً، الخدمة مزدحمة حالياً. تواصل معنا على +967775012242"

# باقي كود البوت (نفس الهيكلية السابقة للـ Webhook)
flask_app = Flask(__name__)
application = Application.builder().token(TOKEN).updater(None).build()

# ... (باقي الـ Handlers كما في الكود السابق) ...

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run_coroutine_threadsafe(application.process_update(update), asyncio.get_event_loop())
        return "OK", 200
    return "Method Not Allowed", 405

import sys
import time

print("🚀 [1] جاري بدء تشغيل السيرفر...", flush=True)

try:
    import nest_asyncio
    nest_asyncio.apply()
    import asyncio
    import os
    import logging
    from threading import Thread
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
    await update.message.reply

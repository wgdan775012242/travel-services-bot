import nest_asyncio
nest_asyncio.apply()

import asyncio
import os
import logging
from threading import Thread
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# استدعاء المكتبة الجيل الجديد من جوجل
from google import genai  

# ====================== الإعدادات العامة ======================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")

flask_app = Flask(__name__)
application = None
main_loop = None  # حفظ حلقة التحكم لمنع أخطاء التزامن

# ====================== الردود التلقائية المحلية ======================
LOCAL_RESPONSES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته 👋\nمرحباً بك في مكتب أبو مجد الحداد للسفريات والخدمات. كيف يمكنني خدمتك اليوم؟",
    "مرحبا": "مرحباً بك! 👋 كيف أقدر أساعدك في خدمات السفر والتأشيرات؟",
    "كم سعر التأشيرة": "🛂 أسعار التأشيرات تختلف حسب المهنة والمدة المطلوبة.\nفضلاً أرسل لي (المهنة + الجنسية) لأعطيك السعر الدقيق فوراً.",
    "ايش خدماتكم": "يسعدنا تقديم الخدمات التالية:\n• تخليص تأشيرات العمل (اليمن ← السعودية)\n• حجز تذاكر طيران بكافة الخطوط\n• تأشيرات الزيارة والعمرة\n• المعاملات والخدمات السياحية",
}

# ====================== محرك الذكاء الاصطناعي (Gemini) ======================
async def ask_gemini(user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ خدمة الذكاء الاصطناعي غير متوفرة حالياً."

    try:
        # الاتصال الحديث بنظام الـ Client المباشر دون استخدام configure
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        system_prompt = (
            "أنت مساعد ذكي مخصص لمكتب أبو مجد الحداد للسفريات وخدمات التأشيرات في اليمن. "
            "كن لبقاً ومرحباً دائماً، استخدم الإيموجي المناسب، واطلب التفاصيل بدقة إذا كان سؤال العميل عن الأسعار أو المعاملات."
        )

        # الطريقة الرسمية الجديدة لاستدعاء نموذج 2.5 فلاش
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{system_prompt}\n\nالعميل: {user_message}",
            config={'temperature': 0.75}
        )
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return "عذراً، الخدمة مزدحمة حالياً. يسعدنا تواصلك معنا مباشرة عبر الرقم: +967775012242"

# ====================== معالجة رسائل تيليجرام ======================
async def start(update: Update, context):
    await update.message.reply_text("👋 أهلاً بك في مكتب أبو مجد الحداد للسفريات والتأشيرات. أنا هنا لمساعدتك والإجابة على استفساراتك 24/7.")

async def ai_reply(update: Update, context):
    # إظهار حالة "جاري الكتابة" لمنح العميل شعوراً بالتفاعل الإنساني
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    text = update.message.text.strip()
    
    # التحقق أولاً من الردود المحلية السريعة
    for key in LOCAL_RESPONSES:
        if key in text:
            await update.message.reply_text(LOCAL_RESPONSES[key])
            return
            
    # إذا لم يكن مبرمجاً محلياً، يتم تحويل السؤال للذكاء الاصطناعي
    response = await ask_gemini(text)
    await update.message.reply_text(response)

# ====================== سيرفر Flask والـ Webhook ======================
@flask_app.route('/', methods=['GET'])
def home():
    return

import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import uvicorn

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# استيراد مكتبة جوجل الرسمية للذكاء الاصطناعي
import google.generativeai as genai

# ====================== إعدادات السجلات (Logging) ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== متغيرات البيئة ======================
TOKEN = .environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")


# ====================== بناء تطبيق البوت ======================
ptb_app = Application.builder().token(TOKEN).build()
semaphore = asyncio.Semaphore(4)

# ====================== الذكاء الاصطناعي (Gemini) ======================
async def ask_gemini(user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ خطأ في الإعدادات (مفتاح API مفقود). يرجى التأكد من لوحة تحكم Render."

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

    try:
        # استخدام المكتبة الرسمية المستوردة
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # استدعاء غير متزامن لضمان عدم تعليق البوت
        response = await model.generate_content_async(full_prompt)
        
        if response.text:
            return response.text.strip()
        else:
            return "عذراً، لم أتمكن من صياغة رد مناسب. يرجى المحاولة مرة أخرى."

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "عذراً، الخدمة مزدحمة حالياً أو هناك مشكلة في الاتصال.\nيرجى التواصل مباشرة على: +967775012242"

# ====================== لوحة المفاتيح والأزرار ======================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛂 تأشيرات العمل", callback_data="visa")],
        [InlineKeyboardButton("✈️ حجوزات طيران", callback_data="flights")],
        [InlineKeyboardButton("📞 اتصل بنا", callback_data="contact")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ====================== دوال التعامل مع رسائل البوت ======================
async def start_cmd(update: Update, context):
    await update.message.reply_text(
        "👋 أهلاً وسهلاً بك في *مكتب أبو مجد الحداد*\n\nكيف يمكنني خدمتك اليوم؟",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context):
    if not update.message or not update.message.text:
        return
        
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    user_message = update.message.text.strip()
    
    try:
        async with semaphore:
            response = await ask_gemini(user_message)
            await update.message.reply_text(response, reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Error handling message: {e}")

async def handle_buttons(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    text = "اختر من القائمة 👇"
    if query.data == "visa":
        text = "🛂 لتأشيرة العمل أرسل:\n- الاسم الكامل\n- رقم الجواز\n- المهنة"
    elif query.data == "flights":
        text = "✈️ أخبرني بتفاصيل الحجز:\n- المدينة المغادرة\n- الوجهة\n- التاريخ"
    elif query.data == "contact":
        text = "📞 التواصل المباشر:\n+967775012242"
        
    # تحديث الرسالة بالزر الذي تم اختياره مع إبقاء الأزرار
    try:
        await query.edit_message_text(text=text, reply_markup=get_main_keyboard

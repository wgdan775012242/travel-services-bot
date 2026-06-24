import os
import json
import asyncio
import logging
import httpx
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import uvicorn

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# ====================== إعدادات السجلات (Logging) ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== متغيرات البيئة ======================
TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

# التأكد من وجود التوكن
if not TOKEN:
    logger.error("⚠️ لم يتم العثور على TOKEN البوت في متغيرات البيئة!")

# ====================== بناء تطبيق البوت (PTB) ======================
ptb_app = Application.builder().token(TOKEN).build()
semaphore = asyncio.Semaphore(4)

# ====================== الذكاء الاصطناعي (Gemini) ======================
async def ask_gemini(user_message: str, max_retries: int = 3) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ خطأ في الإعدادات (مفتاح API مفقود). يرجى التواصل مع الإدارة."

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

    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(url, json=data, headers=headers, timeout=30.0)
                if response.status_code == 200:
                    result = response.json()
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
                elif response.status_code == 429:
                    logger.warning("ضغط على خوادم Gemini، جاري إعادة المحاولة...")
                    await asyncio.sleep((2 ** attempt) * 2)
                    continue
                else:
                    logger.error(f"Gemini API error {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"محاولة الاتصال {attempt+1} فشلت: {e}")
                if attempt == max_retries - 1:
                    return "عذراً، الخدمة مزدحمة حالياً.\nيرجى التواصل مباشرة على: +967775012242"
                await asyncio.sleep(2)
    return "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."

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
    
    try:
        await query.edit_message_text(text=text, reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Error updating button text: {e}")

# ربط الدوال بالبوت
ptb_app.add_handler(CommandHandler("start", start_cmd))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
ptb_app.add_handler(CallbackQueryHandler(handle_buttons))

# ====================== إعداد خادم FastAPI ======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # عند تشغيل السيرفر
    await ptb_app.initialize()
    if RENDER_URL:
        webhook_url = f"{RENDER_URL.rstrip('/')}/webhook"
        await ptb_app.bot.set_webhook(webhook_url, drop_pending_updates=True)
        logger.info(f"✅ تم تفعيل Webhook بنجاح على: {webhook_url}")
    await ptb_app.start()
    
    yield # هنا يعمل السيرفر
    
    # عند إيقاف السيرفر
    await ptb_app.stop()
    await ptb_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 50px; background-color: #f4f4f9;">
            <h1 style="color: #4CAF50;">✅ البوت يعمل بنجاح 24/7</h1>
            <h2>مكتب أبو مجد الحداد للسفريات والتأشيرات</h2>
            <p style="color: #666;">🚀 <b>Powered by:</b> FastAPI & Python-Telegram-Bot v20</p>
        </body>
    </html>
    """

@app.post("/webhook")
async def webhook_endpoint(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, ptb_app.bot)
        await ptb_app.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Webhook Error: {e}")
        return Response(status_code=500)

# ====================== التشغيل المحلي (للتجارب فقط) ======================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("travel_bot:app", host="0.0.0.0", port=port)

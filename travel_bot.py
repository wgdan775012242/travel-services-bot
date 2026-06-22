import os
import asyncio
import logging
import httpx
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse

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

if not TOKEN:
    logger.error("⚠️ لم يتم العثور على TOKEN البوت في متغيرات البيئة!")

# ====================== بناء تطبيق البوت ======================
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
- التخصص: تأشيرات عمل يمن -> سعودية، حجوزات طيران، خدمات سياحية.
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
                    try:
                        return result['candidates'][0]['content']['parts'][0]['text'].strip()
                    except (KeyError, IndexError) as e:
                        logger.error(f"خطأ في تحليل الاستجابة: {result}")
                        return "عذراً، لم أتمكن من صياغة الرد بشكل صحيح. يرجى إعادة المحاولة."
                        
                elif response.status_code == 429:
                    logger.warning("ضغط على خوادم Gemini، جاري إعادة المحاولة...")
                    await asyncio.sleep((2 ** attempt) * 2)
                    continue
                else:
                    logger.error(f"Gemini API error {response.status_code}: {response.text}")
                    if response.status_code == 400:
                        return "حدث خطأ (تأكد من صلاحية مفتاح الـ API الخاص بـ Gemini في إعدادات Render)."
            except Exception as e:
                logger.error(f"محاولة الاتصال {attempt+1} فشلت: {e}")
                if attempt == max_retries - 1:
                    return "عذراً، الخدمة مزدحمة حالياً.\nيرجى التواصل مباشرة على: +967775012242"
                await asyncio.sleep(2)
    return "حدث خطأ غير متوقع في خوادم الذكاء الاصطناعي. يرجى المحاولة مرة أخرى."

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
    await query.edit_message_text(text=text, reply_markup=get_main_keyboard())

# ====================== ربط الدوال بالبوت ======================
ptb_app.add_handler(CommandHandler("start", start_cmd))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
ptb_app.add_handler(CallbackQueryHandler(handle_buttons))

# ====================== إعداد FastAPI & Webhook ======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # تشغيل تطبيق التيليجرام في الخلفية وتعيين رابط الـ Webhook
    await ptb_app.initialize()
    if RENDER_URL:
        # التأكد من إزالة الشرطة المائلة الزائدة في نهاية الرابط إن وجدت
        webhook_url = f"{RENDER_URL.rstrip('/')}/webhook"
        await ptb_app.bot.set_webhook(url=webhook_url)
        logger.info(f"✅ تم ربط Webhook بنجاح: {webhook_url}")
    else:
        logger.warning("⚠️ RENDER_EXTERNAL_URL مفقود! لم يتم تفعيل Webhook.")
    
    await ptb_app.start()
    yield
    # الإغلاق الآمن عند إيقاف السيرفر
    await ptb_app.stop()
    await ptb_app.shutdown()

# إنشاء السيرفر وربطه بدورة الحياة
app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """نقطة استقبال التحديثات من تيليجرام وتمريرها للبوت"""
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, ptb_app.bot)
        await ptb_app.update_queue.put(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"خطأ في الـ Webhook: {e}")
        return Response(status_code=500)

@app.get("/")
async def root():
    """صفحة للتحقق من أن السيرفر يعمل بنجاح"""
    return HTMLResponse("<h1>✅ السيرفر والبوت يعملان بنجاح!</h1>")


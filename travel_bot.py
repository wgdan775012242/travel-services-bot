import os
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from google import genai

# --- إعداد السجلات ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("travel_bot")

# --- المفاتيح من متغيرات البيئة ---
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# --- معلومات المكتب (مدمجة) ---
OFFICE_INFO = (
    "معلومات مكتب أبو مجد الحداد للسفريات:\n"
    "- الهاتف: +967775012242\n"
    "- البريد الإلكتروني: what775012242@outlook.sa\n"
    "- فيسبوك: ابومجد الحداد خدمات سفريات وسياحه\n"
    "- إنستغرام: وجدان الحداد-ابومجدالحداد\n"
    "- الخدمات: تأشيرات، حجوزات طيران، خدمات سياحية، وسفر.\n"
)

# --- تهيئة عميل Gemini ---
client = None
if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    logger.error("API_KEY غير معرّف في متغيرات البيئة")

# --- دالة الاتصال بـ Gemini ---
def ask_gemini(user_message: str) -> str:
    if not client:
        return "عذراً، خدمة الذكاء الاصطناعي غير مفعلة حالياً. الرجاء التواصل معنا مباشرة على الرقم: +967775012242"

    prompt = (
        f"{OFFICE_INFO}\n"
        "بصفتك مساعداً ذكياً لمكتب أبو مجد الحداد، أجب على رسالة المستخدم التالية بصورة مهنية وودية وباللغة العربية:\n"
        f"{user_message}\n"
        "أجب بإيجاز واذكر إذا كنت بحاجة لمزيد من التفاصيل أو رقم الحجز. لا تضف إعلانات تجارية."
    )

    try:
        response = client.responses.generate(
            model="gemini-3.5-flash",   # النموذج الموصى به
            input=prompt
        )
        return response.output_text or "عذراً، لم يتم توليد رد."
    except Exception as e:
        logger.exception("خطأ في الاتصال بـ Gemini: %s", e)
        return "عذراً، الخدمة غير متاحة حالياً، يرجى التواصل معنا مباشرة على الرقم: +967775012242"

# --- دوال تليجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد للسفريات! أنا مساعدك الذكي، كيف يمكنني خدمتك اليوم؟')

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, ask_gemini, user_text)
    await update.message.reply_text(response)

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    if not TOKEN:
        logger.error("TOKEN غير معرّف في متغيرات البيئة. تأكد من إضافته قبل التشغيل.")
        print("خطأ: يرجى التأكد من إضافة TOKEN في إعدادات البيئة (TOKEN)")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
        logger.info("البوت يعمل الآن ويستمع للرسائل...")
        print("البوت يعمل الآن ويستمع للرسائل...")
        application.run_polling()

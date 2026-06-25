import os
import json
import urllib.request
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

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

# --- دالة الاتصال المباشر بـ Gemini (تشغيل في executor لتجنب الحظر) ---
def ask_gemini_direct(user_message: str) -> str:
    """نداء متزامن إلى Gemini باستخدام urllib. سيتم استدعاؤها من threadpool لمنع حظر حلقة الأحداث."""
    if not API_KEY:
        logger.error("API_KEY غير معرّف في متغيرات البيئة")
        return "عذراً، خدمة الذكاء الاصطناعي غير مفعلة حالياً. الرجاء التواصل معنا مباشرة على الرقم: +967775012242"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={API_KEY}"

    prompt = (
        f"{OFFICE_INFO}\n"
        "بصفتك مساعداً ذكياً لمكتب أبو مجد الحداد، أجب على رسالة المستخدم التالية بصورة مهنية وودية وباللغة العربية:\n"
        f"{user_message}\n"
        "أجب بإيجاز واذكر إذا كنت بحاجة لمزيد من التفاصيل أو رقم الحجز. لا تضف إعلانات تجارية."
    )

    data = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}

    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read().decode('utf-8')
            result = json.loads(body)

            # حاول استخراج نص الرد من صيغ مختلفة
            if isinstance(result, dict):
                try:
                    return result['candidates'][0]['content']['parts'][0]['text']
                except Exception:
                    pass

                def find_text(o):
                    if isinstance(o, dict):
                        for v in o.values():
                            t = find_text(v)
                            if t:
                                return t
                    elif isinstance(o, list):
                        for item in o:
                            t = find_text(item)
                            if t:
                                return t
                    elif isinstance(o, str):
                        if len(o) > 20:
                            return o
                    return None

                text = find_text(result)
                if text:
                    return text

            logger.error("تعذر استخراج الرد من استجابة Gemini: %s", body)
            return "عذراً، لم يتمكّن النظام من توليد رد تلقائي الآن. الرجاء التواصل معنا مباشرة: +967775012242"

    except Exception as e:
        logger.exception("خطأ في الاتصال بـ Gemini: %s", e)
        return "عذراً، الخدمة غير متاحة حالياً، يرجى التواصل معنا مباشرة على الرقم: +967775012242"


# --- دوال تليجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد للسفريات! أنا مساعدك الذكي، كيف يمكنني خدمتك اليوم؟')


async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""

    # تشغيل نداء الشبكة في executor حتى لا يحجب حلقة الأحداث
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, ask_gemini_direct, user_text)

    await update.message.reply_text(response or "عذراً، لم يتم توليد رد.")


# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    if not TOKEN:
        logger.error("TOKEN غير معرّف في ��تغيرات البيئة. تأكد من إضافته قبل التشغيل.")
        print("خطأ: يرجى التأكد من إضافة TOKEN في إعدادات البيئة (TOKEN)")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
        logger.info("البوت يعمل الآن ويستمع للرسائل...")
        print("البوت يعمل الآن ويستمع للرسائل...")
        application.run_polling()


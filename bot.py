import os
import json
import urllib.request
import logging
import asyncio
from flask import Flask, request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- إعداد السجلات ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("bot")

# --- متغيرات البيئة ---
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")  # اختياري

if not TOKEN:
    logger.error("TOKEN غير معرف في متغيرات البيئة")
    raise RuntimeError("TOKEN env var is required")

# --- دالة الاتصال المباشر بـ Gemini (مزامنة) ---
def ask_gemini_direct(user_message: str) -> str:
    if not API_KEY:
        logger.error("API_KEY غير معرّف في متغيرات البيئة")
        return "عذراً، خدمة الذكاء الاصطناعي غير مفعلة حالياً. الرجاء التواصل معنا مباشرة على الرقم: +967775012242"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

    prompt = (
        "معلومات مكتب أبو مجد الحداد للسفريات:\n"
        "- الهاتف: +967775012242\n"
        "- البريد الإلكتروني: what775012242@outlook.sa\n"
        "- فيسبوك: ابومجد الحداد خدمات سفريات وسياحه\n"
        "- إنستغرام: وجدان الحداد-ابومجدالحداد\n"
        "- الخدمات: تأشيرات، حجوزات طيران، خدمات سياحية، وسفر.\n\n"
        "بصفتك مساعداً ذكياً لمكتب أبو مجد الحداد، أجب على رسالة المستخدم التالية بصورة مهنية وودية وباللغة العربية:\n"
        f"{user_message}\n"
        "أجب بإيجاز واذكر إذا كنت بحاجة لمزيد من التفاصيل أو رقم الحجز. لا تضف إعلانات تجارية."
    )

    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={"Content-Type": "application/json"}, method='POST')
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read().decode('utf-8')
            result = json.loads(body)

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


# --- إعداد Flask و Telegram Application ---
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# --- Handlers ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد للسفريات! أنا مساعدك الذكي، كيف يمكنني خدمتك اليوم؟')

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, ask_gemini_direct, user_text)
    await update.message.reply_text(response or "عذراً، لم يتم توليد رد.")

application.add_handler(CommandHandler("start", start_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# --- Webhook route ---
if WEBHOOK_SECRET:
    WEBHOOK_ROUTE = f"{WEBHOOK_PATH}/{WEBHOOK_SECRET}"
else:
    WEBHOOK_ROUTE = WEBHOOK_PATH

@app.route(WEBHOOK_ROUTE, methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True)
    except Exception as e:
        logger.exception("خطأ في قراءة JSON من Telegram webhook: %s", e)
        return Response(status=400)

    update = Update.de_json(data, application.bot)
    application.create_task(application.process_update(update))
    return Response(status=200)

# expose flask app object as 'flask_app' so gunicorn can import it
flask_app = app

if __name__ == '__main__':
    flask_app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

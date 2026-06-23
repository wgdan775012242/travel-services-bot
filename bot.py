import os
import json
import urllib.request
import logging
import asyncio
from flask import Flask, request, Response, jsonify
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

# --- معلومات المكتب ---
OFFICE_INFO = (
    "مكتب أبو مجد الحداد للسفريات:\n"
    "الهاتف: +967775012242\n"
    "البريد الإلكتروني: what775012242@outlook.sa\n"
    "فيسبوك: ابومجد الحداد خدمات سفريات وسياحه\n"
    "انست��رام: وجدان الحداد-ابومجدالحداد\n"
    "الخدمات: تأشيرات، حجوزات طيران، خدمات سياحية، وسفر.\n"
)

# --- دالة الاتصال المباشر بـ Gemini (مزامنة) ---
def ask_gemini_direct(user_message: str) -> str:
    if not API_KEY:
        logger.error("API_KEY غير معرّف في متغيرات البيئة")
        return "عذراً، خدمة الذكاء الاصطناعي غير مفعلة حالياً. الرجاء التواصل معنا مباشرة على الرقم: +967775012242"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

    prompt = (
        f"{OFFICE_INFO}\n"
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

            # محاولة استخراج النص من صيغ مختلفة للمخرجات
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


# --- إعداد Flask ---
app = Flask(__name__)
# expose flask app object as 'flask_app' so gunicorn can import it
flask_app = app

# --- Telegram application (قد يكون None إذا لم يتوفر TOKEN) ---
telegram_app = None

# --- Handlers ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد للسفريات! أنا مساعدك الذكي، كيف يمكنني خدمتك اليوم؟')


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, ask_gemini_direct, user_text)
    await update.message.reply_text(response or "عذراً، لم يتم توليد رد.")


# --- تهيئة Telegram application فقط إذا كان التوكن معطى ---
if TOKEN:
    try:
        telegram_app = Application.builder().token(TOKEN).build()
        telegram_app.add_handler(CommandHandler("start", start_handler))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        logger.info("Telegram Application initialized.")
    except Exception as e:
        logger.exception("خطأ أثناء تهيئة Telegram Application: %s", e)
        telegram_app = None
else:
    logger.warning("TOKEN غير معرّف — Telegram bot لن يعمل حتى تضيف TOKEN في متغيرات البيئة.")


# --- Webhook route ---
if WEBHOOK_SECRET:
    WEBHOOK_ROUTE = f"{WEBHOOK_PATH}/{WEBHOOK_SECRET}"
else:
    WEBHOOK_ROUTE = WEBHOOK_PATH


@app.route(WEBHOOK_ROUTE, methods=["POST"])
def telegram_webhook():
    if telegram_app is None:
        logger.warning("وصول طلب إلى webhook لكن Telegram application غير مهيأ.")
        return Response("Bot not configured", status=503)

    try:
        data = request.get_json(force=True)
    except Exception as e:
        logger.exception("خطأ في قراءة JSON من Telegram webhook: %s", e)
        return Response(status=400)

    update = Update.de_json(data, telegram_app.bot)
    telegram_app.create_task(telegram_app.process_update(update))
    return Response(status=200)


# health / index route
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "travel-services-bot",
        "telegram_configured": bool(TOKEN),
        "webhook_route": WEBHOOK_ROUTE
    }), 200


if __name__ == '__main__':
    # تشغيل محلي مخصص للتطوير: إذا توكن موجود سنستخدم polling كخيار اختبار
    if TOKEN and telegram_app is not None:
        print("TOKEN معطى — تشغيل polling محلي لاختبار التطوير")
        try:
            # تشغيل polling للتطوير (لا يُستخدم في الإنتاج مع Gunicorn)
            telegram_app.run_polling()
        except Exception as e:
            logger.exception("خطأ في تشغيل polling: %s", e)
    else:
        # تشغيل flask فقط
        print("TOKEN غير معطى أو غير صالح — تشغيل Flask فقط على المنفذ 5000")
        flask_app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

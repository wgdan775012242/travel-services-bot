import os
import json
import urllib.request
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- إعداد السجلات ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- المفاتيح من متغيرات البيئة في Render ---
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# --- إعداد سيرفر وهمي (Flask) لمنع توقف Render ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running successfully!"

def run_flask():
    # Render يمرر المنفذ تلقائياً في متغير البيئة PORT، وإذا لم يجده يفتح منفذ 8080
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# --- معلومات المكتب وتوجيهات الذكاء الاصطناعي الصارمة ---
OFFICE_INFO = """
معلومات مكتب أبو مجد الحداد للسفريات:
- الهاتف: 967775012242+
- البريد الإلكتروني: what775012242@outlook.sa
- فيسبوك: ابومجد الحداد خدمات سفريات وسياحه
- إنستغرام: وجدان الحداد-ابومجدالحداد
- التخصص: تأشيرات العمل من اليمن إلى السعودية، حجوزات طيران، خدمات سياحية، وسفر.
"""

SYSTEM_PROMPT = f"""
{OFFICE_INFO}
أنت مساعد آلي ذكي يمثل "مكتب أبو مجد الحداد".
مهمتك الوحيدة والأساسية هي الرد على استفسارات العملاء في المجالات التالية فقط:
1. السفر والسياحة.
2. تأشيرات العمل (تحديداً من اليمن إلى السعودية).
3. المعاملات الخاصة بالسفر وحجوزات الطيران.

تعليمات صارمة يجب الالتزام بها:
- أجب بأسلوب مهني، محترم، وواضح.
- إذا سألك المستخدم عن أي موضوع خارج هذه التخصصات (مثل البرمجة، السياسة، الأخبار، أو مواضيع عامة)، اعتذر بلباقة وقل: "عذراً، أنا مساعد مخصص فقط لخدمات السفر والسياحة وتأشيرات العمل بمكتب أبو مجد الحداد."
- لا تقم بتأليف أسعار من عندك. إذا سأل عن سعر غير ثابت، اطلب منه التواصل عبر الهاتف.
"""

# --- دالة الاتصال المباشر بـ Gemini ---
def ask_gemini_direct(user_message):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
    full_prompt = f"{SYSTEM_PROMPT}\n\nرسالة العميل: '{user_message}'\nالرد المناسب:"
    
    data = {"contents": [{"parts": [{"text": full_prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logging.error(f"خطأ في الاتصال بـ Gemini: {e}")
        return "عذراً، الخدمة تواجه ضغطاً في الوقت الحالي، يرجى التواصل معنا مباشرة على الرقم: 967775012242+"

# --- دوال تليجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "أهلاً بك في مكتب أبو مجد الحداد للسفريات! ✈️\n\n"
        "أنا مساعدك الآلي، متواجد لخدمتك في استفسارات السفر، السياحة، "
        "وتأشيرات العمل من اليمن إلى السعودية.\n\n"
        "كيف يمكنني خدمتك اليوم؟"
    )
    await update.message.reply_text(welcome_text)

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = ask_gemini_direct(update.message.text)
    await update.message.reply_text(response)

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    if not TOKEN:
        print("خطأ: يرجى التأكد من إضافة TOKEN في متغيرات البيئة")
    else:
        # 1. تشغيل السيرفر الوهمي في خلفية الكود لخدع منصة Render المجانية
        Thread(target=run_flask, daemon=True).start()
        print("تم تشغيل السيرفر الوهمي بنجاح...")

        # 2. تشغيل بوت تليجرام كالمعتاد
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
        print("البوت يعمل الآن ويستمع لرسائل العملاء بشكل مخصص...")
        application.run_polling()

import os
import json
import urllib.request
import logging
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# إعداد السجلات
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# معلومات المكتب المدمجة
OFFICE_INFO = """
معلومات مكتب أبو مجد الحداد للسفريات:
- الهاتف: 967775012242+
- البريد الإلكتروني: what775012242@outlook.sa
- فيسبوك: ابومجد الحداد خدمات سفريات وسياحه
- إنستغرام: وجدان الحداد-ابومجدالحداد
- الخدمات: تأشيرات، حجوزات طيران، خدمات سياحية.
"""

def ask_gemini_direct(user_message):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
    prompt = f"{OFFICE_INFO}\nالمستخدم يسأل: {user_message}\nأجب بأسلوب مهني وودود."
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    # محاولة الاتصال 3 مرات في حال حدوث خطأ 503
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            logging.warning(f"محاولة {attempt+1} فشلت: {e}")
            time.sleep(2) # انتظار ثانيتين قبل إعادة المحاولة
            
    return "عذراً، خدمة الذكاء الاصطناعي مضغوطة حالياً، يرجى التواصل معنا مباشرة على الرقم: 967775012242+"

async def start(update, context):
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد للسفريات!')

async def ai_reply(update, context):
    response = ask_gemini_direct(update.message.text)
    await update.message.reply_text(response)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    application.run_polling()

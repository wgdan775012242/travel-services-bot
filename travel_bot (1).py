import os
import json
import urllib.request
import logging
import asyncio  # تمت إضافة مكتبة المهام المتزامنة بدلاً من time
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- إعداد السجلات ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- المفاتيح من متغيرات البيئة في Render ---
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# --- إعداد سيرفر وهمي (Flask) ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# --- معلومات المكتب ---
OFFICE_INFO = """
معلومات مكتب أبو مجد الحداد للسفريات:
- الهاتف: 967775012242+
- البريد الإلكتروني: what775012242@outlook.sa
- التخصص: تأشيرات العمل من اليمن إلى السعودية، حجوزات طيران، خدمات سياحية.
"""

SYSTEM_PROMPT = f"""
{OFFICE_INFO}
أنت مساعد آلي ذكي يمثل "مكتب أبو مجد الحداد". 
أجب بأسلوب مهني. إذا كان الاستفسار خارج السفر والسياحة، اعتذر بلباقة.
"""

# --- دالة الاتصال المباشر (تقوم بمحاولة واحدة فقط وترجع النتيجة) ---
def ask_gemini_single_request(user_message):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
    full_prompt = f"{SYSTEM_PROMPT}\n\nرسالة العميل: '{user_message}'"
    
    data = {"contents": [{"parts": [{"text": full_prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        return result['candidates'][0]['content']['parts'][0]['text']

# --- دوال تليجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك في مكتب أبو مجد الحداد. كيف يمكنني مساعدتك اليوم؟")

# هنا يكمن السحر: معالجة ذكية للأخطاء بدون تجميد البوت
async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    user_message = update.message.text
    retries = 3
    
    for i in range(retries):
        try:
            # استخدام to_thread يمنع البوت من التجميد لباقي المستخدمين أثناء انتظار رد Gemini
            response = await asyncio.to_thread(ask_gemini_single_request, user_message)
            await update.message.reply_text(response)
            return  # إنهاء الدالة بنجاح
            
        except Exception as e:
            logging.error(f"محاولة {i+1} فشلت: {e}")
            if "429" in str(e):
                await asyncio.sleep(5)  # انتظار آمن لا يوقف البوت عن العمل للمستخدمين الآخرين
            else:
                await asyncio.sleep(2)
                
    # في حال استنفاد كل المحاولات (الضغط شديد جداً من جهة جوجل)
    await update.message.reply_text("عذراً، الخادم يواجه ضغطاً كبيراً حالياً. يرجى التواصل معنا مباشرة على الرقم: 967775012242+")

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    if not TOKEN or not API_KEY:
        print("خطأ: تأكد من ضبط TOKEN و API_KEY في متغيرات البيئة")
    else:
        Thread(target=run_flask, daemon=True).start()
        
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
        
        print("البوت يعمل الآن ومحمي ضد التوقف...")
        application.run_polling()

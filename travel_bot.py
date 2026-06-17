import os
import json
import urllib.request
import logging
import threading
import time
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- الإعدادات ---
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")
# لاحقاً سنضيف هنا معرفات القنوات والمجموعات

logging.basicConfig(level=logging.INFO)

# --- دالة الذكاء الاصطناعي (Gemini) ---
def ask_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))['candidates'][0]['content']['parts'][0]['text']
    except:
        return "عذراً، تعذر الاتصال بالذكاء الاصطناعي."

# --- دالة سحب ونشر الوظائف (تعمل في الخلفية) ---
def job_scraper_loop():
    while True:
        try:
            # مثال لسحب البيانات من أحد المواقع
            url = "https://wazifa.mshatly.com/"
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            job = soup.find('h2').text.strip()
            
            # هنا سنضيف لاحقاً كود إرسال النتيجة إلى تليجرام وواتساب
            logging.info(f"تم سحب وظيفة جديدة: {job}")
            
        except Exception as e:
            logging.error(f"خطأ في سحب الوظائف: {e}")
        
        time.sleep(3600) # فحص كل ساعة

# --- دوال تليجرام (كما هي) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('مرحباً بك! أنا جاهز لمساعدتك.')

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = ask_gemini(update.message.text)
    await update.message.reply_text(response)

# --- التشغيل ---
if __name__ == '__main__':
    # تشغيل الساحب في خيط منفصل (Thread)
    threading.Thread(target=job_scraper_loop, daemon=True).start()
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    application.run_polling()

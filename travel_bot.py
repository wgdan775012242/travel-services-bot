import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# إعداد السجلات (Logging) لمعاينة أي نشاط
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 1. إعداد خادم ويب وهمي (Flask) لإرضاء منصة Render ومنع إغلاق البوت
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running successfully!"

def run_flask():
    # جلب المنفذ تلقائياً من Render أو استخدام 8080 كافتراضي
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# تشغيل خادم الويب في خلفية منفصلة تماماً عن البوت
flask_thread = Thread(target=run_flask)
flask_thread.start()

# 2. جلب المفاتيح من إعدادات البيئة في Render
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# تهيئة الذكاء الاصطناعي (Gemini)
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')

# 3. دالة الترحيب عند الضغط على /start في تليجرام
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_

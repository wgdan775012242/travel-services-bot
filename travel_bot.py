import os
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# إعداد السجلات لمراقبة أداء البوت
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# جلب المفاتيح السرية من إعدادات البيئة (Environment Variables) في Render
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# تهيئة الذكاء الاصطناعي (Gemini)
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')

# دالة الترحيب عند الضغط على /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد للسفريات، كيف يمكنني مساعدتك اليوم؟')

# دالة الرد الذكي باستخدام Gemini
async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    try:
        # صياغة الطلب للذكاء الاصطناعي
        prompt = f"المستخدم يسأل: {user_text}\nأنت مساعد ذكي لمكتب سفريات (مكتب أبو مجد الحداد للسفريات)، أجب على هذا السؤال بطريقة مهنية ومفصلة باللغة العربية."
        response = model.generate_content(prompt)
        
        # إرسال الإجابة للمستخدم في تليجرام
        await update.message.reply_text(response.text)
    except Exception as e:
        # في حال حدوث خطأ، يطبع التفاصيل في الـ Logs ويرسل تنبيه مبسط
        print(f"Error details: {e}")
        await update.message.reply_text(f"عذراً، حدث خطأ أثناء معالجة الطلب.\nتفاصيل الخطأ: {str(e)}")

# دالة مخصصة لإبقاء السيرفر نشطاً دون الحاجة لمنافذ ويب (Flask)
async def keep_alive():
    while True:
        print("البوت يعمل بنشاط في الخلفية...")
        await asyncio.sleep(30)

if __name__ == '__main__':
    print("جاري تشغيل البوت...")
    
    # بناء تطبيق التليجرام
    application = ApplicationBuilder().token(TOKEN).build()
    
    # ربط الأوامر والرسائل بالدوال
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    
    # تشغيل آلية البوت المستمرة
    application.run_polling()

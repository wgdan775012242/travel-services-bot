import os
import logging
import threading
import http.server
import socketserver
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# --- 1. إعداد السجلات (Logging) لمراقبة الأداء ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- 2. الحل الجذري لمشكلة Render (تخطي قيود المنافذ) ---
# نستخدم مكتبات بايثون الأساسية لفتح منفذ وهمي يرضي سيرفرات Render دون الحاجة لمكتبات خارجية
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    Handler = http.server.SimpleHTTPRequestHandler
    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            print(f"تم فتح المنفذ {port} بنجاح. السيرفر الآن مستقر.")
            httpd.serve_forever()
    except Exception as e:
        print(f"ملاحظة في الخادم الوهمي: {e}")

# تشغيل الخادم الوهمي في خلفية منفصلة تماماً لكي لا يعطل عمل البوت
server_thread = threading.Thread(target=run_dummy_server, daemon=True)
server_thread.start()

# --- 3. جلب المفاتيح من إعدادات البيئة ---
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# --- 4. إعداد الذكاء الاصطناعي (حل مشكلة 404) ---
genai.configure(api_key=API_KEY)
# تم التحديث إلى الإصدار الأحدث والأسرع الذي يعمل بكفاءة ولا يسبب أخطاء
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 5. دوال البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد للسفريات، كيف يمكنني مساعدتك اليوم؟')

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    try:
        # صياغة الطلب الموجه للذكاء الاصطناعي
        prompt = f"المستخدم يسأل: {user_text}\nأنت مساعد ذكي لمكتب سفريات (مكتب أبو مجد الحداد للسفريات)، أجب على هذا السؤال بطريقة مهنية، دقيقة، ومفصلة باللغة العربية."
        response = model.generate_content(prompt)
        
        # إرسال الإجابة إلى تليجرام
        await update.message.reply_text(response.text)
    except Exception as e:
        # طباعة الخطأ في السجلات وإرسال رسالة للمستخدم
        print(f"Error details: {e}")
        await update.message.reply_text(f"عذراً، حدث خطأ أثناء معالجة الطلب.\nتفاصيل الخطأ: {str(e)}")

# --- 6. التشغيل الرئيسي ---
if __name__ == '__main__':
    print("جاري تشغيل بوت أبو مجد للسفريات...")
    
    # بناء التطبيق
    application = ApplicationBuilder().token(TOKEN).build()
    
    # ربط الرسائل بالدوال
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    
    # بدء العمل
    application.run_polling()

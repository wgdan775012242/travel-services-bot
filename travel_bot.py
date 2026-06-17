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

# --- 2. حل مشكلة المنافذ في Render ---
# نفتح خادم ويب داخلي مدمج لضمان استقرار الخدمة
def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    Handler = http.server.SimpleHTTPRequestHandler
    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            print(f"Server dynamic port {port} is open and stable.")
            httpd.serve_forever()
    except Exception as e:
        print(f"Note on server thread: {e}")

# تشغيل خادم المنفذ في الخلفية بشكل منفصل
server_thread = threading.Thread(target=run_dummy_server, daemon=True)
server_thread.start()

# --- 3. إعداد المفاتيح ---
# نجلب توكن تليجرام من Render كالمعتاد
TOKEN = os.environ.get("TOKEN")
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد للسفريات، كيف يمكنني مساعدتك اليوم؟')

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    try:
        # صياغة توجيهية للذكاء الاصطناعي للرد باسم مكتبك
        prompt = f"المستخدم يسأل: {user_text}\nأنت مساعد ذكي لمكتب سفريات (مكتب أبو مجد الحداد للسفريات)، أجب على هذا السؤال بطريقة مهنية، دقيقة، ومفصلة باللغة العربية."
        response = model.generate_content(prompt)
        
        # إرسال الإجابة إلى تليجرام
        await update.message.reply_text(response.text)
    except Exception as e:
        # إذا حدث خطأ، سيظهر لك السبب بوضوح
        print(f"Error encountered: {e}")
        await update.message.reply_text(f"عذراً، حدث خطأ في الاتصال بالذكاء الاصطناعي.\nتفاصيل الخطأ: {str(e)}")

# --- 6. نقطة التشغيل الرئيسية للبوت ---
if __name__ == '__main__':
    print("...جاري تشغيل البوت")
    
    # بناء التطبيق واستدعاء التوكن
    application = ApplicationBuilder().token(TOKEN).build()
    
    # ربط الأوامر والرسائل النصية بالدوال
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    
    # بدء استقبال الرسائل
    application.run_polling()

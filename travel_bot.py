import os
import json
import urllib.request
import logging
import threading
import http.server
import socketserver
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- إعداد السجلات ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- خادم المنافذ الوهمي لـ Render ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    Handler = http.server.SimpleHTTPRequestHandler
    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            print(f"Server dynamic port {port} is open and stable.")
            httpd.serve_forever()
    except Exception as e:
        pass

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- المفاتيح من Render ---
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# --- دالة الاتصال المباشر بـ Gemini (بدون مكتبات جوجل القديمة) ---
def ask_gemini_direct(user_message):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    prompt = f"المستخدم يسأل: {user_message}\nأنت مساعد ذكي لمكتب سفريات (مكتب أبو مجد الحداد للسفريات)، أجب على هذا السؤال بطريقة مهنية، دقيقة، ومفصلة باللغة العربية."
    
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"عذراً، هناك مشكلة فنية في الاتصال بالذكاء الاصطناعي.\nالتفاصيل: {str(e)}"

# --- دوال تليجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد للسفريات، كيف يمكنني مساعدتك اليوم؟')

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    # جلب الرد من الدالة المباشرة
    response_text = ask_gemini_direct(user_text)
    await update.message.reply_text(response_text)

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    print("...جاري تشغيل البوت بنشاط")
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    
    application.run_polling()

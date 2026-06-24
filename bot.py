import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# الإعدادات
TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")
PORT = int(os.environ.get("PORT", 8080)) # Render يحدد المنفذ هنا

# إعداد Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def start(update, context):
    await update.message.reply_text("أهلاً بك في مكتب أبو مجد الحداد!")

async def ai_reply(update, context):
    user_message = update.message.text
    try:
        response = model.generate_content(f"أنت مساعد مكتب أبو مجد الحداد. أجب: {user_message}")
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text("عذراً، حدث خطأ.")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))

    # هذا السطر هو الحل! هو الذي يشغل سيرفر ويب داخلي ليبقى البوت متصلاً
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    )

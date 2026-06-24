import os
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# الإعدادات
TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 8080))

# إعداد Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك في مكتب أبو مجد الحداد. كيف يمكنني مساعدتك؟")

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    try:
        response = model.generate_content(f"أنت مساعد مكتب أبو مجد الحداد. أجب: {user_message}")
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("عذراً، حدث خطأ في الاتصال.")

async def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))

    if RENDER_URL:
        # وضع الإنتاج (Render)
        await application.bot.set_webhook(f"{RENDER_URL}/webhook")
        # لا نحتاج لـ Flask لأن البوت سيعمل كـ Webhook
        print("Bot running in Webhook mode")
    else:
        # وضع التطوير (محلي)
        print("Bot running in Polling mode")
        await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())

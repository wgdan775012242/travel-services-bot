import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# جلب المفاتيح من إعدادات المنصة (Environment Variables)
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# إعداد Gemini
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد للسفريات، كيف يمكنني مساعدتك اليوم؟')

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    try:
        response = model.generate_content(f"أنت مساعد لمكتب سفريات، أجب على هذا السؤال بطريقة مهنية: {user_text}")
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text("عذراً، حدث خطأ في الرد، يرجى المحاولة لاحقاً.")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), ai_reply))
    print("Bot is running...")
    application.run_polling()
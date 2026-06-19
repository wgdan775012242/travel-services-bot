import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات الأساسية ---
# يسحب التوكن من إعدادات Render (يجب إضافته في Environment Variables)
TOKEN = os.environ.get("BOT_TOKEN", "8808798356:AAGZMTkXTEd3POomQSSgU74YWYUT-4Yo-8U")

# يسحب المنفذ (Port) تلقائياً من Render
PORT = int(os.environ.get("PORT", "10000"))

# رابط تطبيقك الثابت على Render
RENDER_URL = "https://travel-services-bot-1.onrender.com"

# --- دوال البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رد البوت عند إرسال /start"""
    await update.message.reply_text("أهلاً بك! بوت خدمات السفر والتوظيف يعمل الآن بنظام Webhook مستقر 🚀")

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رد البوت على أي رسالة نصية أخرى"""
    text = update.message.text
    await update.message.reply_text(f"استلمت رسالتك: {text}\n(يمكنك لاحقاً ربط هذه الدالة بسكربتات التوظيف)")

# --- الوظيفة الرئيسية ---
def main():
    # بناء تطبيق البوت
    application = Application.builder().token(TOKEN).build()

    # إضافة الأوامر والرسائل
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    # تشغيل البوت عبر Webhook المدمج (الحل الجذري لـ Render)
    print("جاري تشغيل البوت عبر Webhook...")
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{RENDER_URL}/webhook"
    )

if __name__ == '__main__':
    main()


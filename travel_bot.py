import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import google.generativeai as genai

# --- إعداد السجلات ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- المتغيرات البيئية ---
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# --- إعداد سيرفر وهمي (Flask) لمنع توقف Render ---
flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return "Bot is running successfully!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# --- إعداد Gemini ---
if API_KEY:
    genai.configure(api_key=API_KEY)
    # نستخدم الموديل 1.5 لأنه أسرع وأكثر استقراراً
    model = genai.GenerativeModel('gemini-pro')


# --- الردود المحلية السريعة (تطبع فوراً بدون الذكاء الاصطناعي) ---
LOCAL_RESPONSES = {
    "رقم": "📞 رقم التواصل المباشر مع مكتب أبو مجد الحداد هو: +967775012242",
    "تواصل": "يمكنك التواصل معنا عبر:\n- هاتف/واتساب: +967775012242\n- البريد: what775012242@outlook.sa",
    "موقع": "نحن نعمل إلكترونياً ونقدم خدماتنا في استخراج التأشيرات وحجوزات الطيران أينما كنت. تواصل معنا عبر الواتساب.",
    "سعر": "الأسعار تعتمد على نوع الخدمة والوقت. يرجى التواصل معنا عبر الواتساب على +967775012242 لمعرفة التفاصيل بدقة."
}

# --- التوجيهات الأساسية للذكاء الاصطناعي ---
SYSTEM_PROMPT = """
معلومات مكتب أبو مجد الحداد للسفريات:
- الهاتف: 967775012242+
- البريد: what775012242@outlook.sa
- التخصص: تأشيرات العمل من اليمن إلى السعودية، وحجوزات الطيران.

تعليماتك:
1. أنت تمثل خدمة عملاء مكتب أبو مجد الحداد.
2. أجب باحترافية، ولطف، واختصار.
3. إذا سأل المستخدم خارج مجالات السفر أو التأشيرات، اعتذر بلباقة.
4. لا تخمن أسعاراً أبداً. اطلب من العميل التواصل عبر الواتساب للاستفسار عن الأسعار.
"""

# --- دالة الاتصال بـ Gemini ---
def fetch_gemini_response(user_text):
    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\nسؤال العميل: {user_text}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        # سيقوم البوت بإرجاع الخطأ التقني هنا لتعرف أنت كمطور أين الخلل
        return f"عذراً، حدث خطأ تقني أثناء الاتصال بالذكاء الاصطناعي:\n`{str(e)}`\n\nيرجى التواصل معنا مؤقتاً عبر: +967775012242"

# --- دوال تليجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "أهلاً بك في مكتب أبو مجد الحداد للسفريات! ✈️\n\n"
        "أنا المساعد الآلي للمكتب، متواجد لخدمتك في استفسارات تأشيرات العمل وحجوزات الطيران.\n\n"
        "يرجى اختيار إحدى الخدمات من القائمة أو كتابة استفسارك مباشرة:"
    )
    
    # 1. أزرار القائمة الشفافة (Inline Keyboard)
    inline_keyboard = [
        [InlineKeyboardButton("🛂 تأشيرات العمل (يمن - سعودية)", callback_data='visa')],
        [InlineKeyboardButton("✈️ حجوزات الطيران", callback_data='flight'), 
         InlineKeyboardButton("📞 تواصل معنا", callback_data='contact')]
    ]
    reply_markup_inline = InlineKeyboardMarkup(inline_keyboard)

    # 2. أزرار لوحة المفاتيح السفلية (Reply Keyboard)
    reply_keyboard = [
        [KeyboardButton("أرقام التواصل"), KeyboardButton("مواعيد العمل")]
    ]
    reply_markup_bottom = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    # إرسال الترحيب مع الأزرار
    await update.message.reply_text(welcome_text, reply_markup=reply_markup_inline)
    await update.message.reply_text("أو استخدم الأزرار السريعة بالأسفل 👇", reply_markup=reply_markup_bottom)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع ضغطات الأزرار الشفافة"""
    query = update.callback_query
    await query.answer() # ضروري لكي لا يعلق زر التليجرام
    
    if query.data == 'visa':
        text = "🛂 نحن متخصصون في استخراج وتسهيل تأشيرات العمل من اليمن إلى المملكة العربية السعودية. يرجى تجهيز أوراقك والتواصل معنا عبر الواتساب للبدء في الإجراءات."
    elif query.data == 'flight':
        text = "✈️ نوفر حجوزات طيران لأغلب الوجهات العالمية بأفضل الأسعار. يرجى تزويدنا بوجهة السفر وتاريخ الرحلة وسنقوم بخدمتك."
    elif query.data == 'contact':
        text = "📞 للتواصل المباشر مع مكتب أبو مجد الحداد:\n- واتساب/هاتف: +967775012242\n- بريد إلكتروني: what775012242@outlook.sa"
    
    # تعديل الرسالة لتعرض الرد
    await query.edit_message_text(text=text)

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    if not user_message:
        return

    # 1. البحث في الردود الخاصة بالكيبورد السفلي
    if user_message == "أرقام التواصل":
        await update.message.reply_text("📞 هاتف/واتساب: +967775012242")
        return
    elif user_message == "مواعيد العمل":
        await update.message.reply_text("نعمل على مدار الأسبوع لخدمتكم. اترك رسالتك وسنرد في أقرب وقت متاح.")
        return

    # 2. البحث في الكلمات المفتاحية (الردود المحلية السريعة)
    for key, reply in LOCAL_RESPONSES.items():
        if key in user_message:
            await update.message.reply_text(reply)
            return

    # 3. إظهار حالة "جاري الكتابة..." ليعلم المستخدم أن البوت يعمل
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # 4. إرسال الطلب لـ Gemini بشكل منفصل (async) لتجنب توقف السيرفر
    ai_response = await asyncio.to_thread(fetch_gemini_response, user_message)

    # 5. إرسال الرد للمستخدم
    await update.message.reply_text(ai_response)

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    if not TOKEN:
        logger.error("خطأ: يرجى التأكد من إضافة TOKEN في متغيرات البيئة")
    elif not API_KEY:
        logger.error("خطأ: يرجى التأكد من إضافة API_KEY في متغيرات البيئة")
    else:
        # 1. تشغيل السيرفر الوهمي في خلفية الكود
        Thread(target=run_flask, daemon=True).start()
        logger.info("تم تشغيل السيرفر الوهمي بنجاح...")

        # 2. تشغيل تطبيق البوت
        application = ApplicationBuilder().token(TOKEN).build()
        
        # إضافة معالجات الأوامر والرسائل
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler)) # معالج الأزرار الشفافة
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
        
        logger.info("البوت يعمل الآن باحترافية ويستمع للرسائل...")
        application.run_polling()

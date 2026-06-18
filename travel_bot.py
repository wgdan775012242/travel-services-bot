import os
import json
import urllib.request
import urllib.error
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- إعداد السجلات ---
logging.basicConfig(level=logging.INFO)

# --- المفاتيح من Render ---
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# --- معلومات المكتب الشاملة ---
OFFICE_INFO = """
معلومات مكتب أبو مجد الحداد للسفريات:
- الهاتف والواتساب: 967775012242+
- البريد الإلكتروني: what775012242@outlook.sa
- فيسبوك: ابومجد الحداد خدمات سفريات وسياحه
- إنستغرام: وجدان الحداد-ابومجدالحداد
- الخدمات: تأشيرات، حجوزات طيران، خدمات سياحية، وسفر.
"""

# --- دالة الاتصال المباشر بـ Gemini ---
def ask_gemini_direct(user_message):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
    prompt = f"{OFFICE_INFO}\nالمستخدم يسأل: {user_message}\nبصفتك المساعد الذكي لمكتب أبو مجد الحداد، أجب بأسلوب مهني، دقيق، ومرحب باللغة العربية."
    
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['candidates'][0]['content']['parts'][0]['text']
            
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return "عذراً، هناك ضغط كبير من الرسائل حالياً. يرجى الانتظار دقيقة ثم المحاولة مجدداً."
        return f"عذراً، الخدمة تواجه مشكلة فنية. يرجى التواصل معنا مباشرة على الواتساب: 967775012242+"
        
    except Exception as e:
        logging.error(f"خطأ في الاتصال: {e}")
        return "عذراً، الخدمة غير متاحة مؤقتاً، نسعد بتواصلك معنا عبر الرقم: 967775012242+"

# --- دوال تليجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('أهلاً بك في مكتب أبو مجد الحداد للسفريات! أنا مساعدك الذكي، كيف يمكنني خدمتك اليوم؟')

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. إظهار حالة "جاري الكتابة..." للزبون
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # 2. الانتظار ثانيتين لتخفيف الضغط على سيرفرات جوجل (تجنب خطأ 429)
    await asyncio.sleep(2)
    
    # 3. جلب الرد من الذكاء الاصطناعي وإرساله
    response = ask_gemini_direct(update.message.text)
    await update.message.reply_text(response)

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    if not TOKEN or not API_KEY:
        print("خطأ: يرجى التأكد من إضافة TOKEN و API_KEY في إعدادات Render.")
    else:
        print("... البوت يعمل الآن ويستمع للرسائل بنجاح ...")
        application = ApplicationBuilder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
        
        application.run_polling()
        tmux

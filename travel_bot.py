import os
import json
import asyncio
import logging
from threading import Thread
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import urllib.request
import time
from asyncio import Semaphore

# ====================== إعدادات Logging ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("API_KEY")

# ====================== Flask ======================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Bot is running successfully! | مكتب أبو مجد الحداد"

# ====================== Gemini API ======================
async def ask_gemini(user_message: str, max_retries: int = 5) -> str:
    if not GEMINI_API_KEY:
        return "خطأ في الإعدادات. يرجى التواصل مع الإدارة."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    OFFICE_INFO = """
معلومات مكتب أبو مجد الحداد للسفريات:
- الهاتف: +967775012242
- البريد: what775012242@outlook.sa
- التخصص: تأشيرات العمل من اليمن إلى السعودية، حجوزات طيران، خدمات سياحية.
"""

    SYSTEM_PROMPT = f"""
{OFFICE_INFO}
أنت مساعد ذكي محترف لمكتب أبو مجد الحداد. 
أجب بلباقة واحترافية. ركز على خدمات السفر والتأشيرات والسياحة.
إذا كان السؤال خارج نطاق عملنا، اعتذر بلباقة واقترح التواصل المباشر.
"""

    full_prompt = f"{SYSTEM_PROMPT}\n\nالرسالة من العميل: {user_message}"

    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.75,
            "maxOutputTokens": 1000,
            "topP": 0.95,
        }
    }

    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url=url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=35) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['candidates'][0]['content']['parts'][0]['text'].strip()

        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"Gemini attempt {attempt+1}/{max_retries} failed: {e}")

            if "429" in error_str or "resourceexhausted" in error_str or "quota" in error_str:
                wait = (2 ** attempt) * 2
                logger.warning(f"Rate limit → waiting {wait} seconds")
                await asyncio.sleep(wait)
                continue
            elif attempt == max_retries - 1:
                return "عذراً، الخدمة تعاني من ضغط عالي حالياً.\nيرجى التواصل مباشرة على: +967775012242"
            else:
                await asyncio.sleep(1.5)

    return "حدث خطأ غير متوقع. يرجى المحاولة لاحقاً أو الاتصال على +967775012242"


# ====================== Telegram Handlers =====================

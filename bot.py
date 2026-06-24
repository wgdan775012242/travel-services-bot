import logging
import asyncio
import traceback
from telegram import Update, Bot
from telegram.ext import ContextTypes

# تأكد من تعريف المتغيرات التالية في بداية ملفك (أو في ملف الإعدادات)
# TOKEN = "your_token_here"
# ADMIN_CHAT_ID = "your_admin_id"
# model = your_gemini_model_instance

# إعداد الـ Logger
logger = logging.getLogger(__name__)

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Defensive checks
    try:
        user_message = getattr(update.message, 'text', '') if update and update.message else ''
    except Exception:
        user_message = ''

    # تسجيل وصول الرسالة
    logger.info('Received message from %s: %s', update.effective_user.id if update and update.effective_user else 'unknown', user_message)

    resp = None
    text = None
    
    try:
        if 'model' in globals() and model:
            # استدعاء Gemini
            maybe = model.generate_content(f"أنت مساعد مكتب أبو مجد الحداد. أجب: {user_message}")
            if asyncio.iscoroutine(maybe):
                resp = await maybe
            else:
                resp = maybe

            # استخراج النص من استجابة النموذج
            extractors = [
                lambda r: getattr(r, 'text', None),
                lambda r: (r.candidates[0].text if getattr(r, 'candidates', None) and len(r.candidates) > 0 else None),
                lambda r: (r.output[0].content[0].text if getattr(r, 'output', None) and len(r.output) > 0 else None),
                lambda r: (r.result[0].content[0].text if getattr(r, 'result', None) and len(r.result) > 0 else None),
                lambda r: getattr(r, 'content', None),
            ]

            for fn in extractors:
                try:
                    val = fn(resp)
                    if val:
                        text = val
                        break
                except Exception:
                    continue

            # Fallback في حال فشل الاستخراج
            if not text:
                try:
                    text = str(resp)
                except Exception:
                    text = None

        else:
            text = 'خدمة الذكاء الاصطناعي غير مفعلة حالياً. تواصل مع المطوّر.'

        if not text:
            text = 'آسف، لا أستطيع الوصول إلى خدمة الذكاء الاصطناعي حالياً. حاول مرة أخرى لاحقاً.'

        await update.message.reply_text(text)

    except Exception as e:
        # تسجيل الخطأ
        tb = traceback.format_exc()
        logger.error('Exception in ai_reply: %s', e)
        logger.error('Traceback:\n%s', tb)
        
        try:
            await update.message.reply_text('عذراً، حدث خطأ أثناء معالجة رسالتك. تواصل على الرقم +967775012242.')
        except Exception:
            logger.exception('Failed to send error message to user')

        # إرسال إشعار للمشرف (تأكد من تعريف ADMIN_CHAT_ID و TOKEN)
        if 'ADMIN_CHAT_ID' in globals() and 'TOKEN' in globals() and ADMIN_CHAT_ID:
            try:
                bot = Bot(token=TOKEN)
                notify_text = f"Bot error for user {update.effective_user.id if update and update.effective_user else 'unknown'}:\n{str(e)}"
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=notify_text)
            except Exception:
                logger.exception('Failed to notify admin about the error')

async def ai_reply(update: Update, context):
    # Defensive checks
    try:
        user_message = getattr(update.message, 'text', '') if update and update.message else ''
    except Exception:
        user_message = ''

    logger.info('Received message from %s: %s', update.effective_user.id if update and update.effective_user else 'unknown', user_message)

    resp = None
    text = None
    try:
        if model:
            # Call Gemini; support coroutine responses
            maybe = model.generate_content(f"أنت مساعد مكتب أبو مجد الحداد. أجب: {user_message}")
            if asyncio.iscoroutine(maybe):
                resp = await maybe
            else:
                resp = maybe

            # Try multiple extraction strategies
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

            # Fallback to stringifying
            if not text:
                try:
                    text = str(resp)
                except Exception:
                    text = None

        else:
            text = 'خدمة الذكاء الاصطناعي غير مفعلة حالياً. تواصل مع المطوّر.'

        if not text:
            # final fallback
            text = 'آسف، لا أستطيع الوصول إلى خدمة الذكاء الاصطناعي حالياً. حاول مرة أخرى لاحقاً.'

        await update.message.reply_text(text)

    except Exception as e:
        # Log full traceback and debug info
        tb = traceback.format_exc()
        logger.error('Exception in ai_reply: %s', e)
        logger.error('Traceback:\n%s', tb)
        try:
            # Log update object for debugging (may be large)
            logger.debug('Update object: %s', update)
            if resp is not None:
                logger.debug('AI response object: %s', resp)
        except Exception:
            logger.exception('Failed to log debug info')

        # Send a friendly message to the user
        try:
            await update.message.reply_text('عذراً، حدث خطأ أثناء معالجة رسالتك.')
        except Exception:
            logger.exception('Failed to send error message to user')

        # Optionally notify admin if ADMIN_CHAT_ID is set
        if ADMIN_CHAT_ID:
            try:
                from telegram import Bot
                bot = Bot(token=TOKEN)
                notify_text = f"Bot error for user {update.effective_user.id if update and update.effective_user else 'unknown'}:\n{str(e)}\nSee logs for traceback."
                bot.send_message(chat_id=ADMIN_CHAT_ID, text=notify_text)
            except Exception:
                logger.exception('Failed to notify admin about the error')

import os
import requests
from flask import Flask, request, abort, jsonify

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEHOOK_SECRET = os.environ.get("TELEHOOK_SECRET")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

TELEGRAM_API = lambda: f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

if not TELEGRAM_TOKEN:
    app.logger.warning("TELEGRAM_TOKEN is not set. The bot will not be able to send messages.")
if not OPENAI_API_KEY:
    app.logger.warning("OPENAI_API_KEY is not set. The bot will not be able to generate AI replies.")

SYSTEM_PROMPT_AR = (
    "أنت مساعد محترف لخدمات السفر. تجاوب على استفسارات العملاء بأسلوب مهني، ودود، ومباشر. إذا كتب المستخدم بالعربية، اجب بالعربية. "
    "اختصر الإجابات وكن واضحاً. لا تعرض أو تخترع معلومات اتصال أو روابط غير مؤكدة."
)

SYSTEM_PROMPT_EN = (
    "You are a professional travel services assistant. Reply concisely and helpfully. If the user writes in Arabic, reply in Arabic. "
    "Do not fabricate contact details or unverified links. Be polite and correct."
)


def guess_user_language(text: str) -> str:
    # simple heuristic: detect Arabic characters
    if any("\u0600" <= ch <= "\u06FF" for ch in text):
        return "ar"
    return "en"


def generate_reply_with_openai(user_text: str) -> str:
    if not OPENAI_API_KEY:
        return "عذراً، لم يتم ضبط مزود الذكاء الصناعي. الرجاء إعلام المسؤول." if guess_user_language(user_text) == "ar" else "OpenAI API key not configured."

    system_prompt = SYSTEM_PROMPT_AR if guess_user_language(user_text) == "ar" else SYSTEM_PROMPT_EN

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": 500,
        "temperature": 0.2,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # safe access
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        app.logger.exception("OpenAI request failed")
        if guess_user_language(user_text) == "ar":
            return "عذراً، حدث خطأ داخلي أثناء توليد الرد. حاول مرة أخرى لاحقاً."
        return "Sorry, an error occurred generating the reply. Please try again later."


@app.route("/webhook", methods=["POST"]) 
def webhook():
    # Verify Telegram secret token header if configured
    header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if TELEHOOK_SECRET and header != TELEHOOK_SECRET:
        app.logger.warning("Forbidden: invalid secret token")
        abort(403)

    update = request.get_json(force=True)
    app.logger.info("Received update: %s", update)

    # handle only message text updates for now
    message = update.get("message") or update.get("edited_message")
    if not message:
        return jsonify({"ok": True})

    text = message.get("text")
    if not text:
        # ignore non-text messages for now
        return jsonify({"ok": True})

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    if not chat_id:
        return jsonify({"ok": True})

    # generate AI reply
    reply_text = generate_reply_with_openai(text)

    # send reply back via Telegram
    if TELEGRAM_TOKEN:
        send_url = f"{TELEGRAM_API()}/sendMessage"
        payload = {"chat_id": chat_id, "text": reply_text}
        try:
            r = requests.post(send_url, json=payload, timeout=10)
            r.raise_for_status()
        except Exception:
            app.logger.exception("Failed to send message to Telegram")

    return jsonify({"ok": True})


@app.route("/healthz", methods=["GET"]) 
def healthz():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

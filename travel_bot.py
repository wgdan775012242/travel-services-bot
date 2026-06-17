import os
import json
import time
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

# جلب المفاتيح البيئية من Render
TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")

# 1. خادم ويب مصغر مدمج بدون مكتبات خارجية لإرضاء Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write("البوت يعمل بنجاح وبدون مشاكل!".encode('utf-8'))
    def log_message(self, format, *args):
        pass # لإبقاء السجلات نظيفة

def start_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"تم تشغيل خادم المنافذ على المنفذ: {port}")
    server.serve_forever()

Thread(target=start_server, daemon=True).start()

# 2. دالة الاتصال بذكاء Gemini (إصدار 1.5 الفعال)
def ask_gemini(user_message):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    prompt = f"المستخدم يسأل: {user_message}\nأنت مساعد ذكي لمكتب سفريات (مكتب أبو مجد الحداد للسفريات)، أجب على هذا السؤال بطريقة مهنية، دقيقة، ومفصلة باللغة العربية."
    
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"عذراً، واجه السيرفر مشكلة في الاتصال بالذكاء الاصطناعي: {e}"

# 3. دالة إرسال الرسائل إلى تليجرام
def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode('utf-8')
    try:
        urllib.request.urlopen(url, data=data)
    except Exception as e:
        print(f"خطأ في إرسال الرسالة: {e}")

# 4. الحلقة الأساسية لاستقبال وتصريف الرسائل (Polling)
def main_polling():
    offset = 0
    print("بدء استقبال الرسائل من تليجرام...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=30"
            with urllib.request.urlopen(url, timeout=35) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        offset = update["update_id"] + 1
                        if "message" in update and "text" in update["message"]:
                            chat_id = update["message"]["chat"]["id"]
                            user_text = update["message"]["text"]
                            
                            if user_text.startswith("/start"):
                                send_telegram_message(chat_id, 'أهلاً بك في مكتب أبو مجد الحداد للسفريات، كيف يمكنني مساعدتك اليوم؟')
                            else:
                                # جلب الرد من جيميني وإرساله
                                bot_response = ask_gemini(user_text)
                                send_telegram_message(chat_id, bot_response)
        except Exception as e:
            print(f"جاري إبقاء الاتصال نشطاً: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main_polling()

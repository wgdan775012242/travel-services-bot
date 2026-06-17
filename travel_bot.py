# --- دالة الاتصال المباشر بـ Gemini (محدثة مع بيانات المكتب) ---
def ask_gemini_direct(user_message):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    # هنا أضفنا معلومات مكتبك لتكون جزءاً من تعليمات الذكاء الاصطناعي
    office_info = """
    معلومات مكتب أبو مجد الحداد للسفريات:
    - الهاتف: 967775012242+
    - البريد الإلكتروني: what775012242@outlook.sa
    - فيسبوك: ابومجد الحداد خدمات سفريات وسياحه
    - إنستغرام: وجدان الحداد-ابومجدالحداد
    - الخدمات: تأشيرات، حجوزات طيران، خدمات سياحية.
    """
    
    prompt = f"{office_info}\nالمستخدم يسأل: {user_message}\nبصفتك المساعد الذكي لمكتب أبو مجد الحداد، أجب على هذا السؤال بناءً على المعلومات المذكورة أعلاه وبطريقة مهنية ومفصلة باللغة العربية."
    
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"عذراً، هناك مشكلة فنية في الاتصال بالذكاء الاصطناعي.\nالتفاصيل: {str(e)}"

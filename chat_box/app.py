from flask import Flask, request, jsonify, render_template
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
app = Flask(__name__)

# ✅ Đặt API KEY ở đây (bảo mật hơn: có thể dùng biến môi trường)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# Dữ liệu mặc định
today = datetime.now()
tomorrow = today + timedelta(days=1)

@app.route('/')
def index():
    default_data = {
        'departure_date': today.strftime('%Y-%m-%d'),
        'return_date': tomorrow.strftime('%Y-%m-%d'),
        'passenger_adults': 1,
        'passenger_children': 0,
        'passenger_infants': 0,
        'seat_class': [
            {'value': 'ECO', 'label': 'Hạng phổ thông'},
            {'value': 'BUS', 'label': 'Hạng thương gia'}
        ],
        'is_round_trip': True
    }
    return render_template("homepage.html", san_bay=[], default_data=default_data, api_url="", user_info="")

@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_message = data.get("message", "")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [{
            "parts": [{"text": user_message}]
        }]
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        result = response.json()

        # ✅ Lấy kết quả trả về
        reply_text = result['candidates'][0]['content']['parts'][0]['text'] if 'candidates' in result else "Xin lỗi, tôi không thể phản hồi."
        return jsonify({"reply": reply_text})

    except Exception as e:
        print("Gemini API Error:", e)
        return jsonify({"reply": "Lỗi hệ thống: không thể kết nối đến Gemini."})

if __name__ == '__main__':
    app.run(debug=True)

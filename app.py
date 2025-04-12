from flask import Flask, render_template, request, jsonify
import requests
import uuid
import re

app = Flask(__name__)

@app.route('/customer')
def customer():
    return render_template('customer.html')

@app.route('/send_message', methods=['POST'])
def handle_message():
    user_msg = request.form.get('message', '')
    unique_id = str(uuid.uuid4())
    
    # নেকো সাইটে রিকোয়েস্ট পাঠানো
    api_url = f"https://nekosite.ddns.net/ai?q={user_msg}&id={unique_id}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        ai_response = data.get('response', '')
        
        # রেসপন্স প্রসেসিং
        processed_html = process_ai_response(ai_response)
        return jsonify({'html': processed_html})
        
    except Exception as e:
        return jsonify({'html': f'Error: {str(e)}'})

def process_ai_response(text):
    # এইচটিএমএল কোড ব্লক প্রসেসিং
    code_blocks = re.findall(r'```html(.*?)```', text, re.DOTALL)
    text_parts = re.split(r'```html.*?```', text, flags=re.DOTALL)
    
    processed = []
    for i, part in enumerate(text_parts):
        part = part.strip()
        if part:
            # মার্কডাউন ফরম্যাটিং
            part = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', part)
            part = re.sub(r'\*(.*?)\*', r'<i>\1</i>', part)
            processed.append(part)
        if i < len(code_blocks):
            # কোড ব্লক যোগ করুন
            code = code_blocks[i].strip()
            processed.append(f'<div class="code-output">{code}</div>')
    
    return ''.join(processed)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

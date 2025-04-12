from flask import Flask, render_template, request, jsonify
import requests
import uuid
import re
import html

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
    # Process code blocks first
    processed_text = process_code_blocks(text)
    
    # Process bullet points with bold text
    processed_text = process_bullet_bold(processed_text)
    
    # Process bold text
    processed_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', processed_text)
    
    # Process italic text
    processed_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', processed_text)
    
    return processed_text

def process_code_blocks(text):
    # Process HTML code blocks with copy functionality
    def replace_html_code(match):
        code = match.group(1).strip()
        return f'''
        <div class="code-container">
            <div class="tooltip" id="tooltip-{uuid.uuid4()}">Copied!</div>
            <button class="copy-icon" onclick="copyCode('tooltip-{uuid.uuid4()}', this)" aria-label="Copy Code">
                <svg xmlns="http://www.w3.org/2000/svg" height="20" width="20" viewBox="0 0 24 24">
                    <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v16c0 
                    1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 18H8V7h11v16z"/>
                </svg>
            </button>
            <pre>{html.escape(code)}</pre>
        </div>
        '''
    
    # Process all code blocks (```html and ```)
    text = re.sub(r'```html(.*?)```', replace_html_code, text, flags=re.DOTALL)
    text = re.sub(r'```(.*?)```', replace_html_code, text, flags=re.DOTALL)
    
    return text

def process_bullet_bold(text):
    # Process bullet points with bold text (* **text**)
    def replace_bullet_bold(match):
        return f'<li><b>{match.group(1)}</b></li>'
    
    return re.sub(r'\*\s+\*\*(.*?)\*\*', replace_bullet_bold, text)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

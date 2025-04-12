# App.py
from flask import Flask, render_template, request, jsonify, session
import requests
import uuid
import re
import html

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a real secret key

@app.route('/customer')
def customer():
    # Generate a persistent UUID for the session if not exists
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return render_template('customer.html')

@app.route('/send_message', methods=['POST'])
def handle_message():
    user_msg = request.form.get('message', '')

    # Use the persistent session ID
    user_id = session.get('user_id', str(uuid.uuid4()))

    api_url = f"https://nekosite.ddns.net/ai?q={user_msg}&id={user_id}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        ai_response = data.get('response', '')

        processed_html = process_ai_response(ai_response)
        return jsonify({'html': processed_html})

    except Exception as e:
        return jsonify({'html': f'Error: {str(e)}'})

def process_ai_response(text):
    # Split text into parts while preserving code blocks
    parts = re.split(r'(```[\s\S]*?```)', text)
    processed_parts = []

    for part in parts:
        if part.startswith('```') and part.endswith('```'):
            # Process code blocks
            lang_match = re.match(r'```(\w+)?', part)
            language = lang_match.group(1) if lang_match else ''
            code_content = part[len(language)+3:-3].strip()

            processed_parts.append(format_code_block(code_content, language))
        else:
            # Process normal text
            processed_parts.append(format_text(part))

    return ''.join(processed_parts)

def format_code_block(code, language=''):
    escaped_code = html.escape(code)
    language_class = f'language-{language}' if language else ''

    return f'''
    <div class="code-container">
        <pre class="{language_class}"><code>{escaped_code}</code></pre>
    </div>
    '''

def format_text(text):
    # Process bullet points with bold text
    text = re.sub(r'\*\s+\*\*(.*?)\*\*', r'<li><b>\1</b></li>', text)
    # Process bold text
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Process italic text
    text = re.sub(r'\*(?!\s)(.*?)\*', r'<i>\1</i>', text)
    # Convert line breaks to <br>
    text = text.replace('\n', '<br>')
    # Replace remaining single asterisks with bullet points
    text = re.sub(r'\*(?!\*)', '•', text)
    return text

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    

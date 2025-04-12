from flask import Flask, render_template, request, jsonify, session
import requests
import uuid
import re
import html
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a real secret key
HISTORY_FILE = 'history.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_history(history_data):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history_data, f, indent=4)

@app.route('/customer')
def customer():
    user_id = session.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id

    chat_id = session.get('chat_id')
    if not chat_id:
        chat_id = str(uuid.uuid4())
        session['chat_id'] = chat_id

    history_data = load_history()
    user_history = history_data.get(user_id, {})
    current_chat_history = user_history.get(chat_id, [])

    return render_template('customer.html', history=current_chat_history, chat_id=chat_id)

@app.route('/new_chat')
def new_chat():
    session.pop('chat_id', None)
    return jsonify({'redirect': '/customer'})

@app.route('/get_history_list')
def get_history_list():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not identified'}), 401

    history_data = load_history()
    user_history = history_data.get(user_id, {})
    history_list = [{"chat_id": chat_id, "last_message": history[-1].get('text', '')[:50] + '...' if history else 'New Chat'}
                    for chat_id, history in user_history.items()]
    return jsonify(history_list)

@app.route('/load_history/<chat_id>')
def load_history_by_id(chat_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not identified'}), 401

    session['chat_id'] = chat_id
    history_data = load_history()
    user_history = history_data.get(user_id, {})
    current_chat_history = user_history.get(chat_id, [])
    return jsonify({'history': current_chat_history})

@app.route('/send_message', methods=['POST'])
def handle_message():
    user_msg = request.form.get('message', '')
    user_id = session.get('user_id')
    chat_id = session.get('chat_id')

    if not user_id or not chat_id:
        return jsonify({'html': 'Error: User or chat session not identified.'})

    api_url = f"https://nekosite.ddns.net/ai?q={user_msg}&id={user_id}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        ai_response = data.get('response', '')

        processed_html = process_ai_response(ai_response)

        history_data = load_history()
        if user_id not in history_data:
            history_data[user_id] = {}
        if chat_id not in history_data[user_id]:
            history_data[user_id][chat_id] = []

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history_data[user_id][chat_id].append({'sender': 'user', 'text': user_msg, 'timestamp': timestamp})
        history_data[user_id][chat_id].append({'sender': 'bot', 'html': processed_html, 'timestamp': timestamp})
        save_history(history_data)

        return jsonify({'html': processed_html})

    except Exception as e:
        return jsonify({'html': f'Error: {str(e)}'})

def process_ai_response(text):
    parts = re.split(r'(```[\s\S]*?```)', text)
    processed_parts = []

    for part in parts:
        if part.startswith('```') and part.endswith('```'):
            lang_match = re.match(r'```(\w+)?', part)
            language = lang_match.group(1) if lang_match else ''
            code_content = part[len(language)+3:-3].strip()
            processed_parts.append(format_code_block(code_content, language))
        else:
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
    text = re.sub(r'\*\s+\*\*(.*?)\*\*', r'<li><b>\1</b></li>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(?!\s)(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'\*', '•', text)  # Replace remaining asterisks with bullets
    text = text.replace('\n', '<br>')
    return text

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    

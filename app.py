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
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

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

@app.route('/')
def index():
    return redirect('/customer')

@app.route('/customer')
def customer():
    # Initialize user session
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session['current_chat'] = str(uuid.uuid4())
    
    # Initialize user in history
    history = load_history()
    user_id = session['user_id']
    if user_id not in history:
        history[user_id] = {}
    
    # Initialize new chat if needed
    chat_id = session['current_chat']
    if chat_id not in history[user_id]:
        history[user_id][chat_id] = {
            'created_at': datetime.now().isoformat(),
            'messages': []
        }
        save_history(history)
    
    return render_template('customer.html')

@app.route('/get_current_chat')
def get_current_chat():
    history = load_history()
    user_id = session.get('user_id')
    chat_id = session.get('current_chat')
    
    if not user_id or not chat_id:
        return jsonify({'error': 'Session not initialized'}), 400
    
    messages = history.get(user_id, {}).get(chat_id, {}).get('messages', [])
    return jsonify({
        'chat_id': chat_id,
        'messages': messages
    })

@app.route('/new_chat', methods=['POST'])
def new_chat():
    history = load_history()
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User not identified'}), 400
    
    new_chat_id = str(uuid.uuid4())
    session['current_chat'] = new_chat_id
    
    history[user_id][new_chat_id] = {
        'created_at': datetime.now().isoformat(),
        'messages': []
    }
    save_history(history)
    
    return jsonify({
        'success': True,
        'chat_id': new_chat_id
    })

@app.route('/get_history')
def get_history():
    history = load_history()
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User not identified'}), 400
    
    return jsonify(history.get(user_id, {}))

@app.route('/load_chat/<chat_id>')
def load_chat(chat_id):
    history = load_history()
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User not identified'}), 400
    
    if chat_id not in history.get(user_id, {}):
        return jsonify({'error': 'Chat not found'}), 404
    
    session['current_chat'] = chat_id
    messages = history[user_id][chat_id].get('messages', [])
    
    return jsonify({
        'success': True,
        'messages': messages
    })

@app.route('/send_message', methods=['POST'])
def handle_message():
    user_msg = request.form.get('message', '')
    chat_id = request.form.get('chat_id', '')
    user_id = session.get('user_id')
    
    if not user_id or not chat_id:
        return jsonify({'error': 'Session not initialized'}), 400
    
    # Save user message
    history = load_history()
    if user_id not in history or chat_id not in history[user_id]:
        return jsonify({'error': 'Chat not found'}), 404
    
    # Add user message to history
    history[user_id][chat_id]['messages'].append({
        'sender': 'user',
        'content': user_msg,
        'timestamp': datetime.now().isoformat()
    })
    
    # Call AI API
    api_url = f"https://nekosite.ddns.net/ai?q={user_msg}&id={user_id}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        ai_response = data.get('response', '')
        
        # Process AI response
        processed_html = process_ai_response(ai_response)
        
        # Save AI response to history
        history[user_id][chat_id]['messages'].append({
            'sender': 'bot',
            'content': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
        save_history(history)
        
        return jsonify({'html': processed_html})
        
    except Exception as e:
        # Save error message to history
        history[user_id][chat_id]['messages'].append({
            'sender': 'bot',
            'content': f'Error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        })
        save_history(history)
        
        return jsonify({'html': f'Error: {str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

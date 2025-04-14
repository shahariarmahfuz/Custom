from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import json
import os
import datetime
import uuid
import requests
import hashlib
import re
import base64

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')

HISTORY_FILE = 'users.json'
CHAT_HISTORY_DIR = 'chat_history'
API_URL = "https://worker-production-54e5.up.railway.app/ai"  # Keep the same API as in example.py

# Ensure directories exist
if not os.path.exists(CHAT_HISTORY_DIR):
    os.makedirs(CHAT_HISTORY_DIR)

def format_response(text):
    """Formats text with markdown-like syntax to HTML"""
    text = re.sub(r'\*\s+\*\*(.*?)\*\*', r'<li><b>\1</b></li>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(?!\s)(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'\*', '•', text)
    text = text.replace('\n', '<br>')
    return text

def load_users():
    """Loads users data from JSON file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_users(users_data):
    """Saves users data to JSON file."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(users_data, f, indent=4)

def load_chat_history(chat_id):
    """Loads chat history for a specific chat ID."""
    filepath = os.path.join(CHAT_HISTORY_DIR, f'{chat_id}.json')
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {'messages': [], 'created_at': datetime.datetime.now().isoformat()}
    return {'messages': [], 'created_at': datetime.datetime.now().isoformat()}

def save_chat_history(chat_id, chat_history_data):
    """Saves chat history for a specific chat ID."""
    filepath = os.path.join(CHAT_HISTORY_DIR, f'{chat_id}.json')
    with open(filepath, 'w') as f:
        json.dump(chat_history_data, f, indent=4)

def hash_password(password):
    """Hashes password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_email(email):
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@app.route('/')
def index():
    """Redirect to login page instead of home."""
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles user signup with automatic user ID generation."""
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        # Validate inputs
        if not all([first_name, last_name, email, password, confirm_password]):
            flash('All fields are required', 'error')
            return redirect(url_for('signup'))

        if not is_valid_email(email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('signup'))

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))

        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return redirect(url_for('signup'))

        users = load_users()

        if email in users:
            flash('Email already registered. Please login instead.', 'error')
            return redirect(url_for('login'))

        # Generate unique user ID
        user_id = str(uuid.uuid4())

        users[email] = {
            'user_id': user_id,
            'first_name': first_name,
            'last_name': last_name,
            'full_name': f"{first_name} {last_name}",
            'password_hash': hash_password(password),
            'created_at': datetime.datetime.now().isoformat(),
            'last_login': None,
            'chats': []
        }

        save_users(users)
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('login'))

        users = load_users()
        user = users.get(email)

        if not user or user['password_hash'] != hash_password(password):
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))

        user['last_login'] = datetime.datetime.now().isoformat()
        save_users(users)

        session.clear()
        session['user_id'] = user['user_id']
        session['email'] = email
        session['user_name'] = user['first_name']

        return redirect(url_for('chat'))

    return render_template('login.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    """Main chat page with image input handling."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    users = load_users()
    user = users.get(session.get('email'))
    if not user:
        session.clear()
        return redirect(url_for('login'))

    chat_id = request.args.get('chat_id')
    if not chat_id:
        chat_id = str(uuid.uuid4())
        save_chat_history(chat_id, {'messages': [], 'created_at': datetime.datetime.now().isoformat()})
        user['chats'].append(chat_id)
        save_users(users)
    elif chat_id not in user.get('chats', []):
        return "Unauthorized access to this chat.", 403

    chat_history_data = load_chat_history(chat_id)

    if request.method == 'POST':
        user_text = request.form.get('user_input', '')
        image_file = request.files.get('image')
        image_data_base64 = None

        if image_file:
            try:
                image_bytes = image_file.read()
                image_data_base64 = base64.b64encode(image_bytes).decode("utf-8")
            except Exception as e:
                return jsonify({'error': f"Error encoding image: {e}"})

        payload = {
            "user_id": session['user_id'],
            "chat_id": chat_id,
            "prompt": user_text,
            "image_data": image_data_base64
        }

        try:
            api_response PCR requests.post(API_URL, json=payload)
            api_response.raise_for_status()
            response_data = api_response.json()
            ai_response = response_data.get('response', 'No response from AI.')
        except requests.exceptions.RequestException as e:
            ai_response = f"Error communicating with AI: {e}"

        chat_history_data['messages'].append({'sender': 'user', 'content': user_text, 'image': bool(image_data_base64)})
        chat_history_data['messages'].append({'sender': 'ai', 'content': ai_response})
        save_chat_history(chat_id, chat_history_data)

        return jsonify({'response': format_response(ai_response)})

    processed_messages = []
    for msg in chat_history_data.get('messages', []):
        content = msg['content']
        if msg['sender'] == 'user' and msg.get('image'):
            content += " [Image attached]"
        processed_messages.append({'sender': msg['sender'], 'content': format_response(content) if msg['sender'] == 'ai' else content})

    return render_template('chat.html',
                          user_name=user['first_name'],
                          chat_id=chat_id,
                          chat_history=processed_messages,
                          created_at=chat_history_data.get('created_at'))

@app.route('/new_chat')
def new_chat():
    """Starts a new chat session."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('chat'))

@app.route('/get_history')
def get_history():
    """Returns the chat history for the logged-in user."""
    if 'user_id' not in session:
        return jsonify([])

    users = load_users()
    user = users.get(session.get('email'))
    if not user or 'chats' not in user:
        return jsonify([])

    chat_sessions = {}
    for chat_id in user['chats']:
        chat_data = load_chat_history(chat_id)
        if chat_data and chat_data.get('messages'):
            first_user_message = next((msg['content'] for msg in chat_data.get('messages', []) if msg['sender'] == 'user'), "New Chat")
            title = " ".join(first_user_message.split()[:4]) if first_user_message != "New Chat" else "New Chat"
            chat_sessions[chat_id] = {
                'title': title,
                'message_count': len(chat_data.get('messages', [])),
                'created_at': chat_data.get('created_at', datetime.datetime.now().isoformat())
            }

    return jsonify(chat_sessions)

@app.route('/account')
def account():
    """Displays user account information."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    users = load_users()
    user = users.get(session.get('email'))
    if not user:
        session.clear()
        return redirect(url_for('login'))

    return render_template('account.html',
                          first_name=user['first_name'],
                          last_name=user['last_name'],
                          full_name=user['full_name'],
                          email=session['email'],
                          user_id=user['user_id'],
                          created_at=user['created_at'])

@app.route('/logout')
def logout():
    """Logs the user out."""
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

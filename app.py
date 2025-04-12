from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import json
import os
import datetime
import uuid
import requests
import hashlib
import re
import html  # Import the html module

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')

HISTORY_FILE = 'users.json'
CHAT_HISTORY_DIR = 'chat_history'

# Ensure directories exist
if not os.path.exists(CHAT_HISTORY_DIR):
    os.makedirs(CHAT_HISTORY_DIR)

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
def home():
    """Home page with login/signup options."""
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles user signup."""
    # ... (rest of the signup route remains the same)
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

        # Check if email already exists
        if email in users:
            flash('Email already registered. Please login instead.', 'error')
            return redirect(url_for('login'))

        # Generate unique user ID
        user_id = str(uuid.uuid4())

        # Create user account
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
    # ... (rest of the login route remains the same)
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('login'))

        users = load_users()
        user = users.get(email)

        if not user:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))

        if user['password_hash'] != hash_password(password):
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))

        # Update last login time
        user['last_login'] = datetime.datetime.now().isoformat()
        save_users(users)

        # Set session
        session.clear()
        session['user_id'] = user['user_id']
        session['email'] = email
        session['user_name'] = user['first_name']

        return redirect(url_for('chat'))

    return render_template('login.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    """Main chat page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    users = load_users()
    user = users.get(session.get('email'))
    if not user:
        session.clear()
        return redirect(url_for('login'))

    user_name = user['first_name']
    chat_id = request.args.get('chat_id')
    chat_history_data = {'messages': [], 'created_at': datetime.datetime.now().isoformat()}
    is_existing_chat = False

    if chat_id:
        if chat_id in user['chats']:
            chat_history_data = load_chat_history(chat_id)
            is_existing_chat = True
        else:
            return "Unauthorized access to this chat.", 403

    if not chat_id:
        chat_id = str(uuid.uuid4())
        chat_history_data['created_at'] = datetime.datetime.now().isoformat()

    if request.method == 'POST':
        user_text = request.form['user_input']
        current_chat_id = request.form['chat_id']

        # Send message to AI API
        api_url = f"[https://nekosite.ddns.net/ai?q=](https://nekosite.ddns.net/ai?q=){user_text}&id={current_chat_id}"
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            ai_response_data = response.json()
            ai_response = ai_response_data.get('response', 'No response from AI.')
            # Format the AI response
            formatted_ai_response = process_ai_response(ai_response)
        except requests.exceptions.RequestException as e:
            formatted_ai_response = f"Error communicating with AI: {e}"

        # Save chat history
        updated_chat_history_data = load_chat_history(current_chat_id)
        if not updated_chat_history_data.get('messages'):
            updated_chat_history_data['messages'] = []

        updated_chat_history_data['messages'].append({'sender': 'user', 'content': user_text})
        updated_chat_history_data['messages'].append({'sender': 'ai', 'content': formatted_ai_response})
        save_chat_history(current_chat_id, updated_chat_history_data)

        # If this is the first message in a new chat, save the chat ID to user's history
        if not is_existing_chat and updated_chat_history_data['messages']:
            users = load_users()
            if session['email'] in users:
                if 'chats' not in users[session['email']]:
                    users[session['email']]['chats'] = [current_chat_id]
                else:
                    if current_chat_id not in users[session['email']]['chats']:
                        users[session['email']]['chats'].append(current_chat_id)
                save_users(users)

        return jsonify({'response': formatted_ai_response})

    return render_template('chat_combined.html',
                         user_name=user_name,
                         chat_id=chat_id,
                         chat_history=chat_history_data.get('messages', []),
                         created_at=chat_history_data.get('created_at'))

@app.route('/new_chat')
def new_chat():
    """Redirects to a new chat session."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('chat'))

@app.route('/get_history')
def get_history():
    """Returns the chat history for the logged-in user as JSON."""
    if 'user_id' not in session:
        return jsonify([])

    users = load_users()
    user = users.get(session.get('email'))
    if not user or 'chats' not in user:
        return jsonify([])

    chat_sessions = {}
    for chat_id in user['chats']:
        filepath = os.path.join(CHAT_HISTORY_DIR, f'{chat_id}.json')
        if os.path.exists(filepath):
            chat_data = load_chat_history(chat_id)
            if chat_data and chat_data.get('messages'):
                first_user_message = next((msg['content'] for msg in chat_data.get('messages', []) if msg['sender'] == 'user'), None)
                title = "New Chat"
                if first_user_message:
                    title_words = first_user_message.split()[:4]
                    title = " ".join(title_words)
                chat_sessions[chat_id] = {
                    'title': title,
                    'message_count': len(chat_data.get('messages', [])),
                    'created_at': chat_data.get('created_at', datetime.datetime.now().isoformat())
                }

    return jsonify(chat_sessions)

@app.route('/account')
def account():
    """Displays the user's account information."""
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
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    

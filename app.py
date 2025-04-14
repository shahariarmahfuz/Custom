from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import base64
import requests
import uuid
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Configuration
API_URL = "https://worker-production-54e5.up.railway.app/ai"
USERS_FILE = 'users.json'
CHATS_DIR = 'chat_history'

# Ensure directories exist
os.makedirs(CHATS_DIR, exist_ok=True)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_chat(chat_id):
    file_path = os.path.join(CHATS_DIR, f'{chat_id}.json')
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {'messages': [], 'created_at': datetime.now().isoformat()}
    return {'messages': [], 'created_at': datetime.now().isoformat()}

def save_chat(chat_id, chat_data):
    file_path = os.path.join(CHATS_DIR, f'{chat_id}.json')
    with open(file_path, 'w') as f:
        json.dump(chat_data, f, indent=4)

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()

        users = load_users()

        # Create new user if doesn't exist
        if username not in users:
            user_id = str(uuid.uuid4())
            users[username] = {
                'user_id': user_id,
                'chats': [],
                'created_at': datetime.now().isoformat()
            }
            save_users(users)

        # Set session
        session['user_id'] = users[username]['user_id']
        session['username'] = username
        return redirect(url_for('chat'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    users = load_users()
    username = session['username']
    user_data = users[username]

    # Get or create chat_id
    chat_id = request.args.get('chat_id')
    if not chat_id:
        chat_id = str(uuid.uuid4())
        return redirect(url_for('chat', chat_id=chat_id))

    # Load chat history
    chat_history = load_chat(chat_id)

    # Add to user's chats if new
    if chat_id not in user_data['chats']:
        user_data['chats'].append(chat_id)
        save_users(users)

    if request.method == 'POST':
        # Handle AJAX request for chat
        prompt = request.form.get('prompt')
        image_file = request.files.get('image')
        image_data_base64 = None

        if image_file:
            try:
                image_bytes = image_file.read()
                image_data_base64 = base64.b64encode(image_bytes).decode('utf-8')
            except Exception as e:
                return jsonify({'error': f'Image processing error: {str(e)}'}), 400

        # Add user message to history
        chat_history['messages'].append({
            'sender': 'user',
            'content': prompt,
            'image': image_data_base64,
            'timestamp': datetime.now().isoformat()
        })

        # Call API - Using chat_id instead of user_id
        payload = {
            "chat_id": chat_id,
            "prompt": prompt,
            "image_data": image_data_base64
        }

        try:
            api_response = requests.post(API_URL, json=payload)
            api_response.raise_for_status()
            response_data = api_response.json()

            # Add AI response to history
            chat_history['messages'].append({
                'sender': 'ai',
                'content': response_data.get('response', ''),
                'timestamp': datetime.now().isoformat()
            })

            save_chat(chat_id, chat_history)
            return jsonify(response_data)

        except requests.exceptions.RequestException as e:
            return jsonify({'error': str(e)}), 500

    return render_template('chat.html',
                         username=username,
                         chat_id=chat_id,
                         messages=chat_history['messages'])

@app.route('/history')
def get_history():
    if 'user_id' not in session:
        return jsonify([])

    users = load_users()
    username = session['username']
    user_data = users[username]

    history = []
    for chat_id in user_data['chats']:
        chat_data = load_chat(chat_id)
        if chat_data['messages']:
            first_message = chat_data['messages'][0]['content']
            title = first_message[:30] + '...' if len(first_message) > 30 else first_message
        else:
            title = 'New Chat'

        history.append({
            'chat_id': chat_id,
            'title': title,
            'created_at': chat_data['created_at'],
            'last_activity': chat_data['messages'][-1]['timestamp'] if chat_data['messages'] else chat_data['created_at']
        })

    return jsonify(history)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    

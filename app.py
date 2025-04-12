# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import json
import os
import datetime
import uuid
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Important for session management

HISTORY_FILE = 'history.json'
CHAT_HISTORY_DIR = 'chat_history'

# Ensure chat history directory exists
if not os.path.exists(CHAT_HISTORY_DIR):
    os.makedirs(CHAT_HISTORY_DIR)

def load_history():
    """Loads user history from the JSON file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_history(history_data):
    """Saves user history to the JSON file."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history_data, f, indent=4)

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

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handles the initial login page."""
    if request.method == 'POST':
        name = request.form['name']
        user_id = request.form['user_id']
        history_data = load_history()
        if user_id not in history_data:
            history_data[user_id] = {'name': name, 'full_name': name, 'last_login': datetime.datetime.now().isoformat(), 'chats': []}
        else:
            history_data[user_id]['last_login'] = datetime.datetime.now().isoformat()
            if 'full_name' not in history_data[user_id]:
                history_data[user_id]['full_name'] = history_data[user_id].get('name')
        save_history(history_data)
        session['user_id'] = user_id
        return redirect(url_for('chat'))
    return render_template('index.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    """Handles the main chat page."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))

    history_data = load_history()
    user_info = history_data.get(user_id)
    if not user_info:
        return redirect(url_for('index'))

    user_name = user_info['name']
    chat_id = request.args.get('chat_id')
    chat_history_data = {'messages': [], 'created_at': datetime.datetime.now().isoformat()}
    is_existing_chat = False

    if chat_id:
        if user_id in history_data and 'chats' in history_data[user_id] and chat_id in history_data[user_id]['chats']:
            chat_history_data = load_chat_history(chat_id)
            is_existing_chat = True
        else:
            return render_template('unauthorized.html', message="You are not authorized to access this chat.")
    else:
        chat_id = str(uuid.uuid4()) # Generate a new chat ID
        chat_history_data['created_at'] = datetime.datetime.now().isoformat()

    if request.method == 'POST':
        user_text = request.form['user_input']
        current_chat_id = request.form['chat_id']

        # Security check for POST requests as well
        if current_chat_id:
            if user_id not in history_data or 'chats' not in history_data[user_id] or current_chat_id not in history_data[user_id]['chats']:
                return jsonify({'error': 'Unauthorized access'}), 403

        # Send message to AI API
        api_url = f"https://nekosite.ddns.net/ai?q={user_text}&id={current_chat_id}"
        try:
            response = requests.get(api_url)
            response.raise_for_status()  # Raise an exception for bad status codes
            ai_response_data = response.json()
            ai_response = ai_response_data.get('response', 'No response from AI.')
        except requests.exceptions.RequestException as e:
            ai_response = f"Error communicating with AI: {e}"

        # Save chat history
        updated_chat_history_data = load_chat_history(current_chat_id)
        if not updated_chat_history_data.get('messages'):
            updated_chat_history_data['messages'] = []
        updated_chat_history_data['messages'].append({'sender': 'user', 'content': user_text})
        updated_chat_history_data['messages'].append({'sender': 'ai', 'content': ai_response})
        save_chat_history(current_chat_id, updated_chat_history_data)

        # If this is the first message in a new chat, save the chat ID to history
        if not is_existing_chat and updated_chat_history_data['messages']:
            history_data = load_history()
            if user_id in history_data:
                if 'chats' not in history_data[user_id]:
                    history_data[user_id]['chats'] = [current_chat_id]
                else:
                    if current_chat_id not in history_data[user_id]['chats']:
                        history_data[user_id]['chats'].append(current_chat_id)
                save_history(history_data)

        return jsonify({'response': ai_response}) # Changed to match expected response in JS

    return render_template('chat_combined.html', user_name=user_name, chat_id=chat_id, chat_history=chat_history_data.get('messages', []), created_at=chat_history_data.get('created_at'))

@app.route('/new_chat')
def new_chat():
    """Redirects to a new chat session."""
    return redirect(url_for('chat'))

@app.route('/get_history')
def get_history():
    """Returns the chat history for the logged-in user as JSON."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])

    history_data = load_history()
    user_info = history_data.get(user_id)
    if not user_info or 'chats' not in user_info:
        return jsonify([])

    chat_sessions = {}
    for chat_id in user_info['chats']:
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
    """Displays the user's account information and logout option."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))

    history_data = load_history()
    user_info = history_data.get(user_id)
    if not user_info:
        return redirect(url_for('index'))

    name = user_info.get('name')
    full_name = user_info.get('full_name')
    user_id_display = user_id

    return render_template('account.html', name=name, full_name=full_name, user_id=user_id_display)

@app.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.pop('user_id', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

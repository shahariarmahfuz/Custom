from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
import datetime
import uuid
import requests

app = Flask(__name__)

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
                return []
    return []

def save_chat_history(chat_id, chat_history):
    """Saves chat history for a specific chat ID."""
    filepath = os.path.join(CHAT_HISTORY_DIR, f'{chat_id}.json')
    with open(filepath, 'w') as f:
        json.dump(chat_history, f, indent=4)

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handles the initial login page."""
    if request.method == 'POST':
        name = request.form['name']
        user_id = request.form['user_id']
        history_data = load_history()
        history_data[user_id] = {'name': name, 'last_login': datetime.datetime.now().isoformat()}
        save_history(history_data)
        return redirect(url_for('chat'))
    return render_template('index.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    """Handles the main chat page."""
    history_data = load_history()
    if not history_data:
        return redirect(url_for('index'))  # Redirect if no user is logged in

    user_id = list(history_data.keys())[0] # Assuming only one user for simplicity in this example
    user_name = history_data[user_id]['name']

    if request.method == 'POST':
        user_text = request.form['user_input']
        chat_id = request.form['chat_id']

        # Send message to AI API
        api_url = f"https://nekosite.ddns.net/ai?q={user_text}&id={chat_id}"
        try:
            response = requests.get(api_url)
            response.raise_for_status()  # Raise an exception for bad status codes
            ai_response_data = response.json()
            ai_response = ai_response_data.get('response', 'No response from AI.')
        except requests.exceptions.RequestException as e:
            ai_response = f"Error communicating with AI: {e}"

        # Save chat history
        chat_history = load_chat_history(chat_id)
        chat_history.append({'user': user_text, 'ai': ai_response})
        save_chat_history(chat_id, chat_history)

        return jsonify({'user': user_text, 'ai': ai_response})

    # Initial load or new chat
    chat_id = request.args.get('chat_id')
    chat_history = []
    if not chat_id:
        chat_id = str(uuid.uuid4()) # Generate a new chat ID
    else:
        chat_history = load_chat_history(chat_id)

    return render_template('chat.html', user_name=user_name, chat_id=chat_id, chat_history=chat_history)

@app.route('/new_chat')
def new_chat():
    """Redirects to a new chat session."""
    return redirect(url_for('chat'))

@app.route('/history')
def history():
    """Displays the chat history sidebar."""
    history_data = load_history()
    if not history_data:
        return "No user logged in." # Handle this better in a real app

    user_id = list(history_data.keys())[0]
    chat_files = [f for f in os.listdir(CHAT_HISTORY_DIR) if f.endswith('.json')]
    chat_sessions = []
    for filename in chat_files:
        chat_id = filename[:-5]
        # You might want to store some metadata about each chat session
        # (e.g., timestamp of first message) to display in the sidebar.
        # For now, we'll just show the chat ID.
        chat_sessions.append({'id': chat_id})

    return render_template('history.html', chat_sessions=chat_sessions)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    

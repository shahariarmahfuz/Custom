from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import base64
import requests
import json
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Important for session management

API_URL = "https://worker-production-54e5.up.railway.app/ai"
HISTORY_FILE = "history.json"

def load_history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

def save_history(history_data):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history_data, f, indent=4)

def generate_chat_id():
    return str(uuid.uuid4())

@app.route("/", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    user_id = request.form.get("user_id")
    user_name = request.form.get("user_name")
    if user_id and user_name:
        session['user_id'] = user_id
        session['user_name'] = user_name
        chat_id = generate_chat_id()
        return redirect(url_for('chat', chat_id=chat_id))
    else:
        return render_template("login.html", error="Please enter both User ID and Name.")

@app.route("/chat/<chat_id>", methods=["GET", "POST"])
def chat(chat_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    response_data = None
    error_message = None
    history_data = load_history()
    chat_history = history_data.get(user_id, {}).get(chat_id, [])

    if request.method == "POST":
        prompt = request.form.get("prompt")
        image_file = request.files.get("image")
        image_data_base64 = None

        if image_file:
            try:
                image_bytes = image_file.read()
                image_data_base64 = base64.b64encode(image_bytes).decode("utf-8")
            except Exception as e:
                error_message = f"Error encoding image: {e}"
                return render_template("chat.html", chat_id=chat_id, history=chat_history, error=error_message)

        payload = {
            "user_id": user_id,
            "prompt": prompt,
            "image_data": image_data_base64,
            "chat_id": chat_id
        }

        try:
            api_response = requests.post(API_URL, json=payload)
            api_response.raise_for_status()
            response_data = api_response.json()

            # Save the interaction to history
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user_message = {"type": "user", "text": prompt, "image": image_data_base64, "timestamp": timestamp}
            ai_response = {"type": "ai", "response": response_data.get("response"), "timestamp": timestamp}

            if user_id not in history_data:
                history_data[user_id] = {}
            if chat_id not in history_data[user_id]:
                history_data[user_id][chat_id] = []

            history_data[user_id][chat_id].append(user_message)
            history_data[user_id][chat_id].append(ai_response)
            save_history(history_data)

            # Reload chat history to display the new message
            chat_history = history_data.get(user_id, {}).get(chat_id, [])

        except requests.exceptions.RequestException as e:
            error_message = f"Error sending request to API: {e}"
        except ValueError:
            error_message = "Error decoding API response."

    return render_template("chat.html", chat_id=chat_id, history=chat_history, response=response_data, error=error_message)

@app.route("/history")
def history():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    history_data = load_history()
    user_chats = history_data.get(user_id, {})
    return render_template("history.html", chats=user_chats)

@app.route("/history/<chat_id>", methods=["GET", "POST"])
def view_history(chat_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    history_data = load_history()
    chat_history = history_data.get(user_id, {}).get(chat_id, [])
    response_data = None
    error_message = None

    if request.method == "POST":
        prompt = request.form.get("prompt")
        image_file = request.files.get("image")
        image_data_base64 = None

        if image_file:
            try:
                image_bytes = image_file.read()
                image_data_base64 = base64.b64encode(image_bytes).decode("utf-8")
            except Exception as e:
                error_message = f"Error encoding image: {e}"
                return render_template("view_history.html", chat_id=chat_id, history=chat_history, error=error_message)

        payload = {
            "user_id": user_id,
            "prompt": prompt,
            "image_data": image_data_base64,
            "chat_id": chat_id
        }

        try:
            api_response = requests.post(API_URL, json=payload)
            api_response.raise_for_status()
            response_data = api_response.json()

            # Save the new interaction to history
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user_message = {"type": "user", "text": prompt, "image": image_data_base64, "timestamp": timestamp}
            ai_response = {"type": "ai", "response": response_data.get("response"), "timestamp": timestamp}

            history_data[user_id][chat_id].append(user_message)
            history_data[user_id][chat_id].append(ai_response)
            save_history(history_data)

            # Reload chat history to display the new message
            chat_history = history_data.get(user_id, {}).get(chat_id, [])

        except requests.exceptions.RequestException as e:
            error_message = f"Error sending request to API: {e}"
        except ValueError:
            error_message = "Error decoding API response."

    return render_template("view_history.html", chat_id=chat_id, history=chat_history, response=response_data, error=error_message)

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('login_page'))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
    

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import base64
import requests
import uuid
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure secret key

API_URL = "https://worker-production-54e5.up.railway.app/ai"
HISTORY_FILE = "history.json"

# Initialize history file if it doesn't exist
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w') as f:
        json.dump({}, f)

def save_history(user_id, chat_id, prompt, response, image_data=None):
    with open(HISTORY_FILE, 'r+') as f:
        history = json.load(f)
        
        if user_id not in history:
            history[user_id] = {}
        
        if chat_id not in history[user_id]:
            history[user_id][chat_id] = {
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "messages": []
            }
        
        history[user_id][chat_id]["messages"].append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "prompt": prompt,
            "response": response,
            "image": image_data is not None
        })
        
        f.seek(0)
        json.dump(history, f, indent=2)
        f.truncate()

def get_user_history(user_id):
    with open(HISTORY_FILE, 'r') as f:
        history = json.load(f)
        return history.get(user_id, {})

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        username = request.form.get("username")
        
        if user_id and username:
            session['user_id'] = user_id
            session['username'] = username
            return redirect(url_for('chat'))
    
    return render_template("login.html")

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    chat_id = request.args.get('chat_id', str(uuid.uuid4()))
    response_data = None
    
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
                return render_template("chat.html", error=error_message, chat_id=chat_id)

        payload = {
            "user_id": session['user_id'],
            "prompt": prompt,
            "image_data": image_data_base64
        }

        try:
            api_response = requests.post(API_URL, json=payload)
            api_response.raise_for_status()
            response_data = api_response.json()
            
            # Save to history
            save_history(
                session['user_id'],
                chat_id,
                prompt,
                response_data.get('response', ''),
                image_data_base64
            )
        except requests.exceptions.RequestException as e:
            error_message = f"Error sending request to API: {e}"
            return render_template("chat.html", error=error_message, chat_id=chat_id)
        except ValueError:
            error_message = "Error decoding API response."
            return render_template("chat.html", error=error_message, chat_id=chat_id)

    return render_template("chat.html", response=response_data, chat_id=chat_id)

@app.route("/history")
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_history = get_user_history(session['user_id'])
    return render_template("history.html", history=user_history)

@app.route("/chat/<chat_id>")
def view_chat(chat_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_history = get_user_history(session['user_id'])
    chat_history = user_history.get(chat_id, None)
    
    if not chat_history:
        return redirect(url_for('history'))
    
    return render_template("chat_history.html", chat_id=chat_id, chat_history=chat_history)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

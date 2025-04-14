from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import base64
import requests
import json
import os
from uuid import uuid4

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # সেশনের জন্য সিক্রেট কী

API_URL = "https://worker-production-54e5.up.railway.app/ai"
HISTORY_FILE = 'history.json'

# হিস্টোরি লোড করা
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

# হিস্টোরি সেভ করা
def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        if username:
            session['username'] = username
            return redirect(url_for('index'))
    return render_template("login.html")

@app.route("/", methods=["GET", "POST"])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    history = load_history()
    user_history = history.get(username, {})

    if request.method == "POST":
        prompt = request.form.get("prompt")
        image_file = request.files.get("image")
        chat_id = request.form.get("chat_id", str(uuid4()))  # নতুন চ্যাট আইডি তৈরি
        image_data_base64 = None

        if image_file:
            try:
                image_bytes = image_file.read()
                image_data_base64 = base64.b64encode(image_bytes).decode("utf-8")
            except Exception as e:
                return jsonify({"error": f"Error encoding image: {e}"}), 400

        payload = {
            "user_id": username,
            "prompt": prompt,
            "image_data": image_data_base64,
            "chat_id": chat_id
        }

        try:
            api_response = requests.post(API_URL, json=payload)
            api_response.raise_for_status()
            response_data = api_response.json()
            # হিস্টোরি সেভ করা
            if chat_id not in user_history:
                user_history[chat_id] = []
            user_history[chat_id].append({
                "prompt": prompt,
                "response": response_data["response"]
            })
            history[username] = user_history
            save_history(history)
            return jsonify({"response": response_data["response"], "chat_id": chat_id})
        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Error sending request to API: {e}"}), 500
        except ValueError:
            return jsonify({"error": "Error decoding API response."}), 500

    return render_template("index.html", history=user_history)

@app.route("/history/<chat_id>")
def get_history(chat_id):
    username = session['username']
    history = load_history()
    user_history = history.get(username, {})
    chat_history = user_history.get(chat_id, [])
    return jsonify(chat_history)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

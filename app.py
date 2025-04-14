from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import base64
import requests
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # For session management, replace with a strong secret key

API_URL = "https://worker-production-54e5.up.railway.app/ai"
HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_history(history_data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_data, f, indent=4)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        if username:
            session["username"] = username
            return redirect(url_for("index"))
        return render_template("login.html", error="Please enter a username.")
    return render_template("login.html")

@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    history_data = load_history()
    user_history = history_data.get(username, [])

    if request.method == "POST":
        user_id = username  # Use username as user ID for simplicity
        prompt = request.form.get("prompt")
        image_file = request.files.get("image")
        chat_id = request.form.get("chat_id")  # Get chat_id if it exists
        image_data_base64 = None

        if image_file:
            try:
                image_bytes = image_file.read()
                image_data_base64 = base64.b64encode(image_bytes).decode("utf-8")
            except Exception as e:
                return jsonify({"error": f"Error encoding image: {e}"}), 400

        payload = {
            "user_id": user_id,
            "prompt": prompt,
            "image_data": image_data_base64,
            "chat_id": chat_id  # Send chat_id to the AI API
        }

        try:
            api_response = requests.post(API_URL, json=payload)
            api_response.raise_for_status()
            response_data = api_response.json()
            ai_response = response_data.get("response")

            if ai_response:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if not chat_id:
                    chat_id = str(uuid.uuid4())
                    user_history.append({"chat_id": chat_id, "history": [{"role": "user", "content": prompt, "has_image": bool(image_file)}, {"role": "ai", "content": ai_response, "timestamp": timestamp}]})
                else:
                    for chat in user_history:
                        if chat["chat_id"] == chat_id:
                            chat["history"].append({"role": "user", "content": prompt, "has_image": bool(image_file)})
                            chat["history"].append({"role": "ai", "content": ai_response, "timestamp": timestamp})
                            break

                history_data[username] = user_history
                save_history(history_data)
                return jsonify({"response": ai_response, "chat_id": chat_id})
            else:
                return jsonify({"error": "No 'response' found in API response."}), 500

        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Error sending request to API: {e}"}), 500
        except ValueError:
            return jsonify({"error": "Error decoding API response."}), 500

    return render_template("index.html", history=user_history)

@app.route("/history/<chat_id>")
def load_chat_history(chat_id):
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    history_data = load_history()
    user_history = history_data.get(username, [])

    selected_history = None
    for chat in user_history:
        if chat["chat_id"] == chat_id:
            selected_history = chat["history"]
            break

    return jsonify({"history": selected_history, "chat_id": chat_id})

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
    

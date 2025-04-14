from flask import Flask, render_template, request, jsonify
import base64
import requests

app = Flask(__name__)

API_URL = "https://worker-production-54e5.up.railway.app/ai"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        prompt = request.form.get("prompt")
        image_file = request.files.get("image")
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
            "image_data": image_data_base64
        }

        try:
            api_response = requests.post(API_URL, json=payload)
            api_response.raise_for_status()
            response_data = api_response.json()
            return jsonify({"response": response_data["response"]})
        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Error sending request to API: {e}"}), 500
        except ValueError:
            return jsonify({"error": "Error decoding API response."}), 500

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

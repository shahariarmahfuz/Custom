from flask import Flask, request, render_template, jsonify
import requests
import uuid
import re

app = Flask(__name__)

@app.route('/customer')
def customer_page():
    return render_template('customer.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user_msg = data.get('message')
    if not user_msg:
        return jsonify({"error": "Message is required"}), 400

    unique_id = uuid.uuid4()
    api_url = f"https://nekosite.ddns.net/ai?q={user_msg}&id={unique_id}"

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        api_data = response.json()
        bot_response = api_data.get('response', '')

        # Basic handling for bold and italic tags (can be improved)
        processed_response = bot_response.replace('<b>', '<strong>').replace('</b>', '</strong>')
        processed_response = processed_response.replace('<i>', '<em>').replace('</i>', '</em>')
        processed_response = processed_response.replace('\n', '<br>')
        processed_response = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', processed_response)
        processed_response = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', processed_response)

        return jsonify({"response": processed_response})

    except requests.exceptions.RequestException as e:
        return jsonify({"response": f"Error communicating with the AI service: {e}"}), 500
    except Exception as e:
        return jsonify({"response": f"An unexpected error occurred: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

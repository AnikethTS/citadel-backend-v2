from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import os

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

messages_file = 'messages.json'

def load_messages():
    if os.path.exists(messages_file):
        with open(messages_file, 'r') as f:
            return json.load(f)
    else:
        return []

def save_message(new_message):
    messages = load_messages()
    messages.append(new_message)
    with open(messages_file, 'w') as f:
        json.dump(messages, f, indent=4)

@app.route('/')
def index():
    return "Citadel Messaging Server is Live!"

@app.route('/get_messages', methods=['GET'])
def get_messages():
    return jsonify(load_messages())

@socketio.on('send_message')
def handle_send_message(data):
    save_message(data)
    emit('receive_message', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)

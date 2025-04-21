from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import os

# 🔥 Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, messaging as firebase_messaging

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ✨ Initialize Firebase
cred = credentials.Certificate('/etc/secrets/firebase-admin-key.json')
firebase_admin.initialize_app(cred)

messages_file = 'messages.json'
media_folder = 'media'

# 🔥 Create media folder if doesn't exist
if not os.path.exists(media_folder):
    os.makedirs(media_folder)

def load_messages():
    if os.path.exists(messages_file):
        with open(messages_file, 'r') as f:
            return json.load(f)
    else:
        return []

def save_all_messages(messages):
    with open(messages_file, 'w') as f:
        json.dump(messages, f, indent=4)

def save_message(new_message):
    messages = load_messages()
    messages.append(new_message)
    save_all_messages(messages)

@app.route('/')
def index():
    return "Citadel Messaging Server is Live!"

@app.route('/get_messages', methods=['GET'])
def get_messages():
    return jsonify(load_messages())

@app.route('/upload_media', methods=['POST'])
def upload_media():
    file = request.files.get('file')
    sender = request.form.get('sender')

    if file:
        filepath = os.path.join(media_folder, file.filename)
        file.save(filepath)

        message_entry = {
            "sender": sender,
            "message": "",
            "media": {
                "type": "image" if file.mimetype.startswith('image') else "video",
                "url": f"/media/{file.filename}"
            },
            "time": request.form.get('time')
        }
        save_message(message_entry)

        # Emit new media message to everyone
        socketio.emit('receive_message', message_entry)
        return jsonify({"status": "success", "url": f"/media/{file.filename}"})

    return jsonify({"status": "error", "message": "No file provided"}), 400

# 🔥 Serve uploaded media files
@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(media_folder, filename)

@socketio.on('send_message')
def on_send_message(data):
    save_message(data)
    emit('receive_message', data, broadcast=True)

    try:
        push_message = firebase_messaging.Message(
            notification=firebase_messaging.Notification(
                title=f"New message from {data.get('sender')}",
                body=data.get('message'),
            ),
            topic="citadel-chat",
        )
        response = firebase_messaging.send(push_message)
        print('✅ Successfully sent push notification:', response)
    except Exception as e:
        print('❌ Error sending push notification:', e)

@socketio.on('typing')
def handle_typing(data):
    emit('typing', data, broadcast=True)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    emit('stop_typing', data, broadcast=True)

@socketio.on('edit_message')
def handle_edit_message(data):
    index = data.get('index')
    new_message = data.get('new_message')
    messages = load_messages()
    if 0 <= index < len(messages):
        messages[index]['message'] = new_message
        save_all_messages(messages)
        emit('update_messages', messages, broadcast=True)

@socketio.on('delete_message')
def handle_delete_message(data):
    index = data.get('index')
    messages = load_messages()
    if 0 <= index < len(messages):
        del messages[index]
        save_all_messages(messages)
        emit('update_messages', messages, broadcast=True)

# ✅ Call Related Handlers
@socketio.on('call_user')
def handle_call_user(data):
    print(f"📞 {data.get('from')} is calling {data.get('to')}")
    emit('incoming_call', data, broadcast=True)

@socketio.on('accept_call')
def handle_accept_call(data):
    print(f"✅ {data.get('from')} accepted call from {data.get('to')}")
    emit('call_accepted', data, broadcast=True)

@socketio.on('reject_call')
def handle_reject_call(data):
    print(f"❌ {data.get('from')} rejected call from {data.get('to')}")
    emit('call_rejected', data, broadcast=True)

# ✅ Future (WebRTC)
@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    emit('webrtc_offer', data, broadcast=True)

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    emit('webrtc_answer', data, broadcast=True)

@socketio.on('webrtc_ice_candidate')
def handle_webrtc_ice_candidate(data):
    emit('webrtc_ice_candidate', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)

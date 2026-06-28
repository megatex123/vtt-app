import os
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
VOICE_MODEL_URL = os.environ.get('VOICE_MODEL_URL', 'http://localhost:5555')
PORT = int(os.environ.get('PORT', 3000))


@app.get('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.get('/<path:filename>')
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.post('/api/transcribe')
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file. Send a file under the key "audio".'}), 400

    audio_file = request.files['audio']

    try:
        resp = requests.post(
            f'{VOICE_MODEL_URL}/inference',
            files={'audio': (audio_file.filename, audio_file.stream, audio_file.mimetype)},
            timeout=60,
        )
        return (resp.content, resp.status_code, {'Content-Type': 'application/json'})
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Voice model server unavailable. Start voice-model-server in pm2.'}), 503
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Voice model server timed out (>60 s).'}), 504


@app.get('/health')
def health():
    return jsonify({'status': 'ok', 'port': PORT, 'voice_model_url': VOICE_MODEL_URL})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)

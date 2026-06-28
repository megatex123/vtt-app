import os
import sys
import tempfile

from flask import Flask, request, jsonify

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from inference import transcribe

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'}
PORT = 5555


@app.post('/inference')
def inference():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided. Send a file under the key "audio".'}), 400

    audio_file = request.files['audio']
    if not audio_file.filename:
        return jsonify({'error': 'Empty filename.'}), 400

    ext = os.path.splitext(audio_file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'Unsupported format "{ext}". Allowed: {sorted(ALLOWED_EXTENSIONS)}'}), 415

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        text = transcribe(tmp_path)
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        os.unlink(tmp_path)


@app.get('/health')
def health():
    return jsonify({'status': 'ok', 'port': PORT})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)

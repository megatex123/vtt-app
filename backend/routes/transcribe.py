import os
import tempfile
import logging

from flask import Blueprint, request, jsonify

import transcriber
import database
from telegram import notify_transcription_done, notify_transcription_error

log = logging.getLogger(__name__)

transcribe_bp = Blueprint('transcribe', __name__)

ALLOWED_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.webm', '.ogg'}


@transcribe_bp.post('/transcribe')
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file. Send a file under the key "audio".'}), 400

    audio_file = request.files['audio']

    if not audio_file.filename:
        return jsonify({'error': 'Empty filename.'}), 400

    ext = os.path.splitext(audio_file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            'error': f'Unsupported format "{ext}". Allowed: {sorted(ALLOWED_EXTENSIONS)}'
        }), 415

    # Reject zero-byte uploads
    audio_file.stream.seek(0, 2)
    size = audio_file.stream.tell()
    audio_file.stream.seek(0)
    if size == 0:
        return jsonify({'error': 'Audio file is empty.'}), 400

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, dir='/tmp', delete=False) as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name

        result = transcriber.transcribe(tmp_path)

        row_id = database.save_transcription(
            text=result['text'],
            duration=result['duration_seconds'],
            model_used=result['model_used'],
            language=result['language'],
            confidence=result['confidence'],
        )

        notify_transcription_done(
            text=result['text'],
            model_used=result['model_used'],
            duration=result['duration_seconds'],
        )

        return jsonify({
            'id':         row_id,
            'text':       result['text'],
            'duration':   result['duration_seconds'],
            'model_used': result['model_used'],
            'language':   result['language'],
        })

    except Exception as exc:
        log.exception('[transcribe] Error during transcription')
        notify_transcription_error(str(exc))
        return jsonify({'error': str(exc)}), 500

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

"""Tests for POST /api/transcribe."""

import io
from tests.conftest import WAV_BYTES


def _post_audio(client, data, filename, mimetype='audio/wav'):
    return client.post(
        '/api/transcribe',
        data={'audio': (io.BytesIO(data), filename, mimetype)},
        content_type='multipart/form-data',
    )


# ── Happy path ─────────────────────────────────────────────────────────────────

def test_transcribe_valid_wav_returns_200(client):
    resp = _post_audio(client, WAV_BYTES, 'speech.wav')
    assert resp.status_code == 200


def test_transcribe_valid_wav_has_text_field(client):
    resp = _post_audio(client, WAV_BYTES, 'speech.wav')
    body = resp.get_json()
    assert 'text' in body
    assert isinstance(body['text'], str)


def test_transcribe_response_has_expected_fields(client):
    resp = _post_audio(client, WAV_BYTES, 'speech.wav')
    body = resp.get_json()
    for field in ('id', 'text', 'duration', 'model_used', 'language'):
        assert field in body, f"Missing field: {field}"


def test_transcribe_returns_mocked_text(client, mock_transcribe):
    resp = _post_audio(client, WAV_BYTES, 'speech.wav')
    body = resp.get_json()
    assert body['text'] == mock_transcribe['text']


def test_transcribe_id_is_integer(client):
    resp = _post_audio(client, WAV_BYTES, 'speech.wav')
    body = resp.get_json()
    assert isinstance(body['id'], int)
    assert body['id'] >= 1


# ── Validation failures ────────────────────────────────────────────────────────

def test_transcribe_no_file_returns_400(client):
    resp = client.post('/api/transcribe', data={}, content_type='multipart/form-data')
    assert resp.status_code == 400


def test_transcribe_no_file_has_error_field(client):
    resp = client.post('/api/transcribe', data={}, content_type='multipart/form-data')
    body = resp.get_json()
    assert 'error' in body


def test_transcribe_wrong_file_type_returns_415(client):
    resp = _post_audio(client, b'not audio', 'doc.txt', 'text/plain')
    assert resp.status_code == 415


def test_transcribe_wrong_file_type_has_error_field(client):
    resp = _post_audio(client, b'not audio', 'doc.txt', 'text/plain')
    body = resp.get_json()
    assert 'error' in body


def test_transcribe_empty_file_returns_400(client):
    resp = _post_audio(client, b'', 'empty.wav')
    assert resp.status_code == 400


def test_transcribe_empty_file_has_error_field(client):
    resp = _post_audio(client, b'', 'empty.wav')
    body = resp.get_json()
    assert 'error' in body

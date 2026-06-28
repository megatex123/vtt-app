"""
Shared fixtures for vtt-app backend tests.

ML packages (torch, transformers, librosa) are mocked at sys.modules level so
tests run without the full model stack installed.  The mock must happen before
any import that transitively imports those packages.
"""

import io
import os
import struct
import sys
import wave
from unittest.mock import MagicMock

import pytest

# ── Mock heavy ML deps if not installed ────────────────────────────────────────
# Must be at module level so the patches are in place before `import transcriber`
# is triggered by `from app import app` inside fixtures.

for _pkg in ('torch', 'transformers', 'librosa', 'soundfile', 'numpy'):
    try:
        __import__(_pkg)
    except ImportError:
        _m = MagicMock()
        sys.modules[_pkg] = _m
        # Allow `from transformers import WhisperProcessor` etc.
        sys.modules[f'{_pkg}.models'] = _m
        sys.modules[f'{_pkg}.models.whisper'] = _m

# ── Shared test WAV bytes (0.1 s silence, 16kHz mono 16-bit) ──────────────────

def _make_wav() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16_000)
        w.writeframes(struct.pack('<1600h', *([0] * 1600)))
    buf.seek(0)
    return buf.read()


WAV_BYTES = _make_wav()

# ── sys.path: allow `import database`, `import transcriber` from backend/ ─────
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import database  # noqa: E402  (import after sys.path setup)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def test_db_path(tmp_path, monkeypatch):
    """Redirect database.DB_PATH to a temp file and initialise the schema."""
    db_file = str(tmp_path / 'test.db')
    monkeypatch.setattr(database, 'DB_PATH', db_file)
    database.init_db()
    return db_file


@pytest.fixture()
def mock_transcribe(monkeypatch):
    """Patch transcriber.transcribe so no ML model is loaded."""
    import transcriber  # imported here — ML packages already mocked above

    fake_result = {
        'text': 'ujian transkripsi',
        'duration_seconds': 2.5,
        'model_used': 'base',
        'language': 'ms',
        'confidence': 0.92,
    }
    monkeypatch.setattr(transcriber, 'transcribe', MagicMock(return_value=fake_result))
    return fake_result


@pytest.fixture()
def client(test_db_path, mock_transcribe, monkeypatch):
    """
    Flask test client with:
    - test-scoped SQLite DB
    - transcriber.transcribe mocked (no model load)
    - Telegram notifications silenced
    """
    import routes.transcribe as rt

    monkeypatch.setattr(rt, 'notify_transcription_done',  MagicMock())
    monkeypatch.setattr(rt, 'notify_transcription_error', MagicMock())

    from app import app  # noqa: PLC0415

    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

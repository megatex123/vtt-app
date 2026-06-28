"""Tests for database.py functions directly (no Flask client)."""

import database


# ── save_transcription ─────────────────────────────────────────────────────────

def test_save_returns_integer_id(test_db_path):
    row_id = database.save_transcription('hello', 1.0, 'base', 'ms', 0.9)
    assert isinstance(row_id, int)
    assert row_id >= 1


def test_save_id_increments(test_db_path):
    id1 = database.save_transcription('a', 1.0, 'base', 'ms', 0.8)
    id2 = database.save_transcription('b', 2.0, 'base', 'ms', 0.9)
    assert id2 > id1


def test_save_and_retrieve_text(test_db_path):
    database.save_transcription('teks ujian', 1.5, 'fine-tuned', 'ms', 0.95)
    rows = database.get_history(limit=1)
    assert rows[0]['text'] == 'teks ujian'


def test_save_stores_all_fields(test_db_path):
    database.save_transcription('hello', 3.0, 'fine-tuned', 'ms', 0.88)
    row = database.get_history(limit=1)[0]
    assert row['text']             == 'hello'
    assert row['duration_seconds'] == 3.0
    assert row['model_used']       == 'fine-tuned'
    assert row['language']         == 'ms'
    assert abs(row['confidence'] - 0.88) < 1e-6


def test_save_with_none_optional_fields(test_db_path):
    row_id = database.save_transcription('minimal', None, None, None, None)
    assert isinstance(row_id, int)
    row = database.get_history(limit=1)[0]
    assert row['duration_seconds'] is None
    assert row['confidence'] is None


# ── get_history ────────────────────────────────────────────────────────────────

def test_get_history_empty_db_returns_list(test_db_path):
    result = database.get_history()
    assert isinstance(result, list)
    assert result == []


def test_get_history_returns_dicts(test_db_path):
    database.save_transcription('x', 1.0, 'base', 'ms', 0.5)
    rows = database.get_history()
    assert isinstance(rows[0], dict)


def test_get_history_default_limit_50(test_db_path):
    for i in range(60):
        database.save_transcription(f't{i}', 1.0, 'base', 'ms', 0.9)
    rows = database.get_history()  # default limit=50
    assert len(rows) == 50


def test_get_history_custom_limit(test_db_path):
    for i in range(10):
        database.save_transcription(f't{i}', 1.0, 'base', 'ms', 0.9)
    rows = database.get_history(limit=3)
    assert len(rows) == 3


def test_get_history_ordered_newest_first(test_db_path):
    database.save_transcription('first', 1.0, 'base', 'ms', 0.9)
    database.save_transcription('second', 2.0, 'base', 'ms', 0.9)
    rows = database.get_history(limit=2)
    assert rows[0]['text'] == 'second'
    assert rows[1]['text'] == 'first'


def test_get_history_row_has_expected_keys(test_db_path):
    database.save_transcription('k', 1.0, 'base', 'ms', 0.9)
    row = database.get_history(limit=1)[0]
    for key in ('id', 'text', 'timestamp', 'duration_seconds', 'model_used', 'language', 'confidence'):
        assert key in row, f"Missing key: {key}"


# ── get_stats ──────────────────────────────────────────────────────────────────

def test_get_stats_returns_dict(test_db_path):
    result = database.get_stats()
    assert isinstance(result, dict)


def test_get_stats_has_correct_keys(test_db_path):
    stats = database.get_stats()
    assert 'total' in stats
    assert 'avg_duration' in stats
    assert 'most_used_model' in stats


def test_get_stats_empty_db_total_is_zero(test_db_path):
    assert database.get_stats()['total'] == 0


def test_get_stats_empty_db_avg_is_none(test_db_path):
    assert database.get_stats()['avg_duration'] is None


def test_get_stats_total_count(test_db_path):
    for i in range(5):
        database.save_transcription(f't{i}', 1.0, 'base', 'ms', 0.9)
    assert database.get_stats()['total'] == 5


def test_get_stats_avg_duration(test_db_path):
    database.save_transcription('a', 2.0, 'base', 'ms', 0.9)
    database.save_transcription('b', 4.0, 'base', 'ms', 0.9)
    avg = database.get_stats()['avg_duration']
    assert abs(avg - 3.0) < 1e-6


def test_get_stats_most_used_model(test_db_path):
    database.save_transcription('a', 1.0, 'base', 'ms', 0.9)
    database.save_transcription('b', 1.0, 'base', 'ms', 0.9)
    database.save_transcription('c', 1.0, 'fine-tuned', 'ms', 0.9)
    assert database.get_stats()['most_used_model'] == 'base'


# ── delete_transcription ───────────────────────────────────────────────────────

def test_delete_existing_returns_true(test_db_path):
    row_id = database.save_transcription('del me', 1.0, 'base', 'ms', 0.9)
    assert database.delete_transcription(row_id) is True


def test_delete_nonexistent_returns_false(test_db_path):
    assert database.delete_transcription(99999) is False


def test_delete_removes_row(test_db_path):
    row_id = database.save_transcription('gone', 1.0, 'base', 'ms', 0.9)
    database.delete_transcription(row_id)
    remaining = [r['id'] for r in database.get_history()]
    assert row_id not in remaining


def test_delete_does_not_remove_other_rows(test_db_path):
    id1 = database.save_transcription('keep', 1.0, 'base', 'ms', 0.9)
    id2 = database.save_transcription('del',  1.0, 'base', 'ms', 0.9)
    database.delete_transcription(id2)
    remaining = [r['id'] for r in database.get_history()]
    assert id1 in remaining

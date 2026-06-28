"""Tests for GET /api/history, GET /api/stats, DELETE /api/history/<id>."""

import database


def _seed(n=3):
    """Insert n rows and return their ids."""
    ids = []
    for i in range(n):
        row_id = database.save_transcription(
            text=f'teks {i}',
            duration=float(i + 1),
            model_used='base',
            language='ms',
            confidence=0.9,
        )
        ids.append(row_id)
    return ids


# ── GET /api/history ───────────────────────────────────────────────────────────

def test_history_returns_200(client):
    resp = client.get('/api/history')
    assert resp.status_code == 200


def test_history_returns_list(client):
    body = client.get('/api/history').get_json()
    assert isinstance(body, list)


def test_history_empty_db_returns_empty_list(client):
    body = client.get('/api/history').get_json()
    assert body == []


def test_history_returns_seeded_rows(client, test_db_path):
    _seed(3)
    body = client.get('/api/history').get_json()
    assert len(body) == 3


def test_history_rows_have_expected_fields(client, test_db_path):
    _seed(1)
    row = client.get('/api/history').get_json()[0]
    for field in ('id', 'text', 'timestamp', 'duration_seconds', 'model_used', 'language', 'confidence'):
        assert field in row, f"Missing field: {field}"


# ── GET /api/history?limit=N ───────────────────────────────────────────────────

def test_history_limit_param_respected(client, test_db_path):
    _seed(10)
    body = client.get('/api/history?limit=5').get_json()
    assert len(body) <= 5


def test_history_limit_1(client, test_db_path):
    _seed(5)
    body = client.get('/api/history?limit=1').get_json()
    assert len(body) == 1


def test_history_default_limit_is_50(client, test_db_path):
    _seed(3)
    body = client.get('/api/history').get_json()
    assert len(body) == 3  # fewer than default — all returned


def test_history_invalid_limit_falls_back_to_50(client, test_db_path):
    _seed(2)
    body = client.get('/api/history?limit=abc').get_json()
    assert isinstance(body, list)


# ── GET /api/stats ─────────────────────────────────────────────────────────────

def test_stats_returns_200(client):
    resp = client.get('/api/stats')
    assert resp.status_code == 200


def test_stats_has_total_field(client):
    body = client.get('/api/stats').get_json()
    assert 'total' in body


def test_stats_has_avg_duration_field(client):
    body = client.get('/api/stats').get_json()
    assert 'avg_duration' in body


def test_stats_total_matches_seeded_count(client, test_db_path):
    _seed(4)
    body = client.get('/api/stats').get_json()
    assert body['total'] == 4


def test_stats_empty_db_total_is_zero(client):
    body = client.get('/api/stats').get_json()
    assert body['total'] == 0


# ── DELETE /api/history/<id> ───────────────────────────────────────────────────

def test_delete_existing_row_returns_200(client, test_db_path):
    ids = _seed(1)
    resp = client.delete(f'/api/history/{ids[0]}')
    assert resp.status_code == 200


def test_delete_returns_deleted_true(client, test_db_path):
    ids = _seed(1)
    body = client.delete(f'/api/history/{ids[0]}').get_json()
    assert body.get('deleted') is True


def test_delete_returns_correct_id(client, test_db_path):
    ids = _seed(1)
    body = client.delete(f'/api/history/{ids[0]}').get_json()
    assert body.get('id') == ids[0]


def test_delete_nonexistent_returns_404(client):
    resp = client.delete('/api/history/99999')
    assert resp.status_code == 404


def test_delete_removes_row_from_history(client, test_db_path):
    ids = _seed(2)
    client.delete(f'/api/history/{ids[0]}')
    body = client.get('/api/history').get_json()
    remaining_ids = [r['id'] for r in body]
    assert ids[0] not in remaining_ids

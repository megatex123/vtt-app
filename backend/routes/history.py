import logging

from flask import Blueprint, request, jsonify

import database

log = logging.getLogger(__name__)

history_bp = Blueprint('history', __name__)


@history_bp.get('/history')
def get_history():
    try:
        limit = int(request.args.get('limit', 50))
    except (TypeError, ValueError):
        limit = 50

    limit = max(1, min(limit, 200))
    rows  = database.get_history(limit=limit)
    return jsonify(rows)


@history_bp.get('/stats')
def get_stats():
    return jsonify(database.get_stats())


@history_bp.delete('/history/<int:id>')
def delete_entry(id):
    deleted = database.delete_transcription(id)
    if not deleted:
        return jsonify({'error': f'Transcription {id} not found.'}), 404
    return jsonify({'deleted': True, 'id': id})

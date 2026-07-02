import sys
if sys.version_info >= (3, 14):
    sys.path.insert(1, '/home/penyahpepijat/py314-packages')
import os
import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)

log = logging.getLogger(__name__)

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

import database
from telegram import notify_server_start
from transcriber import model_info
from routes.transcribe import transcribe_bp
from routes.history import history_bp

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
PORT         = int(os.environ.get('PORT', 5000))
CORS_ORIGIN  = os.environ.get('CORS_ORIGIN', 'https://voicetotext.percubaan.com')

app = Flask(__name__)

CORS(app, resources={
    r'/api/*': {
        'origins':      [CORS_ORIGIN, 'http://localhost:5000', 'http://localhost:3000'],
        'methods':      ['GET', 'POST', 'DELETE', 'OPTIONS'],
        'allow_headers': ['Content-Type'],
        'max_age':      600,
    }
})

app.register_blueprint(transcribe_bp, url_prefix='/api')
app.register_blueprint(history_bp,    url_prefix='/api')


@app.get('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.get('/<path:filename>')
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.get('/health')
def health():
    info = model_info()
    return jsonify({
        'status': 'ok',
        'port':   PORT,
        'model':  info['model_used'] or ('fine-tuned' if info['fine_tuned_exists'] else 'base'),
        'model_loaded':        info['loaded'],
        'fine_tuned_exists':   info['fine_tuned_exists'],
    })


def _startup():
    database.init_db()
    log.info('[app] Database initialised')
    notify_server_start()
    log.info('[app] VTT server ready on port %d', PORT)


if __name__ == '__main__':
    _startup()
    app.run(host='0.0.0.0', port=PORT)

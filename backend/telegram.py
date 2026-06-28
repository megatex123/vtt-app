import os
import logging

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN   = os.getenv('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

log = logging.getLogger(__name__)


def send(message: str) -> None:
    """Send a plain or HTML message. Silent fail if token/chat_id not configured."""
    if not TOKEN or not CHAT_ID:
        log.debug('[telegram] TOKEN or CHAT_ID not set — skipping notification')
        return
    try:
        requests.post(
            f'https://api.telegram.org/bot{TOKEN}/sendMessage',
            json={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'},
            timeout=5,
        )
    except Exception as exc:
        log.warning('[telegram] Failed to send: %s', exc)


def notify_transcription_done(text: str, model_used: str, duration: float) -> None:
    preview = text[:120] + ('…' if len(text) > 120 else '')
    send(
        f'<b>✅ Transkripsi Selesai</b>\n'
        f'📝 <i>{preview}</i>\n'
        f'🤖 Model: <code>{model_used}</code>\n'
        f'⏱ Durasi: <code>{duration:.1f}s</code>'
    )


def notify_transcription_error(error: str) -> None:
    send(f'<b>❌ Ralat Transkripsi</b>\n<code>{str(error)[:200]}</code>')


def notify_server_start() -> None:
    send('<b>🚀 VTT Server Dimulakan</b>\nvoicetotext.percubaan.com sedang berjalan.')


def notify_server_stats(total: int, avg_duration: float) -> None:
    avg = f'{avg_duration:.1f}s' if avg_duration is not None else 'N/A'
    send(
        f'<b>📊 Statistik VTT</b>\n'
        f'Jumlah transkripsi: <code>{total}</code>\n'
        f'Purata durasi: <code>{avg}</code>'
    )

// Recorder — MediaRecorder wrapper with state machine and fetch upload
//
// States: 'idle' → 'recording' → 'processing' → 'idle'
//
// Usage:
//   const rec = new Recorder({
//     url:           'https://api.percubaan.com/transcribe',
//     onStateChange: (state) => { /* 'idle'|'recording'|'processing' */ },
//     onTimer:       (label) => { /* '01:23' while recording, '' otherwise */ },
//     onStream:      (stream|null) => { /* connect to Waveform.start/stop */ },
//     onResult:      (data) => { /* { id, text, duration, model_used, language } */ },
//     onError:       (message) => { /* human-readable Malay error string */ },
//   });
//   await rec.start();
//   rec.stop();
export class Recorder {
  constructor(options = {}) {
    this._url    = options.url || 'https://api.percubaan.com/transcribe';
    this._onStateChange = options.onStateChange || (() => {});
    this._onTimer       = options.onTimer       || (() => {});
    this._onStream      = options.onStream      || (() => {});
    this._onResult      = options.onResult      || (() => {});
    this._onError       = options.onError       || (() => {});

    this._state         = 'idle';
    this._mediaRecorder = null;
    this._stream        = null;
    this._chunks        = [];
    this._timerHandle   = null;
    this._startTime     = 0;
  }

  get state() { return this._state; }

  async start() {
    if (this._state !== 'idle') return;

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      const msg = err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError'
        ? 'Kebenaran mikrofon ditolak. Sila benarkan akses mikrofon dalam tetapan penyemak imbas.'
        : `Ralat mikrofon: ${err.message}`;
      this._onError(msg);
      return;
    }

    this._stream = stream;
    this._onStream(stream);

    const mime = _bestMime();
    this._mediaRecorder = new MediaRecorder(stream, mime ? { mimeType: mime } : {});
    this._chunks = [];

    this._mediaRecorder.ondataavailable = e => { if (e.data.size > 0) this._chunks.push(e.data); };
    this._mediaRecorder.onstop = () => this._submit();

    this._mediaRecorder.start(250);
    this._startTime   = Date.now();
    this._timerHandle = setInterval(() => {
      const s  = Math.floor((Date.now() - this._startTime) / 1000);
      const mm = String(Math.floor(s / 60)).padStart(2, '0');
      const ss = String(s % 60).padStart(2, '0');
      this._onTimer(`${mm}:${ss}`);
    }, 1000);

    this._setState('recording');
  }

  stop() {
    if (this._state !== 'recording') return;

    clearInterval(this._timerHandle);
    this._timerHandle = null;
    this._onTimer('');

    this._stream.getTracks().forEach(t => t.stop());
    this._onStream(null);
    this._mediaRecorder.stop();
    this._setState('processing');
  }

  async _submit() {
    const mime = this._mediaRecorder.mimeType || '';
    const ext  = mime.includes('webm') ? '.webm'
               : mime.includes('ogg')  ? '.ogg'
               : '.wav';
    const blob = new Blob(this._chunks, { type: mime || 'audio/webm' });
    const fd   = new FormData();
    fd.append('audio', blob, 'recording' + ext);

    try {
      const res  = await fetch(this._url, { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `Ralat pelayan (${res.status})`);
      this._onResult(data);
    } catch (err) {
      const msg = (err.message === 'Failed to fetch' || err instanceof TypeError)
        ? 'Pelayan tidak dapat dicapai. Periksa sambungan internet atau cuba lagi.'
        : `Ralat: ${err.message}`;
      this._onError(msg);
    } finally {
      this._setState('idle');
    }
  }

  _setState(s) {
    this._state = s;
    this._onStateChange(s);
  }
}

// MediaRecorder prefers webm/opus; falls back through ogg.
// WAV and MP3 are not directly producible by MediaRecorder in browsers.
// The backend accepts .webm natively so this is fine.
function _bestMime() {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/ogg',
  ];
  return candidates.find(m => MediaRecorder.isTypeSupported(m)) || '';
}

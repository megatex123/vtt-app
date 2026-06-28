// Canvas FFT waveform — 24 cyan bars, centered vertically
// Usage:
//   const wf = new Waveform(canvasEl);
//   wf.start(mediaStream);   // begin animation
//   wf.stop();               // freeze + reset to idle state
export class Waveform {
  static NUM_BARS = 24;
  static BAR_W    = 4;
  static GAP      = 3;
  static COLOR    = '#06b6d4';

  constructor(canvas) {
    this._canvas   = canvas;
    this._ctx      = canvas.getContext('2d');
    this._raf      = null;
    this._analyser = null;
    this._audioCtx = null;
    this._drawIdle();
  }

  start(stream) {
    this.stop();
    this._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    this._analyser = this._audioCtx.createAnalyser();
    this._analyser.fftSize = 64;
    this._audioCtx.createMediaStreamSource(stream).connect(this._analyser);
    this._tick();
  }

  stop() {
    if (this._raf)      { cancelAnimationFrame(this._raf); this._raf = null; }
    if (this._audioCtx) { this._audioCtx.close(); this._audioCtx = null; }
    this._analyser = null;
    this._drawIdle();
  }

  _tick() {
    const data = new Uint8Array(this._analyser.frequencyBinCount);
    this._analyser.getByteFrequencyData(data);
    this._draw(data);
    this._raf = requestAnimationFrame(() => this._tick());
  }

  _draw(data) {
    const { _canvas: cv, _ctx: ctx } = this;
    const { NUM_BARS, BAR_W, GAP, COLOR } = Waveform;
    const step      = Math.floor(data.length / NUM_BARS);
    const totalW    = NUM_BARS * BAR_W + (NUM_BARS - 1) * GAP;
    const startX    = (cv.width - totalW) / 2;
    const maxBarH   = cv.height * 0.9;

    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.fillStyle = COLOR;

    for (let i = 0; i < NUM_BARS; i++) {
      const val  = data[i * step] || 0;
      const barH = Math.max(4, (val / 255) * maxBarH);
      const x    = startX + i * (BAR_W + GAP);
      const y    = (cv.height - barH) / 2;

      ctx.globalAlpha = val > 10 ? 1.0 : 0.35;
      this._roundRect(x, y, BAR_W, barH, 2);
    }
    ctx.globalAlpha = 1.0;
  }

  _drawIdle() {
    const { _canvas: cv, _ctx: ctx } = this;
    const { NUM_BARS, BAR_W, GAP, COLOR } = Waveform;
    const totalW = NUM_BARS * BAR_W + (NUM_BARS - 1) * GAP;
    const startX = (cv.width - totalW) / 2;
    const barH   = 8;
    const y      = (cv.height - barH) / 2;

    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.fillStyle  = COLOR;
    ctx.globalAlpha = 0.35;
    for (let i = 0; i < NUM_BARS; i++) {
      this._roundRect(startX + i * (BAR_W + GAP), y, BAR_W, barH, 2);
    }
    ctx.globalAlpha = 1.0;
  }

  _roundRect(x, y, w, h, r) {
    const ctx = this._ctx;
    if (ctx.roundRect) {
      ctx.beginPath();
      ctx.roundRect(x, y, w, h, r);
      ctx.fill();
    } else {
      ctx.fillRect(x, y, w, h);
    }
  }
}

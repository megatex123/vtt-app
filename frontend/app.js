(() => {
  const NUM_BARS = 24;
  const API_TRANSCRIBE = '/api/transcribe';

  // --- DOM refs ---
  const btnRecord   = document.getElementById('btn-record');
  const btnLabel    = document.getElementById('btn-label');
  const dot         = document.getElementById('dot');
  const statusEl    = document.getElementById('status');
  const resultCard  = document.getElementById('result-card');
  const transcriptEl= document.getElementById('transcript');
  const btnCopy     = document.getElementById('btn-copy');
  const btnClearRes = document.getElementById('btn-clear-result');
  const historyList = document.getElementById('history-list');
  const emptyMsg    = document.getElementById('empty-msg');
  const waveform    = document.getElementById('waveform');

  // --- Build waveform bars ---
  const bars = Array.from({ length: NUM_BARS }, () => {
    const b = document.createElement('div');
    b.className = 'bar';
    waveform.appendChild(b);
    return b;
  });

  // --- State ---
  let mediaRecorder = null;
  let audioCtx = null;
  let analyser  = null;
  let animFrame = null;
  let chunks    = [];
  let isRecording = false;

  // --- Waveform animation ---
  function animateBars() {
    if (!analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(data);
    const step = Math.floor(data.length / NUM_BARS);
    bars.forEach((bar, i) => {
      const val = data[i * step] || 0;
      const h = Math.max(4, (val / 255) * 54);
      bar.style.height = h + 'px';
      bar.classList.toggle('active', val > 10);
    });
    animFrame = requestAnimationFrame(animateBars);
  }

  function resetBars() {
    bars.forEach(b => { b.style.height = '8px'; b.classList.remove('active'); });
  }

  // --- Status helpers ---
  function setStatus(msg, type = '') {
    statusEl.textContent = msg;
    statusEl.className = type;
  }

  // --- History ---
  function addHistory(text) {
    if (emptyMsg) emptyMsg.remove();
    const li  = document.createElement('li');
    const now = new Date().toLocaleTimeString('ms-MY', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    li.innerHTML = `<span class="ts">${now}</span><span class="txt">${escHtml(text)}</span>`;
    historyList.prepend(li);
    // keep last 20
    const items = historyList.querySelectorAll('li:not(.empty-state)');
    if (items.length > 20) items[items.length - 1].remove();
  }

  function escHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // --- Start recording ---
  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      audioCtx  = new (window.AudioContext || window.webkitAudioContext)();
      analyser  = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      audioCtx.createMediaStreamSource(stream).connect(analyser);

      mediaRecorder = new MediaRecorder(stream, { mimeType: bestMime() });
      chunks = [];
      mediaRecorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
      mediaRecorder.onstop = handleStop;

      mediaRecorder.start(250);
      isRecording = true;

      btnRecord.className = 'btn-record recording';
      btnLabel.textContent = 'Henti Rakaman';
      dot.classList.add('blink');
      setStatus('Merakam…');
      animateBars();
    } catch (err) {
      setStatus('Ralat mikrofon: ' + err.message, 'error');
    }
  }

  // --- Stop recording ---
  function stopRecording() {
    if (!mediaRecorder) return;
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
    cancelAnimationFrame(animFrame);
    resetBars();

    if (audioCtx) { audioCtx.close(); audioCtx = null; analyser = null; }

    isRecording = false;
    btnRecord.disabled = true;
    btnRecord.className = 'btn-record idle';
    btnLabel.textContent = 'Memproses…';
    dot.classList.remove('blink');
    setStatus('Menghantar audio ke pelayan…');
  }

  // --- Send to backend ---
  async function handleStop() {
    const mime = bestMime();
    const ext  = mime.includes('webm') ? '.webm' : mime.includes('ogg') ? '.ogg' : '.wav';
    const blob = new Blob(chunks, { type: mime });
    const fd   = new FormData();
    fd.append('audio', blob, 'recording' + ext);

    try {
      const res  = await fetch(API_TRANSCRIBE, { method: 'POST', body: fd });
      const data = await res.json();

      if (!res.ok) throw new Error(data.error || 'Ralat pelayan');

      const text = data.text || '';
      transcriptEl.textContent = text;
      resultCard.classList.add('visible');
      addHistory(text);
      setStatus('Transkripsi berjaya.', 'success');
    } catch (err) {
      setStatus('Ralat: ' + err.message, 'error');
    } finally {
      btnRecord.disabled = false;
      btnLabel.textContent = 'Mula Rakam';
    }
  }

  // --- Toggle ---
  btnRecord.addEventListener('click', () => {
    if (isRecording) stopRecording();
    else startRecording();
  });

  // --- Copy ---
  btnCopy.addEventListener('click', () => {
    const text = transcriptEl.textContent;
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      btnCopy.textContent = 'Disalin!';
      setTimeout(() => { btnCopy.textContent = 'Salin'; }, 1500);
    });
  });

  // --- Clear result ---
  btnClearRes.addEventListener('click', () => {
    transcriptEl.textContent = '';
    resultCard.classList.remove('visible');
    setStatus('');
  });

  // --- Pick best MIME ---
  function bestMime() {
    const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg'];
    return candidates.find(m => MediaRecorder.isTypeSupported(m)) || '';
  }
})();

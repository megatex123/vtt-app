import { useRef, useEffect, useState } from 'react';
import Head from 'next/head';
import Transcription from '../components/Transcription';
import History from '../components/History';

const IDLE       = 'idle';
const RECORDING  = 'recording';
const PROCESSING = 'processing';

const ACCEPTED = '.wav,.mp3,.m4a,.webm,.ogg';

export default function Home() {
  const canvasRef    = useRef(null);
  const recorderRef  = useRef(null);
  const waveformRef  = useRef(null);
  const fileInputRef = useRef(null);

  const [tab,         setTab]         = useState('record');   // 'record' | 'upload'
  const [recState,    setRecState]    = useState(IDLE);
  const [timer,       setTimer]       = useState('');
  const [result,      setResult]      = useState(null);
  const [error,       setError]       = useState('');
  const [historyKey,  setHistoryKey]  = useState(0);

  // Upload-specific state
  const [uploadFile,    setUploadFile]    = useState(null);   // File object
  const [uploading,     setUploading]     = useState(false);
  const [uploadError,   setUploadError]   = useState('');

  useEffect(() => {
    if (!canvasRef.current) return;
    let rec;
    Promise.all([
      import('../components/Waveform'),
      import('../components/Recorder'),
    ]).then(([{ Waveform }, { Recorder }]) => {
      const wf = new Waveform(canvasRef.current);
      waveformRef.current = wf;
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
      rec = new Recorder({
        url:           `${apiUrl}/transcribe`,
        onStateChange: setRecState,
        onTimer:       setTimer,
        onStream:      s => s ? wf.start(s) : wf.stop(),
        onResult:      data => {
          setResult(data);
          setError('');
          setHistoryKey(k => k + 1);
        },
        onError: msg => setError(msg),
      });
      recorderRef.current = rec;
    });
    return () => { if (rec?.state === RECORDING) rec.stop(); };
  }, []);

  const toggleRecord = () => {
    const rec = recorderRef.current;
    if (!rec) return;
    if (rec.state === IDLE)           rec.start();
    else if (rec.state === RECORDING) rec.stop();
  };

  const handleFileChange = e => {
    const f = e.target.files?.[0] || null;
    setUploadFile(f);
    setUploadError('');
  };

  const submitUpload = async () => {
    if (!uploadFile || uploading) return;
    setUploading(true);
    setUploadError('');
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
      const form = new FormData();
      form.append('audio', uploadFile);
      const res  = await fetch(`${apiUrl}/transcribe`, { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `Ralat pelayan (${res.status})`);
      setResult(data);
      setHistoryKey(k => k + 1);
      setUploadFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setUploadError(err.message || 'Gagal memuat naik fail');
    } finally {
      setUploading(false);
    }
  };

  const isRecording  = recState === RECORDING;
  const isProcessing = recState === PROCESSING;
  const busy         = isProcessing || uploading;

  const btnLabel = isProcessing ? 'Memproses…'
    : isRecording ? 'Henti Rakaman'
    : 'Mula Rakam';

  return (
    <>
      <Head>
        <title>VoiceToText — percubaan.com</title>
        <meta name="description" content="Transkripsi audio Bahasa Melayu menggunakan Whisper" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-[#0a0a14] text-[#e2e8f0]">
        <div className="max-w-xl mx-auto px-4 py-10 sm:py-14 space-y-4">

          {/* Header */}
          <header className="text-center mb-8">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Voice<span className="text-[#6366f1]">ToText</span>
            </h1>
            <p className="text-[#64748b] text-sm mt-1.5">
              percubaan.com &mdash; Transkripsi audio Bahasa Melayu via Whisper
            </p>
          </header>

          {/* Main card */}
          <div className="bg-[#141430] border border-[#1e1e3a] rounded-2xl p-6">

            {/* Tab switcher */}
            <div className="flex gap-1 mb-6 bg-[#0d0d24] rounded-xl p-1">
              {[['record', '🎙 Rakam'], ['upload', '📁 Muat Naik']].map(([id, label]) => (
                <button
                  key={id}
                  onClick={() => { setTab(id); setError(''); setUploadError(''); }}
                  disabled={busy}
                  className={[
                    'flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all duration-150',
                    tab === id
                      ? 'bg-[#6366f1] text-white shadow'
                      : 'text-[#64748b] hover:text-[#e2e8f0]',
                  ].join(' ')}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* ── RECORD TAB ── */}
            {tab === 'record' && (
              <>
                <div className="flex justify-center mb-5 h-[60px]">
                  <canvas ref={canvasRef} width={320} height={60} className="w-full max-w-xs" />
                </div>

                <button
                  onClick={toggleRecord}
                  disabled={isProcessing}
                  className={[
                    'w-full flex items-center justify-center gap-2.5',
                    'py-3.5 px-6 rounded-xl font-semibold text-base transition-all duration-200',
                    isRecording
                      ? 'bg-[#ef4444] text-white shadow-[0_0_24px_rgba(239,68,68,0.3)] hover:bg-[#dc2626]'
                      : isProcessing
                        ? 'bg-[#1e1e3a] text-[#64748b] cursor-not-allowed'
                        : 'bg-[#6366f1] text-white shadow-[0_0_24px_rgba(99,102,241,0.3)] hover:bg-[#4f46e5]',
                  ].join(' ')}
                >
                  <span className={['w-2.5 h-2.5 rounded-full bg-current flex-shrink-0', isRecording ? 'animate-ping' : ''].join(' ')} />
                  <span>{btnLabel}</span>
                  {isRecording && timer && (
                    <span className="ml-auto font-mono text-sm opacity-75 tabular-nums">{timer}</span>
                  )}
                </button>

                {error && <p className="text-[#ef4444] text-xs text-center mt-3">{error}</p>}
              </>
            )}

            {/* ── UPLOAD TAB ── */}
            {tab === 'upload' && (
              <>
                {/* Hidden file input */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED}
                  onChange={handleFileChange}
                  className="hidden"
                />

                {/* Drop zone / picker button */}
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="w-full border-2 border-dashed border-[#1e1e3a] hover:border-[#6366f1] rounded-xl py-8 px-4 flex flex-col items-center gap-2 transition-colors duration-200 group"
                >
                  <span className="text-3xl">📂</span>
                  <span className="text-[#64748b] group-hover:text-[#e2e8f0] text-sm transition-colors">
                    {uploadFile ? uploadFile.name : 'Pilih fail audio…'}
                  </span>
                  {!uploadFile && (
                    <span className="text-[#64748b] text-xs">WAV · MP3 · M4A · WebM · OGG</span>
                  )}
                  {uploadFile && (
                    <span className="text-[#64748b] text-xs">
                      {(uploadFile.size / 1024).toFixed(0)} KB &middot; {uploadFile.type || 'audio'}
                    </span>
                  )}
                </button>

                {/* Transcribe button — only visible once a file is chosen */}
                {uploadFile && (
                  <button
                    onClick={submitUpload}
                    disabled={uploading}
                    className={[
                      'w-full mt-3 flex items-center justify-center gap-2.5',
                      'py-3.5 px-6 rounded-xl font-semibold text-base transition-all duration-200',
                      uploading
                        ? 'bg-[#1e1e3a] text-[#64748b] cursor-not-allowed'
                        : 'bg-[#6366f1] text-white shadow-[0_0_24px_rgba(99,102,241,0.3)] hover:bg-[#4f46e5]',
                    ].join(' ')}
                  >
                    {uploading ? (
                      <>
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        <span>Memproses…</span>
                      </>
                    ) : (
                      <>
                        <span>🔤</span>
                        <span>Transkripsi</span>
                      </>
                    )}
                  </button>
                )}

                {uploadError && (
                  <p className="text-[#ef4444] text-xs text-center mt-3">{uploadError}</p>
                )}
              </>
            )}
          </div>

          {/* Transcription result */}
          <Transcription result={result} isProcessing={busy} />

          {/* History */}
          <div className="bg-[#141430] border border-[#1e1e3a] rounded-2xl p-6">
            <History refreshKey={historyKey} />
          </div>

          <footer className="text-center text-[#64748b] text-xs pt-4">
            percubaan.com &mdash; Sistem AI Tempatan
          </footer>
        </div>
      </div>
    </>
  );
}

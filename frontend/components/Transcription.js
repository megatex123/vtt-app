import { useEffect, useState } from 'react';

function Spinner() {
  return (
    <svg
      className="animate-spin h-5 w-5 text-cyan-400"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

function modelLabel(modelUsed) {
  if (!modelUsed) return '—';
  // base whisper from HuggingFace looks like "openai/whisper-small"
  return modelUsed.startsWith('openai/') ? 'Whisper Asas' : 'Model Tersuai';
}

function fmtDuration(secs) {
  if (!secs && secs !== 0) return '';
  const n = Number(secs);
  if (n < 60) return `${n.toFixed(1)}s`;
  return `${Math.floor(n / 60)}m ${(n % 60).toFixed(0)}s`;
}

export default function Transcription({ result, isProcessing }) {
  const [copied, setCopied] = useState(false);
  const [visible, setVisible] = useState(false);

  // Reset + trigger fade animation whenever a new result arrives (keyed by id)
  useEffect(() => {
    setVisible(false);
    if (!result) return;
    const t = setTimeout(() => setVisible(true), 20);
    return () => clearTimeout(t);
  }, [result?.id]);

  const copy = async () => {
    if (!result?.text) return;
    try {
      await navigator.clipboard.writeText(result.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard may be blocked in non-secure context
    }
  };

  if (isProcessing) {
    return (
      <div className="rounded-2xl bg-[#141430] border border-[#1e1e3a] p-6 flex flex-col items-center justify-center gap-3 min-h-[7rem]">
        <Spinner />
        <p className="text-[#64748b] text-sm">Memproses audio…</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="rounded-2xl bg-[#141430] border border-[#1e1e3a] p-6 flex items-center justify-center min-h-[7rem]">
        <p className="text-[#64748b] text-sm text-center">
          Tiada transkripsi lagi. Tekan butang rakam untuk mula.
        </p>
      </div>
    );
  }

  return (
    <div
      className="rounded-2xl bg-[#141430] border border-[#1e1e3a] p-6 transition-all duration-300 ease-out"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(8px)',
      }}
    >
      <p className="text-[#e2e8f0] text-lg leading-relaxed whitespace-pre-wrap break-words mb-4 min-h-[3rem]">
        {result.text}
      </p>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="bg-[#111128] border border-[#1e1e3a] text-[#64748b] rounded-md px-2 py-0.5">
          {modelLabel(result.model_used)}
        </span>

        {result.duration != null && (
          <span className="text-[#64748b]">{fmtDuration(result.duration)}</span>
        )}

        {result.language && (
          <span className="text-[#64748b] uppercase tracking-wide">{result.language}</span>
        )}

        <button
          onClick={copy}
          className="ml-auto bg-[#111128] hover:bg-[#1e1e3a] border border-[#1e1e3a] text-[#e2e8f0] rounded-lg px-3 py-1 transition-colors text-xs"
        >
          {copied ? 'Disalin ✓' : 'Salin'}
        </button>
      </div>
    </div>
  );
}

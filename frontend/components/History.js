import { useEffect, useState } from 'react';

const PAGE_SIZE = 10;
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.percubaan.com';

function fmtTime(ts) {
  if (!ts) return '';
  try {
    return new Date(ts + (ts.endsWith('Z') ? '' : 'Z')).toLocaleString('ms-MY', {
      day: '2-digit', month: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

function modelBadge(m) {
  if (!m) return '—';
  return m.startsWith('openai/') ? 'Asas' : 'Tersuai';
}

function fmtSecs(s) {
  return s != null ? `${Number(s).toFixed(1)}s` : '';
}

function ChevronLeft() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
    </svg>
  );
}

function ChevronRight() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}

export default function History({ refreshKey }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/history?limit=200`);
      if (res.ok) setItems(await res.json());
    } catch {
      // non-critical — history is informational only
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(0);
    load();
  }, [refreshKey]);

  const del = async (id) => {
    try {
      await fetch(`${API_URL}/history/${id}`, { method: 'DELETE' });
      setItems(prev => prev.filter(i => i.id !== id));
    } catch {
      // silent fail
    }
  };

  const totalPages = Math.ceil(items.length / PAGE_SIZE);
  const paged = items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <section>
      <h2 className="text-xs font-semibold text-[#64748b] uppercase tracking-widest mb-4">
        Sejarah{items.length > 0 ? ` (${items.length})` : ''}
      </h2>

      {loading && (
        <p className="text-[#64748b] text-sm text-center py-6">Memuatkan…</p>
      )}

      {!loading && items.length === 0 && (
        <p className="text-[#64748b] text-sm text-center py-6">Tiada sejarah lagi.</p>
      )}

      {!loading && (
        <ul className="space-y-2">
          {paged.map(item => (
            <li
              key={item.id}
              className="group flex items-start gap-3 bg-[#111128] border border-[#1e1e3a] rounded-xl px-4 py-3"
            >
              <div className="flex-1 min-w-0">
                <p className="text-[#e2e8f0] text-sm truncate">{item.text}</p>
                <div className="flex flex-wrap gap-2 mt-1 text-xs text-[#64748b]">
                  <span>{fmtTime(item.timestamp)}</span>
                  {item.duration_seconds != null && <span>{fmtSecs(item.duration_seconds)}</span>}
                  <span className="bg-[#141430] border border-[#1e1e3a] rounded px-1.5 py-px">
                    {modelBadge(item.model_used)}
                  </span>
                </div>
              </div>

              <button
                onClick={() => del(item.id)}
                title="Padam"
                className="flex-shrink-0 text-[#64748b] hover:text-[#ef4444] transition-colors mt-0.5 opacity-40 group-hover:opacity-100 text-xs leading-none"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 text-xs text-[#64748b]">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="flex items-center gap-1 px-3 py-1.5 bg-[#111128] border border-[#1e1e3a] rounded-lg disabled:opacity-30 hover:bg-[#1e1e3a] transition-colors"
          >
            <ChevronLeft /> Sebelum
          </button>

          <span>{page + 1} / {totalPages}</span>

          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="flex items-center gap-1 px-3 py-1.5 bg-[#111128] border border-[#1e1e3a] rounded-lg disabled:opacity-30 hover:bg-[#1e1e3a] transition-colors"
          >
            Seterus <ChevronRight />
          </button>
        </div>
      )}
    </section>
  );
}

/**
 * History.test.js
 * Tests the History React component:
 *   - renders list of transcriptions fetched from API
 *   - shows empty state when no items
 *   - shows loading state while fetching
 *   - delete button calls DELETE API with correct id
 *   - item removed from list after delete
 *   - pagination shown when > 10 items
 */

import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import History from '../components/History';

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeItem(id, text = `Transkripsi ${id}`) {
  return {
    id,
    text,
    timestamp: '2026-06-27T10:00:00',
    duration_seconds: 1.5,
    model_used: 'openai/whisper-small',
  };
}

const TWO_ITEMS = [makeItem(1, 'Transkripsi pertama'), makeItem(2, 'Transkripsi kedua')];

// ── Fetch mock helpers ────────────────────────────────────────────────────────

function mockFetchOnce(data, ok = true) {
  global.fetch = jest.fn().mockResolvedValueOnce({
    ok,
    json: async () => data,
  });
}

function mockFetchSequence(...responses) {
  global.fetch = jest.fn();
  responses.forEach(([data, ok = true]) => {
    global.fetch.mockResolvedValueOnce({ ok, json: async () => data });
  });
}

afterEach(() => {
  jest.restoreAllMocks();
  if (global.fetch && global.fetch.mockRestore) global.fetch.mockRestore();
  global.fetch = undefined;
});

// ── Render helper ─────────────────────────────────────────────────────────────

async function renderHistory(props = { refreshKey: 0 }) {
  await act(async () => {
    render(<History {...props} />);
  });
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('History — loading state', () => {
  test('shows Memuatkan… while fetch is pending', () => {
    global.fetch = jest.fn(() => new Promise(() => {})); // never resolves
    render(<History refreshKey={0} />);
    expect(screen.getByText('Memuatkan…')).toBeInTheDocument();
  });
});

describe('History — empty state', () => {
  test('shows empty state message when API returns []', async () => {
    mockFetchOnce([]);
    await renderHistory();
    expect(screen.getByText('Tiada sejarah lagi.')).toBeInTheDocument();
  });

  test('shows Sejarah heading with no count', async () => {
    mockFetchOnce([]);
    await renderHistory();
    expect(screen.getByText('Sejarah')).toBeInTheDocument();
  });
});

describe('History — populated list', () => {
  test('renders each item\'s text', async () => {
    mockFetchOnce(TWO_ITEMS);
    await renderHistory();
    expect(screen.getByText('Transkripsi pertama')).toBeInTheDocument();
    expect(screen.getByText('Transkripsi kedua')).toBeInTheDocument();
  });

  test('shows count in heading', async () => {
    mockFetchOnce(TWO_ITEMS);
    await renderHistory();
    expect(screen.getByText('Sejarah (2)')).toBeInTheDocument();
  });

  test('shows duration for each item', async () => {
    mockFetchOnce(TWO_ITEMS);
    await renderHistory();
    const durations = screen.getAllByText('1.5s');
    expect(durations.length).toBe(2);
  });

  test('shows Asas badge for openai/ model', async () => {
    mockFetchOnce(TWO_ITEMS);
    await renderHistory();
    const badges = screen.getAllByText('Asas');
    expect(badges.length).toBe(2);
  });

  test('shows Tersuai badge for fine-tuned model', async () => {
    mockFetchOnce([makeItem(1)].map(i => ({ ...i, model_used: 'fine-tuned' })));
    await renderHistory();
    expect(screen.getByText('Tersuai')).toBeInTheDocument();
  });
});

describe('History — delete', () => {
  test('renders a delete button per item', async () => {
    mockFetchOnce(TWO_ITEMS);
    await renderHistory();
    const deleteBtns = screen.getAllByTitle('Padam');
    expect(deleteBtns).toHaveLength(2);
  });

  test('delete button calls DELETE /history/:id', async () => {
    mockFetchSequence(
      [TWO_ITEMS],            // initial load
      [{ deleted: true }, true] // DELETE response
    );
    await renderHistory();

    await act(async () => {
      fireEvent.click(screen.getAllByTitle('Padam')[0]);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/history/1'),
      { method: 'DELETE' }
    );
  });

  test('removes deleted item from the list', async () => {
    mockFetchSequence(
      [TWO_ITEMS],
      [{ deleted: true }, true]
    );
    await renderHistory();

    expect(screen.getByText('Transkripsi pertama')).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getAllByTitle('Padam')[0]);
    });

    expect(screen.queryByText('Transkripsi pertama')).not.toBeInTheDocument();
    expect(screen.getByText('Transkripsi kedua')).toBeInTheDocument();
  });
});

describe('History — pagination', () => {
  const FIFTEEN_ITEMS = Array.from({ length: 15 }, (_, i) => makeItem(i + 1, `Item ${i + 1}`));

  test('does not show pagination for ≤ 10 items', async () => {
    mockFetchOnce(TWO_ITEMS);
    await renderHistory();
    expect(screen.queryByText(/Seterus/)).not.toBeInTheDocument();
  });

  test('shows pagination controls for > 10 items', async () => {
    mockFetchOnce(FIFTEEN_ITEMS);
    await renderHistory();
    expect(screen.getByText(/Seterus/)).toBeInTheDocument();
  });

  test('shows page indicator 1 / 2 for 15 items', async () => {
    mockFetchOnce(FIFTEEN_ITEMS);
    await renderHistory();
    expect(screen.getByText('1 / 2')).toBeInTheDocument();
  });

  test('Sebelum button is disabled on first page', async () => {
    mockFetchOnce(FIFTEEN_ITEMS);
    await renderHistory();
    expect(screen.getByText(/Sebelum/).closest('button')).toBeDisabled();
  });

  test('clicking Seterus shows next page', async () => {
    mockFetchOnce(FIFTEEN_ITEMS);
    await renderHistory();

    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.queryByText('Item 11')).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByText(/Seterus/).closest('button'));
    });

    expect(screen.queryByText('Item 1')).not.toBeInTheDocument();
    expect(screen.getByText('Item 11')).toBeInTheDocument();
    expect(screen.getByText('2 / 2')).toBeInTheDocument();
  });
});

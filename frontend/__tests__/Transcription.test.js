/**
 * Transcription.test.js
 * Tests the Transcription React component:
 *   - shows spinner when processing
 *   - displays result text when done
 *   - copy button writes to clipboard and shows feedback
 *   - shows model label (Whisper Asas vs Model Tersuai)
 *   - shows formatted duration
 *   - shows empty state when no result
 */

import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import Transcription from '../components/Transcription';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const BASE_RESULT = {
  id: 1,
  text: 'Ini adalah transkripsi ujian Bahasa Melayu.',
  duration: 2.5,
  model_used: 'openai/whisper-small',
  language: 'ms',
};

// ── Clipboard mock ────────────────────────────────────────────────────────────

let mockWriteText;
beforeEach(() => {
  mockWriteText = jest.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: mockWriteText },
    configurable: true,
    writable: true,
  });
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Transcription — loading state', () => {
  test('shows spinner SVG when isProcessing is true', () => {
    render(<Transcription isProcessing={true} result={null} />);
    expect(document.querySelector('svg.animate-spin')).toBeInTheDocument();
  });

  test('shows Memproses audio text when processing', () => {
    render(<Transcription isProcessing={true} result={null} />);
    expect(screen.getByText('Memproses audio…')).toBeInTheDocument();
  });

  test('does not show result text while processing', () => {
    render(<Transcription isProcessing={true} result={BASE_RESULT} />);
    // When isProcessing, the spinner branch renders, not the result
    expect(screen.queryByText(BASE_RESULT.text)).not.toBeInTheDocument();
  });
});

describe('Transcription — empty state', () => {
  test('shows empty state message when result is null', () => {
    render(<Transcription isProcessing={false} result={null} />);
    expect(screen.getByText(/Tiada transkripsi lagi/)).toBeInTheDocument();
  });

  test('does not show copy button when no result', () => {
    render(<Transcription isProcessing={false} result={null} />);
    expect(screen.queryByRole('button', { name: /salin/i })).not.toBeInTheDocument();
  });
});

describe('Transcription — result display', () => {
  async function renderWithResult(result = BASE_RESULT) {
    await act(async () => {
      render(<Transcription isProcessing={false} result={result} />);
    });
  }

  test('displays transcription text', async () => {
    await renderWithResult();
    expect(screen.getByText(BASE_RESULT.text)).toBeInTheDocument();
  });

  test('shows Whisper Asas badge for openai/whisper-* model', async () => {
    await renderWithResult();
    expect(screen.getByText('Whisper Asas')).toBeInTheDocument();
  });

  test('shows Model Tersuai badge for fine-tuned model', async () => {
    await renderWithResult({ ...BASE_RESULT, model_used: 'my-fine-tuned-whisper' });
    expect(screen.getByText('Model Tersuai')).toBeInTheDocument();
  });

  test('shows — when model_used is missing', async () => {
    await renderWithResult({ ...BASE_RESULT, model_used: null });
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  test('formats duration under 60s correctly', async () => {
    await renderWithResult({ ...BASE_RESULT, duration: 2.5 });
    expect(screen.getByText('2.5s')).toBeInTheDocument();
  });

  test('formats duration over 60s correctly', async () => {
    await renderWithResult({ ...BASE_RESULT, duration: 75 });
    expect(screen.getByText('1m 15s')).toBeInTheDocument();
  });

  test('shows language label in uppercase', async () => {
    await renderWithResult();
    expect(screen.getByText('ms')).toBeInTheDocument();
  });

  test('omits duration span when duration is null', async () => {
    await renderWithResult({ ...BASE_RESULT, duration: null });
    // Should not throw; result text is still there
    expect(screen.getByText(BASE_RESULT.text)).toBeInTheDocument();
  });
});

describe('Transcription — copy button', () => {
  test('copy button is present when result exists', async () => {
    await act(async () => {
      render(<Transcription isProcessing={false} result={BASE_RESULT} />);
    });
    expect(screen.getByRole('button', { name: 'Salin' })).toBeInTheDocument();
  });

  test('clicking Salin writes result text to clipboard', async () => {
    await act(async () => {
      render(<Transcription isProcessing={false} result={BASE_RESULT} />);
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Salin' }));
    });

    expect(mockWriteText).toHaveBeenCalledWith(BASE_RESULT.text);
  });

  test('button label changes to Disalin ✓ after copy', async () => {
    jest.useFakeTimers();

    await act(async () => {
      render(<Transcription isProcessing={false} result={BASE_RESULT} />);
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Salin' }));
    });

    // Flush the clipboard.writeText promise
    await act(async () => {});

    expect(screen.getByRole('button', { name: /disalin/i })).toBeInTheDocument();

    // After 1.5s the label reverts
    act(() => jest.advanceTimersByTime(1500));
    expect(screen.getByRole('button', { name: 'Salin' })).toBeInTheDocument();

    jest.useRealTimers();
  });
});

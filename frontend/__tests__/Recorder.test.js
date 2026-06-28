/**
 * Recorder.test.js
 * Tests the recording UI in pages/index.js:
 *   - button renders correctly in idle state
 *   - clicking toggles recording state
 *   - shows live timer while recording
 *   - shows Malay error message when mic is denied
 */

import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';

// ── Mocks (hoisted by Jest before imports) ────────────────────────────────────

jest.mock('next/head', () => ({
  __esModule: true,
  default: function MockHead({ children }) { return <>{children}</>; },
}));

jest.mock('../components/Waveform', () => ({
  Waveform: class MockWaveform {
    constructor() {}
    start() {}
    stop() {}
  },
}));

// Recorder mock — behaviour set in beforeEach
jest.mock('../components/Recorder', () => ({
  Recorder: jest.fn(),
}));

// Stub child components so their own async work doesn't interfere
jest.mock('../components/Transcription', () => ({
  __esModule: true,
  default: () => <div data-testid="transcription-stub" />,
}));
jest.mock('../components/History', () => ({
  __esModule: true,
  default: () => <div data-testid="history-stub" />,
}));

// Mock canvas (jsdom has no 2D context)
beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = () => ({
    clearRect: jest.fn(),
    fillRect: jest.fn(),
    beginPath: jest.fn(),
    fill: jest.fn(),
    roundRect: jest.fn(),
  });
});

// ── Page import (after mocks are in place) ────────────────────────────────────

import Home from '../pages/index';

// ── Test helpers ──────────────────────────────────────────────────────────────

function setupMockRecorder(overrides = {}) {
  const { Recorder } = jest.requireMock('../components/Recorder');
  Recorder.mockClear();

  let capturedCallbacks;
  let instance;

  Recorder.mockImplementation(function (opts) {
    capturedCallbacks = opts;
    this._state = 'idle';
    Object.defineProperty(this, 'state', {
      get: () => this._state,
      configurable: true,
    });
    this.start = jest.fn(async () => {
      this._state = 'recording';
      opts.onStateChange('recording');
      opts.onTimer('00:01');
    });
    this.stop = jest.fn(() => {
      opts.onTimer('');
      this._state = 'idle';
      opts.onStateChange('idle');
    });
    // Allow per-test overrides
    Object.assign(this, overrides);
    instance = this;
  });

  return {
    getCallbacks: () => capturedCallbacks,
    getInstance: () => instance,
    RecorderMock: Recorder,
  };
}

async function renderHome() {
  let result;
  await act(async () => {
    result = render(<Home />);
  });
  return result;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Recorder button — pages/index.js', () => {
  test('renders Mula Rakam button in idle state', async () => {
    setupMockRecorder();
    await renderHome();
    expect(screen.getByRole('button', { name: /mula rakam/i })).toBeInTheDocument();
  });

  test('button is enabled initially (not disabled)', async () => {
    setupMockRecorder();
    await renderHome();
    expect(screen.getByRole('button', { name: /mula rakam/i })).not.toBeDisabled();
  });

  test('clicking Mula Rakam transitions to recording state', async () => {
    setupMockRecorder();
    await renderHome();

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /mula rakam/i }));
    });

    expect(screen.getByText('Henti Rakaman')).toBeInTheDocument();
  });

  test('clicking Henti Rakaman returns to idle state', async () => {
    setupMockRecorder();
    await renderHome();

    // Start
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /mula rakam/i }));
    });
    expect(screen.getByText('Henti Rakaman')).toBeInTheDocument();

    // Stop
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /henti rakaman/i }));
    });
    expect(screen.getByRole('button', { name: /mula rakam/i })).toBeInTheDocument();
  });

  test('shows live timer while recording', async () => {
    setupMockRecorder();
    await renderHome();

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /mula rakam/i }));
    });

    expect(screen.getByText('00:01')).toBeInTheDocument();
  });

  test('timer disappears after stopping', async () => {
    setupMockRecorder();
    await renderHome();

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /mula rakam/i }));
    });
    expect(screen.getByText('00:01')).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /henti rakaman/i }));
    });
    expect(screen.queryByText('00:01')).not.toBeInTheDocument();
  });

  test('shows Malay error message when mic is denied', async () => {
    const { getCallbacks } = setupMockRecorder();
    await renderHome();

    // Trigger the error callback that Recorder would fire on NotAllowedError
    await act(async () => {
      getCallbacks().onError(
        'Kebenaran mikrofon ditolak. Sila benarkan akses mikrofon dalam tetapan penyemak imbas.'
      );
    });

    expect(screen.getByText(/Kebenaran mikrofon ditolak/)).toBeInTheDocument();
  });

  test('button is disabled while processing', async () => {
    setupMockRecorder();
    await renderHome();

    // Simulate processing state
    const { Recorder } = jest.requireMock('../components/Recorder');
    const instance = Recorder.mock.instances[0];
    if (instance) {
      await act(async () => {
        instance._state = 'processing';
        // Manually trigger state via callback
        Recorder.mock.calls[0][0].onStateChange('processing');
      });
      expect(screen.getByRole('button', { name: /memproses/i })).toBeDisabled();
    }
  });
});

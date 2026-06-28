import os
import sys
import argparse

import torch
import librosa
import numpy as np
from transformers import WhisperProcessor, WhisperForConditionalGeneration

sys.path.insert(0, os.path.dirname(__file__))
from config import OUTPUT_DIR, MODEL_NAME, LANGUAGE, TASK, SAMPLE_RATE, MAX_INPUT_LENGTH

SUPPORTED_FORMATS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'}

_processor = None
_model     = None
_device    = None


def _load_model():
    global _processor, _model, _device

    if _model is not None:
        return

    _device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Use fine-tuned model if available, else fall back to base Whisper
    model_path = OUTPUT_DIR if os.path.isdir(OUTPUT_DIR) and os.listdir(OUTPUT_DIR) else MODEL_NAME
    source     = 'fine-tuned' if model_path == OUTPUT_DIR else 'base (openai/whisper-small)'
    print(f"[inference] Loading model from {model_path} ({source}) on {_device}…")

    _processor = WhisperProcessor.from_pretrained(model_path, language=LANGUAGE, task=TASK)
    _model     = WhisperForConditionalGeneration.from_pretrained(model_path).to(_device)
    _model.eval()

    _model.config.forced_decoder_ids = _processor.get_decoder_prompt_ids(language=LANGUAGE, task=TASK)
    _model.config.suppress_tokens    = []


def _load_audio(audio_path: str) -> np.ndarray:
    ext = os.path.splitext(audio_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format '{ext}'. Supported: {sorted(SUPPORTED_FORMATS)}")

    audio, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)

    # Clip to Whisper's hard limit
    max_samples = MAX_INPUT_LENGTH * SAMPLE_RATE
    if len(audio) > max_samples:
        print(f"[inference] Warning: audio is {len(audio)/SAMPLE_RATE:.1f}s — truncating to {MAX_INPUT_LENGTH}s")
        audio = audio[:max_samples]

    # Peak normalise
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak

    return audio


def transcribe(audio_path: str) -> str:
    """
    Transcribe an audio file to text.

    Args:
        audio_path: path to .wav, .mp3, .m4a, .flac, .ogg, or .webm file

    Returns:
        Transcribed text string
    """
    _load_model()

    audio = _load_audio(audio_path)

    inputs = _processor(
        audio,
        sampling_rate=SAMPLE_RATE,
        return_tensors='pt',
    ).input_features.to(_device)

    with torch.no_grad():
        generated_ids = _model.generate(
            inputs,
            forced_decoder_ids=_processor.get_decoder_prompt_ids(language=LANGUAGE, task=TASK),
        )

    text = _processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text.strip()


def main():
    parser = argparse.ArgumentParser(description='Transcribe an audio file using Whisper')
    parser.add_argument('--file', '-f', required=True, help='Path to audio file')
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    result = transcribe(args.file)
    print(f"\nTranscription:\n{result}")


if __name__ == '__main__':
    main()

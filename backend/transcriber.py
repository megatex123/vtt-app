import os
import logging

import torch
import librosa
import numpy as np
from transformers import WhisperProcessor, WhisperForConditionalGeneration

log = logging.getLogger(__name__)

# Paths
_BACKEND_DIR   = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT  = os.path.abspath(os.path.join(_BACKEND_DIR, '..', '..'))
MODELS_DIR     = os.path.join(_PROJECT_ROOT, 'voice-model', 'models')
BASE_MODEL     = 'openai/whisper-small'

LANGUAGE         = 'ms'
TASK             = 'transcribe'
SAMPLE_RATE      = 16_000
MAX_DURATION_S   = 30
SUPPORTED_FMTS   = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'}

# Module-level singletons — loaded once on first call
_processor  = None
_model      = None
_device     = None
_model_used = None   # 'fine-tuned' | 'base'


def _has_fine_tuned_model() -> bool:
    """True if MODELS_DIR contains a saved HuggingFace model (config.json present)."""
    return os.path.isfile(os.path.join(MODELS_DIR, 'config.json'))


def _load_model() -> None:
    global _processor, _model, _device, _model_used

    if _model is not None:
        return

    _device = 'cuda' if torch.cuda.is_available() else 'cpu'

    if _has_fine_tuned_model():
        model_path  = MODELS_DIR
        _model_used = 'fine-tuned'
        log.info('[transcriber] Fine-tuned model found at %s — loading on %s', model_path, _device)
    else:
        model_path  = BASE_MODEL
        _model_used = 'base'
        log.info('[transcriber] No fine-tuned model found in %s — loading base model (%s) on %s',
                 MODELS_DIR, BASE_MODEL, _device)

    try:
        _processor = WhisperProcessor.from_pretrained(model_path, language=LANGUAGE, task=TASK)
        _model     = WhisperForConditionalGeneration.from_pretrained(
                         model_path, low_cpu_mem_usage=False).to(_device)
        _model.eval()
        _model.config.forced_decoder_ids = _processor.get_decoder_prompt_ids(language=LANGUAGE, task=TASK)
        _model.config.suppress_tokens    = []
        log.info('[transcriber] Model ready: %s', _model_used)

    except Exception as exc:
        # Fine-tuned checkpoint corrupt or incompatible — fall back to base
        if _model_used == 'fine-tuned':
            log.warning('[transcriber] Fine-tuned model failed (%s) — falling back to base model', exc)
            _model_used = 'base'
            _processor  = WhisperProcessor.from_pretrained(BASE_MODEL, language=LANGUAGE, task=TASK)
            _model      = WhisperForConditionalGeneration.from_pretrained(
                              BASE_MODEL, low_cpu_mem_usage=False).to(_device)
            _model.eval()
            _model.config.forced_decoder_ids = _processor.get_decoder_prompt_ids(language=LANGUAGE, task=TASK)
            _model.config.suppress_tokens    = []
            log.info('[transcriber] Fallback to base model successful')
        else:
            raise


def transcribe(audio_path: str) -> dict:
    """
    Transcribe an audio file.

    Returns:
        {text, duration_seconds, model_used, language, confidence}
    """
    _load_model()

    ext = os.path.splitext(audio_path)[1].lower()
    if ext not in SUPPORTED_FMTS:
        raise ValueError(f"Unsupported format '{ext}'. Allowed: {sorted(SUPPORTED_FMTS)}")

    # Load + normalise audio
    audio, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    duration_seconds = round(len(audio) / SAMPLE_RATE, 2)

    if len(audio) > MAX_DURATION_S * SAMPLE_RATE:
        log.warning('[transcriber] Audio %.1fs > %ds limit — truncating', duration_seconds, MAX_DURATION_S)
        audio            = audio[:MAX_DURATION_S * SAMPLE_RATE]
        duration_seconds = float(MAX_DURATION_S)

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak

    inputs = _processor(
        audio, sampling_rate=SAMPLE_RATE, return_tensors='pt'
    ).input_features.to(_device)

    with torch.no_grad():
        outputs = _model.generate(
            inputs,
            forced_decoder_ids=_processor.get_decoder_prompt_ids(language=LANGUAGE, task=TASK),
            output_scores=True,
            return_dict_in_generate=True,
        )

    text = _processor.batch_decode(outputs.sequences, skip_special_tokens=True)[0].strip()

    # Confidence: average max-token probability across generated tokens
    confidence = None
    if outputs.scores:
        try:
            probs      = [torch.softmax(s, dim=-1).max().item() for s in outputs.scores]
            confidence = round(sum(probs) / len(probs), 4)
        except Exception:
            pass

    return {
        'text':             text,
        'duration_seconds': duration_seconds,
        'model_used':       _model_used,
        'language':         LANGUAGE,
        'confidence':       confidence,
    }


def model_info() -> dict:
    """Return current model status without triggering a load."""
    return {
        'model_used':        _model_used,
        'fine_tuned_exists': _has_fine_tuned_model(),
        'models_dir':        MODELS_DIR,
        'loaded':            _model is not None,
    }

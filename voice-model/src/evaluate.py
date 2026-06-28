import os
import sys
import json
from datetime import datetime

import jiwer
from datasets import load_from_disk
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import torch

sys.path.insert(0, os.path.dirname(__file__))
from config import DATA_DIR, OUTPUT_DIR, LANGUAGE, TASK, SAMPLE_RATE

RESULTS_PATH = os.path.join(os.path.dirname(OUTPUT_DIR), 'results.json')

# jiwer normalisation: lowercase, strip punctuation, collapse whitespace
TRANSFORM = jiwer.Compose([
    jiwer.ToLowerCase(),
    jiwer.RemovePunctuation(),
    jiwer.RemoveMultipleSpaces(),
    jiwer.Strip(),
    jiwer.RemoveEmptyStrings(),
    jiwer.ReduceToListOfListOfWords(),
])


def transcribe_batch(model, processor, audio_arrays, device):
    inputs = processor(
        audio_arrays,
        sampling_rate=SAMPLE_RATE,
        return_tensors='pt',
        padding=True,
    ).input_features.to(device)

    with torch.no_grad():
        generated_ids = model.generate(
            inputs,
            forced_decoder_ids=processor.get_decoder_prompt_ids(language=LANGUAGE, task=TASK),
        )

    return processor.batch_decode(generated_ids, skip_special_tokens=True)


def main():
    print("=== Whisper Evaluation ===")
    print(f"Model dir : {OUTPUT_DIR}")
    print(f"Data dir  : {DATA_DIR}")
    print()

    if not os.path.exists(OUTPUT_DIR):
        print(f"ERROR: Model not found at {OUTPUT_DIR}")
        print("Run src/train.py first.")
        sys.exit(1)

    if not os.path.exists(DATA_DIR):
        print(f"ERROR: Dataset not found at {DATA_DIR}")
        print("Run src/prepare_data.py first.")
        sys.exit(1)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")

    processor = WhisperProcessor.from_pretrained(OUTPUT_DIR)
    model     = WhisperForConditionalGeneration.from_pretrained(OUTPUT_DIR).to(device)
    model.eval()

    dataset   = load_from_disk(DATA_DIR)
    val_set   = dataset['validation']
    print(f"Validation samples: {len(val_set)}\n")

    per_sample = []
    references  = []
    predictions = []

    print(f"{'#':<4} {'Reference':<40} {'Prediction':<40} {'WER':>6}")
    print('-' * 94)

    for i, sample in enumerate(val_set):
        audio_array = sample['audio']['array']
        reference   = sample['text']

        pred_list = transcribe_batch(model, processor, [audio_array], device)
        prediction = pred_list[0]

        # Per-sample WER
        try:
            sample_wer = jiwer.wer(
                reference,
                prediction,
                truth_transform=TRANSFORM,
                hypothesis_transform=TRANSFORM,
            )
        except Exception:
            sample_wer = 1.0

        references.append(reference)
        predictions.append(prediction)
        per_sample.append({
            'index':      i,
            'filename':   sample.get('filename', f'sample_{i}'),
            'reference':  reference,
            'prediction': prediction,
            'wer':        round(sample_wer, 4),
        })

        ref_display  = reference[:37]  + '…' if len(reference)  > 40 else reference
        pred_display = prediction[:37] + '…' if len(prediction) > 40 else prediction
        print(f"{i:<4} {ref_display:<40} {pred_display:<40} {sample_wer:>6.3f}")

    # Aggregate WER over full validation set
    try:
        avg_wer = jiwer.wer(
            references,
            predictions,
            truth_transform=TRANSFORM,
            hypothesis_transform=TRANSFORM,
        )
    except Exception:
        avg_wer = sum(s['wer'] for s in per_sample) / max(len(per_sample), 1)

    print()
    print('=' * 94)
    print(f"Average WER : {avg_wer:.4f}  ({avg_wer * 100:.1f}%)")
    print(f"Samples     : {len(per_sample)}")
    print()

    # Save results JSON
    results = {
        'timestamp':    datetime.now().isoformat(),
        'model_dir':    OUTPUT_DIR,
        'language':     LANGUAGE,
        'avg_wer':      round(avg_wer, 4),
        'sample_count': len(per_sample),
        'per_sample':   per_sample,
    }

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Results saved to: {RESULTS_PATH}")


if __name__ == '__main__':
    main()

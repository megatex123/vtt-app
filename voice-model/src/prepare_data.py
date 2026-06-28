import os
import sys
import numpy as np
import pandas as pd
import librosa
import soundfile as sf
from datasets import Dataset, DatasetDict, Audio
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    AUDIO_DIR, TRANSCRIPT_PATH, DATA_DIR,
    SAMPLE_RATE, TRAIN_RATIO, VAL_RATIO, MAX_INPUT_LENGTH,
)


def load_transcripts() -> pd.DataFrame:
    df = pd.read_csv(TRANSCRIPT_PATH)
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=['filename', 'text'])
    df['filename'] = df['filename'].str.strip()
    df['text'] = df['text'].str.strip()
    return df


def load_and_preprocess_audio(filepath: str) -> np.ndarray | None:
    try:
        audio, sr = librosa.load(filepath, sr=SAMPLE_RATE, mono=True)
    except Exception as e:
        print(f"  [skip] {filepath}: {e}")
        return None

    # Drop clips longer than Whisper's hard limit
    if len(audio) / SAMPLE_RATE > MAX_INPUT_LENGTH:
        print(f"  [skip] {os.path.basename(filepath)}: exceeds {MAX_INPUT_LENGTH}s limit")
        return None

    # Normalise to [-1, 1]
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak

    return audio


def build_samples(df: pd.DataFrame) -> list[dict]:
    samples = []
    wav_files = {f for f in os.listdir(AUDIO_DIR) if f.endswith('.wav')} if os.path.isdir(AUDIO_DIR) else set()

    for _, row in df.iterrows():
        filepath = os.path.join(AUDIO_DIR, row['filename'])

        if row['filename'] not in wav_files:
            print(f"  [missing] {row['filename']} — not found in {AUDIO_DIR}")
            continue

        audio = load_and_preprocess_audio(filepath)
        if audio is None:
            continue

        samples.append({
            'audio':    {'array': audio, 'sampling_rate': SAMPLE_RATE},
            'text':     row['text'],
            'filename': row['filename'],
        })

    return samples


def save_processed_wav(samples: list[dict]) -> None:
    processed_audio_dir = os.path.join(DATA_DIR, 'audio')
    os.makedirs(processed_audio_dir, exist_ok=True)
    for s in samples:
        out_path = os.path.join(processed_audio_dir, s['filename'])
        sf.write(out_path, s['audio']['array'], SAMPLE_RATE)


def main():
    print("=== Voice Model — Data Preparation ===")
    print(f"Audio dir : {AUDIO_DIR}")
    print(f"Transcripts: {TRANSCRIPT_PATH}")
    print(f"Output dir : {DATA_DIR}")
    print()

    df = load_transcripts()
    print(f"Transcripts loaded: {len(df)} rows")

    samples = build_samples(df)
    total = len(samples)
    print(f"Valid samples after preprocessing: {total}")

    if total == 0:
        print("\nNo valid samples found. Add .wav files to voice-model/data/audio/ and rerun.")
        return

    # Train / val split
    train_samples, val_samples = train_test_split(
        samples,
        test_size=VAL_RATIO,
        random_state=42,
        shuffle=True,
    )

    # Build HuggingFace DatasetDict
    def to_hf(sample_list):
        return Dataset.from_list([
            {'audio': s['audio'], 'text': s['text'], 'filename': s['filename']}
            for s in sample_list
        ]).cast_column('audio', Audio(sampling_rate=SAMPLE_RATE))

    dataset = DatasetDict({
        'train':      to_hf(train_samples),
        'validation': to_hf(val_samples),
    })

    os.makedirs(DATA_DIR, exist_ok=True)
    dataset.save_to_disk(DATA_DIR)

    # Also save processed wavs for inspection
    save_processed_wav(samples)

    print()
    print("=== Summary ===")
    print(f"Total samples : {total}")
    print(f"Train         : {len(train_samples)} ({len(train_samples)/total*100:.0f}%)")
    print(f"Validation    : {len(val_samples)} ({len(val_samples)/total*100:.0f}%)")
    print(f"Sample rate   : {SAMPLE_RATE} Hz")
    print(f"Saved to      : {DATA_DIR}")
    print("\nDone. Run src/train.py next.")


if __name__ == '__main__':
    main()

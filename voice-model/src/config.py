import os

# Model
MODEL_NAME = 'openai/whisper-small'
LANGUAGE   = 'ms'       # Malay
TASK       = 'transcribe'

# Paths (relative to project root: /home/penyahpepijat/claude)
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE_DIR, 'voice-model', 'data', 'processed')
AUDIO_DIR  = os.path.join(BASE_DIR, 'voice-model', 'data', 'audio')
TRANSCRIPT_PATH = os.path.join(BASE_DIR, 'voice-model', 'data', 'transcripts.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, 'voice-model', 'models')

# Training hyperparameters
EPOCHS          = 10
BATCH_SIZE      = 8
LEARNING_RATE   = 1e-5
MAX_INPUT_LENGTH = 30   # seconds — Whisper hard limit

# Dataset split
TRAIN_RATIO = 0.8
VAL_RATIO   = 0.2

# Sampling
SAMPLE_RATE = 16_000    # Hz — Whisper requires 16kHz mono

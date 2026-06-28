import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Union

import torch
import numpy as np
import evaluate as evaluate_lib
from datasets import load_from_disk
from transformers import (
    WhisperProcessor,
    WhisperForConditionalGeneration,
    WhisperFeatureExtractor,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
)

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    MODEL_NAME, DATA_DIR, OUTPUT_DIR,
    EPOCHS, BATCH_SIZE, LEARNING_RATE,
    LANGUAGE, TASK, SAMPLE_RATE,
)

wer_metric = evaluate_lib.load('wer')


@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: WhisperProcessor

    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        # Pad input audio features
        input_features = [{'input_features': f['input_features']} for f in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors='pt')

        # Pad label sequences, replace padding token id with -100 so loss ignores them
        label_features = [{'input_ids': f['labels']} for f in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors='pt')
        labels = labels_batch['input_ids'].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )

        # Strip leading BOS token if decoder adds it automatically
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all():
            labels = labels[:, 1:]

        batch['labels'] = labels
        return batch


def prepare_dataset(batch, processor: WhisperProcessor):
    audio = batch['audio']
    batch['input_features'] = processor.feature_extractor(
        audio['array'],
        sampling_rate=audio['sampling_rate'],
        return_tensors='np',
    ).input_features[0]
    batch['labels'] = processor.tokenizer(batch['text']).input_ids
    return batch


def compute_metrics(pred, processor: WhisperProcessor):
    pred_ids   = pred.predictions
    label_ids  = pred.label_ids

    # Replace -100 back to pad token id for decoding
    label_ids[label_ids == -100] = processor.tokenizer.pad_token_id

    pred_str  = processor.tokenizer.batch_decode(pred_ids,  skip_special_tokens=True)
    label_str = processor.tokenizer.batch_decode(label_ids, skip_special_tokens=True)

    wer = wer_metric.compute(predictions=pred_str, references=label_str)
    return {'wer': round(wer, 4)}


def main():
    print(f"=== Whisper Fine-Tune Training ===")
    print(f"Model     : {MODEL_NAME}")
    print(f"Language  : {LANGUAGE}")
    print(f"Data dir  : {DATA_DIR}")
    print(f"Output dir: {OUTPUT_DIR}")
    print()

    if not os.path.exists(DATA_DIR):
        print(f"ERROR: Processed dataset not found at {DATA_DIR}")
        print("Run src/prepare_data.py first.")
        sys.exit(1)

    # Load processor + model
    processor = WhisperProcessor.from_pretrained(MODEL_NAME, language=LANGUAGE, task=TASK)
    model     = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME)

    # Force Malay decoding — disable multilingual auto-detection
    model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(language=LANGUAGE, task=TASK)
    model.config.suppress_tokens    = []

    # Load and map dataset
    dataset = load_from_disk(DATA_DIR)
    print(f"Dataset: {dataset}")

    dataset = dataset.map(
        lambda batch: prepare_dataset(batch, processor),
        remove_columns=dataset.column_names['train'],
        num_proc=1,
    )

    data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    training_args = Seq2SeqTrainingArguments(
        output_dir                  = OUTPUT_DIR,
        num_train_epochs            = EPOCHS,
        per_device_train_batch_size = BATCH_SIZE,
        per_device_eval_batch_size  = BATCH_SIZE,
        learning_rate               = LEARNING_RATE,
        warmup_steps                = 500,
        gradient_checkpointing      = True,
        fp16                        = torch.cuda.is_available(),
        evaluation_strategy         = 'epoch',
        save_strategy               = 'epoch',
        load_best_model_at_end      = True,
        metric_for_best_model       = 'wer',
        greater_is_better           = False,   # lower WER is better
        logging_steps               = 100,
        predict_with_generate       = True,
        generation_max_length       = 225,
        report_to                   = 'none',
        push_to_hub                 = False,
    )

    trainer = Seq2SeqTrainer(
        model         = model,
        args          = training_args,
        train_dataset = dataset['train'],
        eval_dataset  = dataset['validation'],
        tokenizer     = processor.feature_extractor,
        data_collator = data_collator,
        compute_metrics = lambda pred: compute_metrics(pred, processor),
    )

    print("Starting training…")
    trainer.train()

    print("\nSaving best model…")
    trainer.save_model(OUTPUT_DIR)
    processor.save_pretrained(OUTPUT_DIR)

    # Final evaluation
    print("\nRunning final evaluation…")
    metrics = trainer.evaluate()
    final_wer = metrics.get('eval_wer', 'N/A')
    print(f"\n=== Final WER: {final_wer} ===")
    print(f"Model saved to: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()

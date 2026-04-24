"""
Configuration constants for the meteorological fine-tuning pipeline.

Defines the calendar split (training vs testing dates), LoRA hyperparameters
for the base model, and Trainer arguments for QLoRA fine-tuning. Consumers:

    - dataset_creation.py reads get_testing_dates() and get_training_date_ranges()
    - finetuning_pipeline.py reads get_model_config() and get_training_config()

Earlier versions of this file exposed additional helpers (validate_testing_dates,
print_date_configuration, get_testing_months, etc.) and a GENERATION_CONFIG
dict. None had callers in the codebase; all were removed in the cleanup.
Inference-time generation parameters now live on the inference modules
themselves (hf_inference.py and ollama_inference.py) rather than here.
"""

from datetime import datetime
from typing import Dict, List


# ---------------------------------------------------------------------------
# Date split
# ---------------------------------------------------------------------------

# Testing uses the 30th day of six months spaced evenly across the year.
# This spacing ensures each test date has roughly 60 days of unseen weather
# variation relative to the last test date, so the held-out evaluation is
# not dominated by seasonal autocorrelation.
_TESTING_DAY = 30
_TESTING_MONTHS = (1, 3, 5, 7, 9, 11)

# Training uses days 1 through 25 of every month. Days 26-29 act as an
# unused buffer separating the end of the training window from the test
# day (30), preventing leakage from nearby dates whose weather data
# overlaps with the test date's past_days context window.
_TRAINING_DAY_START = 1
_TRAINING_DAY_END = 25


def get_testing_dates(year: int) -> List[str]:
    """
    Return the six testing dates for a given year, in YYYY-MM-DD format.

    Dates are the 30th of January, March, May, July, September, November.
    """
    return [f"{year}-{month:02d}-{_TESTING_DAY:02d}" for month in _TESTING_MONTHS]


def get_training_date_ranges(year: int) -> List[str]:
    """
    Return all training dates for a given year, in YYYY-MM-DD format.

    Uses days 1-25 of every month. February's short length is handled
    by the datetime constructor raising ValueError for invalid dates,
    which we skip silently - this affects days 26-28/29, which are
    outside the training range anyway.
    """
    training_dates: List[str] = []
    for month in range(1, 13):
        for day in range(_TRAINING_DAY_START, _TRAINING_DAY_END + 1):
            try:
                date = datetime(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                # Days 1-25 are valid in every month of every year, so
                # this branch is defensive rather than necessary. Kept
                # for robustness if the range bounds are ever widened.
                continue
            training_dates.append(date)
    return training_dates


# ---------------------------------------------------------------------------
# Model and training configuration
# ---------------------------------------------------------------------------

_DEFAULT_BATCH_SIZE = 2

# Tokenizer truncation length used during training. Must be >= the longest
# tokenized training example, otherwise the tail (task block + target
# response) is silently dropped and the model trains on headers-plus-CoT
# only. Measured distribution on the 2024 dataset at past_days=4: p50=9.4K,
# p99=11K, max=11.6K tokens. 16384 covers the max with headroom and matches
# the num_ctx ceiling used at inference so training and eval see prompts
# in the same format.
_MAX_SEQUENCE_LENGTH = 16384

# LoRA configuration for the 8B base model.
# target_modules covers all attention projections and MLP sublayers,
# which is the standard "full-coverage" LoRA setup.
MODEL_CONFIG: Dict = {
    "base_model": "meta-llama/Llama-3.1-8B-Instruct",
    "max_length": _MAX_SEQUENCE_LENGTH,
    "lora_r": 32,
    "lora_alpha": 64,
    "lora_dropout": 0.1,
    "target_modules": [
        "q_proj", "v_proj", "k_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
}

# Trainer arguments for QLoRA fine-tuning on an RTX A6000 (48GB VRAM).
# NOTE: the dtype selection (fp16 vs bf16) is controlled by the
# MeteorologyFineTuner constructor's torch_dtype argument, not from this
# dict. The finetuning pipeline maps torch_dtype to TrainingArguments'
# bf16/fp16 boolean flags at call time, so any fp16/bf16 value set here
# would be silently overridden. The earlier version of this file had an
# "fp16: True" entry which was dead; removed in the cleanup.
# Step-budget math for the current dataset (~289 training examples at
# past_days=4): steps_per_epoch = ceil(289 / (batch*grad_accum)) and
# total_steps = steps_per_epoch * epochs. The settings below are tuned to
# that scale so warmup finishes early, checkpoints fire a few times, and
# logs are dense enough to see the loss curve.
#
# Changed from the previous version:
#   - warmup_steps=100 -> warmup_ratio=0.05. The previous value was >3x
#     the total optimizer step count, so learning rate never reached the
#     configured 2e-4 and training was effectively dead. warmup_ratio
#     auto-scales with step count.
#   - gradient_accumulation_steps 4 -> 1. grad_accum*batch=32 on a
#     289-example dataset gave only ~10 steps/epoch; at grad_accum=1 we
#     get ~36 steps/epoch, so the LR schedule has runway to actually
#     move LoRA weights. VRAM headroom at seq=16384 is fine thanks to
#     gradient checkpointing (enabled by prepare_model_for_kbit_training).
#   - save_steps / eval_steps 200 -> 40. At the previous value, neither
#     fired before end-of-training. 40 gives ~3 intermediate checkpoints
#     across the run.
TRAINING_CONFIG: Dict = {
    "num_train_epochs": 3,
    "learning_rate": 2e-4,
    "warmup_ratio": 0.05,
    "per_device_train_batch_size": _DEFAULT_BATCH_SIZE,
    "gradient_accumulation_steps": 1,
    "logging_steps": 10,
    "save_steps": 40,
    "eval_steps": 40,
    "save_total_limit": 3,
}


def get_model_config() -> Dict:
    """Return a copy of the LoRA + base model configuration."""
    return MODEL_CONFIG.copy()


def get_training_config() -> Dict:
    """Return a copy of the Trainer argument configuration."""
    return TRAINING_CONFIG.copy()

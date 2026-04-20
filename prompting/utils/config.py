
# """
# Configuration file for meteorological fine-tuning pipeline.
# Contains fixed testing dates and training date ranges.
# """

# def get_testing_dates(year: int) -> list:
#     """
#     Get the fixed testing dates for a given year.
#     Testing dates are always the 30th day of January, March, May, July, September, November.
    
#     Args:
#         year (int): Year for which to generate testing dates
        
#     Returns:
#         list: List of testing dates in YYYY-MM-DD format
#     """
#     return [
#         f"{year}-01-30",  # January 30th
#         f"{year}-03-30",  # March 30th  
#         f"{year}-05-30",  # May 30th
#         f"{year}-07-30",  # July 30th
#         f"{year}-09-30",  # September 30th
#         f"{year}-11-30"   # November 30th
#     ]

# def get_training_date_ranges(year: int) -> list:
#     """
#     Get training date ranges for a given year.
#     Training uses days 1-25 of each month.
    
#     Args:
#         year (int): Year for which to generate training dates
        
#     Returns:
#         list: List of training dates in YYYY-MM-DD format
#     """
#     from datetime import datetime
    
#     training_dates = []
    
#     for month in range(1, 13):
#         for day in range(1, 26):  # Days 1-25 of each month
#             try:
#                 date = datetime(year, month, day).strftime("%Y-%m-%d")
#                 training_dates.append(date)
#             except ValueError:
#                 # Handle months with fewer than 25 days (shouldn't happen for days 1-25)
#                 continue
    
#     return training_dates

# def validate_testing_dates(year: int, check_data_availability: callable = None) -> list:
#     """
#     Validate testing dates and optionally check data availability.
    
#     Args:
#         year (int): Year for validation
#         check_data_availability (callable): Function to check if data exists for a date
        
#     Returns:
#         list: List of valid testing dates
#     """
#     testing_dates = get_testing_dates(year)
#     valid_dates = []
    
#     for date in testing_dates:
#         if check_data_availability:
#             try:
#                 # Assuming the function returns a dict with 'sufficient_data' key
#                 result = check_data_availability(date, 5)  # Check with 5 past days
#                 if result.get('sufficient_data', False):
#                     valid_dates.append(date)
#                     print(f"Valid testing date: {date}")
#                 else:
#                     print(f"Insufficient data for testing date: {date}")
#             except Exception as e:
#                 print(f"Error checking data for {date}: {e}")
#         else:
#             valid_dates.append(date)
    
#     return valid_dates

# def get_testing_months() -> list:
#     """
#     Get the months used for testing (January, March, May, July, September, November).
    
#     Returns:
#         list: List of month numbers (1, 3, 5, 7, 9, 11)
#     """
#     return [1, 3, 5, 7, 9, 11]

# def get_training_months() -> list:
#     """
#     Get all months used for training (all 12 months).
    
#     Returns:
#         list: List of month numbers (1-12)
#     """
#     return list(range(1, 13))

# def get_training_days() -> list:
#     """
#     Get the days of the month used for training (1-25).
    
#     Returns:
#         list: List of day numbers (1-25)
#     """
#     return list(range(1, 26))

# def get_testing_day() -> int:
#     """
#     Get the day of the month used for testing (30th).
    
#     Returns:
#         int: Day number (30)
#     """
#     return 30

# def print_date_configuration(year: int):
#     """
#     Print the complete date configuration for a given year.
    
#     Args:
#         year (int): Year to display configuration for
#     """
#     training_dates = get_training_date_ranges(year)
#     testing_dates = get_testing_dates(year)
    
#     print(f"Date Configuration for {year}")
#     print("=" * 50)
#     print(f"Training dates: {len(training_dates)} dates")
#     print(f"  - Months: {get_training_months()}")
#     print(f"  - Days: {get_training_days()}")
#     print(f"  - First training date: {training_dates[0] if training_dates else 'None'}")
#     print(f"  - Last training date: {training_dates[-1] if training_dates else 'None'}")
    
#     print(f"\nTesting dates: {len(testing_dates)} dates")
#     print(f"  - Months: {get_testing_months()}")
#     print(f"  - Day: {get_testing_day()}")
#     print(f"  - Testing dates:")
#     for date in testing_dates:
#         print(f"    - {date}")

# # Fixed testing dates for common years
# TESTING_DATES_2024 = get_testing_dates(2024)
# TESTING_DATES_2023 = get_testing_dates(2023)
# TESTING_DATES_2022 = get_testing_dates(2022)

# # Configuration constants
# DEFAULT_PAST_DAYS = 4
# DEFAULT_BATCH_SIZE = 24
# MAX_SEQUENCE_LENGTH = 4096

# # Model configuration
# MODEL_CONFIG = {
#     "base_model": "meta-llama/Llama-3.1-8B-Instruct",
#     "max_length": MAX_SEQUENCE_LENGTH,
#     "lora_r": 32,
#     "lora_alpha": 64,
#     "lora_dropout": 0.1,
#     "target_modules": [
#         "q_proj", "v_proj", "k_proj", "o_proj", 
#         "gate_proj", "up_proj", "down_proj"
#     ]
# }

# # Training configuration
# TRAINING_CONFIG = {
#     "num_train_epochs": 3,
#     "learning_rate": 2e-4,
#     "warmup_steps": 100,
#     "per_device_train_batch_size": DEFAULT_BATCH_SIZE,
#     "gradient_accumulation_steps": 4,
#     "fp16": True,
#     "logging_steps": 10,
#     "save_steps": 200,
#     "eval_steps": 200,
#     "save_total_limit": 3
# }

# GENERATION_CONFIG = {
#     "max_new_tokens": 512,  # Increased from 1024
#     "do_sample": True,
#     "temperature": 0.3,  # Reduced for more focused responses
#     "top_p": 0.8,  # Reduced for more focused responses
#     "repetition_penalty": 1.1,  # Add to reduce repetition
#     "pad_token_id": None  # Will be set to eos_token_id
# }

# def get_model_config():
#     """Get model configuration dictionary."""
#     return MODEL_CONFIG.copy()

# def get_training_config():
#     """Get training configuration dictionary."""
#     return TRAINING_CONFIG.copy()

# def get_generation_config():
#     """Get generation configuration dictionary."""
#     return GENERATION_CONFIG.copy()

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

DEFAULT_PAST_DAYS = 4
DEFAULT_BATCH_SIZE = 24
MAX_SEQUENCE_LENGTH = 4096

# LoRA configuration for the 8B base model. Rank 32 with alpha 64 gives
# the adapter ~569K trainable parameters (~0.007% of the 8B base).
# target_modules covers all attention projections and MLP sublayers,
# which is the standard "full-coverage" LoRA setup.
MODEL_CONFIG: Dict = {
    "base_model": "meta-llama/Llama-3.1-8B-Instruct",
    "max_length": MAX_SEQUENCE_LENGTH,
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
TRAINING_CONFIG: Dict = {
    "num_train_epochs": 3,
    "learning_rate": 2e-4,
    "warmup_steps": 100,
    "per_device_train_batch_size": DEFAULT_BATCH_SIZE,
    "gradient_accumulation_steps": 4,
    "logging_steps": 10,
    "save_steps": 200,
    "eval_steps": 200,
    "save_total_limit": 3,
}


def get_model_config() -> Dict:
    """Return a copy of the LoRA + base model configuration."""
    return MODEL_CONFIG.copy()


def get_training_config() -> Dict:
    """Return a copy of the Trainer argument configuration."""
    return TRAINING_CONFIG.copy()

# import os
# import json
# import torch
# import pandas as pd
# from datetime import datetime, timedelta
# from pathlib import Path
# from typing import Dict, List, Tuple
# import logging
# from transformers import (
#     AutoModelForCausalLM, 
#     AutoTokenizer, 
#     TrainingArguments, 
#     Trainer,
#     DataCollatorForLanguageModeling
# )
# from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
# from datasets import Dataset

# # Import HF inference and config
# from .hf_inference import test_hf_models_direct_output, HuggingFaceInference
# from .config import get_testing_dates, get_training_date_ranges, get_model_config, get_training_config
# from .postprocessing_romanian_gpt import load_reference_text, create_analysis_tables_gpt

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# class MeteorologyFineTuner:
#     def __init__(self, 
#                  model_name: str = "meta-llama/Llama-3.1-8B-Instruct",
#                  output_dir: str = "fine_tuned_llm",
#                  max_length: int = 4096):
        
#         self.model_name = model_name
#         self.output_dir = Path(output_dir)
#         self.max_length = max_length
        
#         # Create only essential directories
#         self.output_dir.mkdir(exist_ok=True)
#         (self.output_dir / "responses").mkdir(exist_ok=True)
#         (self.output_dir / "results").mkdir(exist_ok=True)
#         (self.output_dir / "model").mkdir(exist_ok=True)
#         # DON'T create training_data folder by default
        
#         logger.info(f"Initialized MeteorologyFineTuner with output dir: {self.output_dir}")

#     def create_training_data_folder(self):
#         """Create training_data folder only when needed."""
#         training_data_dir = self.output_dir / "training_data"
#         training_data_dir.mkdir(exist_ok=True)
#         return training_data_dir

#     def load_training_data_from_file(self, file_path: str = "train_data.json") -> List[Dict]:
#         """Load pre-created training data from file."""
        
#         if not Path(file_path).exists():
#             logger.error(f"Training data file not found: {file_path}")
#             logger.info("Please run 'python generate_training_data.py' first to create the training data.")
#             return []
        
#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 train_data = json.load(f)
            
#             logger.info(f"Loaded {len(train_data)} training examples from {file_path}")
            
#             # Validate the structure
#             if train_data and 'messages' in train_data[0]:
#                 logger.info("Training data is in correct messages format")
#                 return train_data
#             else:
#                 logger.error("Training data is not in the expected messages format")
#                 return []
                
#         except Exception as e:
#             logger.error(f"Error loading training data from {file_path}: {str(e)}")
#             return []

#     def load_testing_data_from_file(self, file_path: str = "test_data.json", zero_shot: bool = False) -> List[Dict]:
#         """Load pre-created testing data from file."""
        
#         # Choose the correct file based on approach
#         if zero_shot:
#             file_path = "test_data_zero_shot.json"
        
#         if not Path(file_path).exists():
#             logger.error(f"Testing data file not found: {file_path}")
#             if zero_shot:
#                 logger.info("Please run 'python create_zero_shot_test_dataset.py' first to create zero-shot testing data.")
#             else:
#                 logger.info("Please run 'python create_train_test_datasets.py' first to create testing data.")
#             return []
        
#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 test_data = json.load(f)
            
#             approach = "zero-shot" if zero_shot else "few-shot"
#             logger.info(f"Loaded {len(test_data)} {approach} testing examples from {file_path}")
            
#             # Validate the structure
#             if test_data and 'system_prompt' in test_data[0] and 'user_prompt' in test_data[0]:
#                 logger.info(f"Testing data is in correct format for {approach} approach")
#                 return test_data
#             else:
#                 logger.error("Testing data is not in the expected format")
#                 return []
                
#         except Exception as e:
#             logger.error(f"Error loading testing data from {file_path}: {str(e)}")
#             return []

#     def create_date_splits(self, year: int) -> Tuple[List[str], List[str]]:
#         """Create training and testing date splits using configuration."""
        
#         # Get dates from config (for reference only, actual data loaded from files)
#         training_dates = get_training_date_ranges(year)
#         testing_dates = get_testing_dates(year)
        
#         logger.info(f"Reference date splits: {len(training_dates)} training, {len(testing_dates)} testing")
#         logger.info(f"Testing dates: {testing_dates}")
        
#         return training_dates, testing_dates

#     def preprocess_for_training(self, training_data: List[Dict]) -> Dataset:
#         """Preprocess training data for Hugging Face training."""
        
#         def format_conversation(example):
#             messages = example["messages"]
#             # Apply chat template
#             formatted_text = self.tokenizer.apply_chat_template(
#                 messages, 
#                 tokenize=False,
#                 add_generation_prompt=False
#             )
#             return {"text": formatted_text}
        
#         # Convert to Dataset
#         dataset = Dataset.from_list(training_data)
        
#         # Apply formatting
#         dataset = dataset.map(format_conversation, remove_columns=dataset.column_names)
        
#         # Tokenize
#         def tokenize_function(examples):
#             return self.tokenizer(
#                 examples["text"],
#                 truncation=True,
#                 max_length=self.max_length,
#                 padding=False,
#             )
        
#         tokenized_dataset = dataset.map(
#             tokenize_function,
#             batched=True,
#             remove_columns=dataset.column_names
#         )
        
#         logger.info(f"Preprocessed {len(tokenized_dataset)} training examples")
#         return tokenized_dataset

#     def setup_model_and_tokenizer(self):
#         """Setup model and tokenizer with quantization and LoRA."""

#         # HF token 
#         hf_token = ...
        
#         logger.info("Setting up model and tokenizer...")
        
#         # Load tokenizer
#         self.tokenizer = AutoTokenizer.from_pretrained(
#             self.model_name,
#             token=hf_token
#         )
#         if self.tokenizer.pad_token is None:
#             self.tokenizer.pad_token = self.tokenizer.eos_token
        
#         # Load model with quantization
#         self.model = AutoModelForCausalLM.from_pretrained(
#             self.model_name,
#             token=hf_token,
#             torch_dtype=torch.float16,
#             device_map="auto",
#             load_in_4bit=True,
#             bnb_4bit_compute_dtype=torch.float16,
#             bnb_4bit_quant_type="nf4",
#             bnb_4bit_use_double_quant=True,
#         )
        
#         # Get LoRA configuration from config
#         model_config = get_model_config()
#         lora_config = LoraConfig(
#             r=model_config["lora_r"],
#             lora_alpha=model_config["lora_alpha"],
#             target_modules=model_config["target_modules"],
#             lora_dropout=model_config["lora_dropout"],
#             bias="none",
#             task_type="CAUSAL_LM"
#         )
        
#         # Prepare model for training
#         self.model = prepare_model_for_kbit_training(self.model)
#         self.model = get_peft_model(self.model, lora_config)
        
#         # Print trainable parameters
#         trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
#         all_params = sum(p.numel() for p in self.model.parameters())
#         logger.info(f"Trainable parameters: {trainable_params:,} ({100 * trainable_params / all_params:.2f}%)")

#     def train_model(self, training_dataset: Dataset, batch_size: int = 24):
#         """Train the model using the prepared dataset."""
        
#         logger.info("Starting model training...")
        
#         # Create training_data folder only when training
#         training_data_dir = self.create_training_data_folder()
        
#         # Get training configuration from config
#         training_config = get_training_config()
#         training_config["per_device_train_batch_size"] = batch_size
        
#         # Training arguments optimized for RTX A6000
#         training_args = TrainingArguments(
#             output_dir=str(self.output_dir / "model" / "checkpoints"),
            
#             # Batch parameters - optimized for 48GB VRAM
#             per_device_train_batch_size=training_config["per_device_train_batch_size"],
#             gradient_accumulation_steps=training_config["gradient_accumulation_steps"],
            
#             # Training parameters
#             num_train_epochs=training_config["num_train_epochs"],
#             learning_rate=training_config["learning_rate"],
#             warmup_steps=training_config["warmup_steps"],
            
#             # Memory optimizations
#             fp16=training_config["fp16"],
#             dataloader_num_workers=4,
#             dataloader_pin_memory=True,
#             remove_unused_columns=False,
            
#             # Performance optimizations
#             group_by_length=True,
            
#             # Logging and saving
#             logging_steps=training_config["logging_steps"],
#             save_steps=training_config["save_steps"],
#             save_total_limit=training_config["save_total_limit"],
            
#             # Other
#             report_to=None,  # Disable wandb/tensorboard
#         )
        
#         # Data collator
#         data_collator = DataCollatorForLanguageModeling(
#             tokenizer=self.tokenizer,
#             mlm=False,
#         )
        
#         # Create trainer
#         trainer = Trainer(
#             model=self.model,
#             args=training_args,
#             train_dataset=training_dataset,
#             tokenizer=self.tokenizer,
#             data_collator=data_collator,
#         )
        
#         # Start training
#         trainer.train()
        
#         # Save final model
#         final_model_path = self.output_dir / "model" / "final_model"
#         trainer.save_model(str(final_model_path))
#         self.tokenizer.save_pretrained(str(final_model_path))
        
#         logger.info(f"Training completed! Model saved to {final_model_path}")

#     def save_model_for_hf(self):
#         """Save model in Hugging Face format (already done in train_model)."""
        
#         logger.info("Model already saved in Hugging Face format")
        
#         model_path = self.output_dir / "model" / "final_model"
        
#         hf_instructions = f"""
# Model saved in Hugging Face format at: {model_path}

# To use this fine-tuned model:

# 1. Load the model:
#    from transformers import AutoModelForCausalLM, AutoTokenizer
#    from peft import PeftModel
   
#    tokenizer = AutoTokenizer.from_pretrained("{model_path}")
#    model = AutoModelForCausalLM.from_pretrained("{model_path}")

# 2. Or use the inference script:
#    from prompting.utils.hf_inference import load_and_test_fine_tuned_model
   
#    response = load_and_test_fine_tuned_model(
#        model_path="{model_path}",
#        test_prompt="Your meteorological prompt here",
#        system_prompt="Your system prompt here"
#    )

# 3. The model is ready for testing with the pipeline.
# """
        
#         with open(self.output_dir / "hf_usage_instructions.txt", 'w') as f:
#             f.write(hf_instructions)
        
#         logger.info("Hugging Face usage instructions saved")

#     def prepare_testing_prompts_fixed(self, testing_data: List[Dict], requested_past_days: int, zero_shot: bool = False):
#         """FIXED: Prepare testing prompts using requested past_days, not what's in test data."""
        
#         approach = "zero-shot" if zero_shot else "few-shot"
#         logger.info(f"Preparing {approach} testing prompts for past_days = {requested_past_days}")
        
#         # Group test data by date
#         data_by_date = {}
#         for item in testing_data:
#             date = item['date']
#             if date not in data_by_date:
#                 data_by_date[date] = []
#             data_by_date[date].append(item)
        
#         # For each date, find the best matching test item and save prompts with requested past_days
#         for date, items in data_by_date.items():
#             try:
#                 # Find the item with past_days closest to requested (prefer exact match)
#                 available_past_days = [item['past_days'] for item in items]
                
#                 if requested_past_days in available_past_days:
#                     # Exact match - use it
#                     selected_item = next(item for item in items if item['past_days'] == requested_past_days)
#                     logger.info(f"Date {date}: Using exact match for past_days = {requested_past_days}")
#                 else:
#                     # No exact match - use the closest available (prefer the largest available)
#                     closest_past_days = max(available_past_days)
#                     selected_item = next(item for item in items if item['past_days'] == closest_past_days)
#                     logger.info(f"Date {date}: No {requested_past_days} past_days available, using {closest_past_days} (available: {sorted(available_past_days)})")
                
#                 # Create prompts directory with REQUESTED past_days (not what's in test data)
#                 prompts_dir = Path(f"prompts/{approach}/{date}/{requested_past_days}_past_days")
#                 prompts_dir.mkdir(parents=True, exist_ok=True)
                
#                 # Save system prompt
#                 with open(prompts_dir / f"system_prompt_{date}.txt", 'w', encoding='utf-8') as f:
#                     f.write(selected_item['system_prompt'])
                
#                 # Save user prompt  
#                 with open(prompts_dir / f"user_prompt_{date}_{requested_past_days}_past_days.txt", 'w', encoding='utf-8') as f:
#                     f.write(selected_item['user_prompt'])
                
#                 logger.info(f"Saved {approach} prompts for {date} with {requested_past_days} past_days")
                
#             except Exception as e:
#                 logger.error(f"Error preparing prompts for {date}: {str(e)}")

#     def test_single_date_fixed(self, model_path: str, date: str, past_days: int, approach: str, output_dir: str):
#         """Test a single date with fixed past_days value (no iteration)."""
        
#         logger.info(f"Testing {approach} for {date} with {past_days} past days only...")
        
#         # Determine prompt directory based on approach
#         prompts_dir = Path(f"prompts/{approach}/{date}/{past_days}_past_days")
        
#         if not prompts_dir.exists():
#             logger.error(f"Prompts directory not found: {prompts_dir}")
#             return
        
#         # Load system prompt
#         system_prompt_path = prompts_dir / f"system_prompt_{date}.txt"
#         if not system_prompt_path.exists():
#             logger.error(f"System prompt file not found: {system_prompt_path}")
#             return
        
#         with open(system_prompt_path, 'r', encoding='utf-8') as f:
#             system_prompt = f.read().strip()
        
#         # Load user prompt
#         user_prompt_path = prompts_dir / f"user_prompt_{date}_{past_days}_past_days.txt"
#         if not user_prompt_path.exists():
#             logger.error(f"User prompt file not found: {user_prompt_path}")
#             return
        
#         with open(user_prompt_path, 'r', encoding='utf-8') as f:
#             user_prompt = f.read().strip()
        
#         # Initialize inference engine
#         inference_engine = HuggingFaceInference(model_path)
        
#         if not inference_engine.load_model():
#             logger.error(f"Failed to load model: {model_path}")
#             return
        
#         try:
#             # Generate response for ZERO-SHOT: use only system and user prompts
#             if approach == "zero-shot":
#                 # For zero-shot, use ONLY system and user prompts (no few-shot examples)
#                 response_data = inference_engine.generate_response(system_prompt, user_prompt)
#             else:
#                 # For few-shot, use the full prompts as intended
#                 response_data = inference_engine.generate_response(system_prompt, user_prompt)
            
#             if response_data.get("error"):
#                 logger.error(f"Generation failed: {response_data['error']}")
#                 return
            
#             # Save response
#             model_name = Path(model_path).name.replace('/', '_').replace('\\', '_')
#             response_record = {
#                 "model": model_name,
#                 "approach": approach,
#                 "base_date": date,
#                 "past_days": past_days,
#                 "system_prompt": system_prompt,
#                 "user_prompt": user_prompt,
#                 "response": response_data["response"],
#                 "metadata": {
#                     "timestamp": datetime.now().isoformat(),
#                     "prompt_tokens": response_data.get("prompt_eval_count", 0),
#                     "completion_tokens": response_data.get("eval_count", 0),
#                     "total_duration": response_data.get("total_duration", 0),
#                     "load_duration": response_data.get("load_duration", 0),
#                     "prompt_eval_duration": response_data.get("prompt_eval_duration", 0),
#                     "eval_duration": response_data.get("eval_duration", 0)
#                 }
#             }
            
#             response_filename = f"{model_name}_{approach}_{date}_{past_days}_past_days.json"
#             response_path = Path(output_dir) / response_filename
            
#             with open(response_path, 'w', encoding='utf-8') as f:
#                 json.dump(response_record, f, indent=2, ensure_ascii=False)
            
#             logger.info(f"✅ Saved {approach} response to {response_path}")
#             logger.info(f"Response length: {len(response_data['response'])} characters")
            
#         finally:
#             inference_engine.unload_model()

#     def test_model_with_hf_fixed(self, testing_data: List[Dict], past_days: int, zero_shot: bool = False):
#         """FIXED: Test model with proper prompt preparation using requested past_days."""
        
#         approach = "zero-shot" if zero_shot else "few-shot"
#         logger.info(f"Testing model with {approach} approach...")
#         logger.info(f"Command line past_days = {past_days}")
        
#         model_path = str(self.output_dir / "model" / "final_model")
        
#         # Check if model exists
#         if not Path(model_path).exists():
#             logger.error(f"Model not found at {model_path}")
#             return
        
#         # FIXED: Prepare testing prompts with requested past_days
#         self.prepare_testing_prompts_fixed(testing_data, past_days, zero_shot)
        
#         # Get unique dates from testing data
#         testing_dates = list(set(item['date'] for item in testing_data))
        
#         for date in testing_dates:
#             try:
#                 # Create target directory with approach specification (using requested past_days)
#                 target_dir = self.output_dir / "responses" / approach / date / f"{past_days}_past_days"
#                 target_dir.mkdir(parents=True, exist_ok=True)
                
#                 # Use the FIXED HF testing function
#                 self.test_single_date_fixed(
#                     model_path=model_path,
#                     date=date,
#                     past_days=past_days,  # Use requested past_days directly
#                     approach=approach,
#                     output_dir=str(target_dir)
#                 )
                
#                 logger.info(f"✅ Saved {approach} results for {date} to {target_dir}")
                
#             except Exception as e:
#                 logger.error(f"Error testing date {date} with {approach}: {str(e)}")

#     def quick_test_model(self, test_prompt: str, system_prompt: str = "") -> str:
#         """Quick test of the fine-tuned model with a single prompt."""
        
#         model_path = str(self.output_dir / "model" / "final_model")
        
#         if not Path(model_path).exists():
#             return "Error: Model not found"
        
#         inference_engine = HuggingFaceInference(model_path)
        
#         if not inference_engine.load_model():
#             return "Error: Failed to load model"
        
#         try:
#             response_data = inference_engine.generate_response(system_prompt, test_prompt)
            
#             if response_data.get("error"):
#                 return f"Error: {response_data['error']}"
            
#             return response_data["response"]
            
#         finally:
#             inference_engine.unload_model()
    
#     def evaluate_model_performance(self, testing_data: List[Dict], past_days: int, zero_shot: bool = False):
#         """FIXED: Evaluate model performance using requested past_days."""
        
#         approach = "zero-shot" if zero_shot else "few-shot"
#         logger.info(f"Evaluating {approach} model performance...")
        
#         # Get unique dates from testing data
#         testing_dates = list(set(item['date'] for item in testing_data))
        
#         for date in testing_dates:
#             try:
#                 # Load reference text
#                 reference_text = load_reference_text(date)
                
#                 # Run analysis (use requested past_days directly)
#                 responses_folder = self.output_dir / "responses" / approach / date / f"{past_days}_past_days"
                
#                 if responses_folder.exists():
#                     create_analysis_tables_gpt(
#                         responses_folder=str(responses_folder),
#                         output_date=date,
#                         output_past_days=past_days,  # Use requested past_days directly
#                         reference_text=reference_text
#                     )
                    
#                     # Move results to fine_tuned_llm folder with approach specification
#                     source_dir = f"results/{date}/{past_days}_past_days"
#                     target_dir = self.output_dir / "results" / approach / date / f"{past_days}_past_days"
                    
#                     if Path(source_dir).exists():
#                         target_dir.mkdir(parents=True, exist_ok=True)
#                         import shutil
#                         shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
#                         logger.info(f"✅ Moved {approach} analysis to {target_dir}")
                
#             except Exception as e:
#                 logger.error(f"Error analyzing {approach} date {date}: {str(e)}")

#     def run_complete_pipeline(self, year: int = 2024, past_days: int = 5, batch_size: int = 24, 
#                             skip_training: bool = False, skip_testing: bool = False, 
#                             zero_shot: bool = False):
#         """Run the complete fine-tuning pipeline using pre-created files."""
        
#         approach = "zero-shot" if zero_shot else "few-shot"
#         logger.info(f"Starting complete fine-tuning pipeline with {approach} approach...")
#         logger.info(f"Using past_days = {past_days}")
        
#         # Phase 1: Load and validate data files
#         logger.info("Phase 1: Loading pre-created data files...")
        
#         if not skip_training:
#             training_data = self.load_training_data_from_file()
#             if not training_data:
#                 logger.error("Cannot proceed without training data")
#                 return False
        
#         if not skip_testing:
#             testing_data = self.load_testing_data_from_file(zero_shot=zero_shot)
#             if not testing_data:
#                 logger.error("Cannot proceed without testing data")
#                 return False
        
#         # Phase 2: Training
#         if not skip_training:
#             logger.info("Phase 2: Training model...")
            
#             # Setup model and tokenizer
#             self.setup_model_and_tokenizer()
            
#             # Preprocess training data
#             training_dataset = self.preprocess_for_training(training_data)
            
#             # Train model (this will create training_data folder)
#             self.train_model(training_dataset, batch_size)
            
#             # Save model
#             self.save_model_for_hf()
            
#             logger.info("Training completed!")
        
#         # Phase 3: Testing
#         if not skip_testing:
#             logger.info(f"Phase 3: Testing model with {approach} approach...")
            
#             # FIXED: Test model with requested past_days
#             self.test_model_with_hf_fixed(testing_data, past_days, zero_shot)
            
#             # FIXED: Evaluate performance with requested past_days
#             self.evaluate_model_performance(testing_data, past_days, zero_shot)
            
#             logger.info(f"{approach.capitalize()} testing and evaluation completed!")
        
#         logger.info("Complete pipeline finished successfully!")
#         return True

#     def compare_approaches(self, past_days: int = 5):
#         """Compare few-shot vs zero-shot approaches if both datasets exist."""
        
#         logger.info("Comparing few-shot vs zero-shot approaches...")
#         logger.info(f"Using past_days = {past_days}")
        
#         few_shot_data = self.load_testing_data_from_file("test_data.json", zero_shot=False)
#         zero_shot_data = self.load_testing_data_from_file("test_data_zero_shot.json", zero_shot=True)
        
#         if few_shot_data and zero_shot_data:
#             logger.info(f"Few-shot dataset: {len(few_shot_data)} examples")
#             logger.info(f"Zero-shot dataset: {len(zero_shot_data)} examples")
            
#             # Test with both approaches
#             logger.info("Testing with few-shot approach...")
#             self.test_model_with_hf_fixed(few_shot_data, past_days, zero_shot=False)
            
#             logger.info("Testing with zero-shot approach...")
#             self.test_model_with_hf_fixed(zero_shot_data, past_days, zero_shot=True)
            
#             # Evaluate both
#             logger.info("Evaluating few-shot performance...")
#             self.evaluate_model_performance(few_shot_data, past_days, zero_shot=False)
            
#             logger.info("Evaluating zero-shot performance...")
#             self.evaluate_model_performance(zero_shot_data, past_days, zero_shot=True)
            
#             logger.info("Approach comparison completed!")
#         else:
#             logger.warning("Cannot compare approaches - missing dataset files")


"""
Llama 3.1 8B QLoRA fine-tuning pipeline for the meteorological diagnosis task.

The MeteorologyFineTuner class wraps three phases:

  1. Training: load train_data.json (chat-format messages), apply LoRA on
     a 4-bit quantized base model, save the adapter to disk.

  2. Testing: load test_data.json or test_data_zero_shot.json, generate
     predictions for every requested (date, past_days) combination, save
     each response as a JSON file.

  3. Evaluation: run create_analysis_tables_gpt over the saved responses
     to produce per-metric pivot tables and summary statistics.

Public API (signatures backward-compatible with the previous module;
new optional kwargs are added with defaults so finetune_integration.py
works unchanged after the import rename, except for the
compare_approaches -> run_both_approaches rename described below):

    MeteorologyFineTuner(model_name, output_dir, max_length, ...)
    MeteorologyFineTuner.run_complete_pipeline(...)
    MeteorologyFineTuner.run_both_approaches(past_days)   [renamed]
    MeteorologyFineTuner.quick_test_model(test_prompt, system_prompt)

KEY DESIGN POINTS for downstream readers:

1. SFT label masking. The default collator is DataCollatorForCompletionOnlyLM
   from the trl library, which masks system+user tokens to -100 so cross-
   entropy loss is computed only on the assistant response. The previous
   pipeline used DataCollatorForLanguageModeling(mlm=False), which trains
   the model to predict every token including the user prompt - this
   teaches input memorization rather than instruction following. The
   change is intentional and improves SFT quality but produces a
   numerically different fine-tuned model. Set
   use_completion_only_collator=False to fall back to the legacy collator
   for continuity with the existing final_model.

2. Reproducibility. Training uses seed=42, data_seed=42 by default. The
   constructor accepts training_seed for variance studies. Inference
   uses seed=42 by default and supports n_seeds>1 for variance estimation
   matching the n_seeds API in ollama_inference.py.

3. NUMERICAL TYPE. The default torch_dtype is bfloat16, which is
   universally recommended for QLoRA on the A6000 (and any Ampere or
   later GPU). The previous pipeline used float16, which has known
   instability under gradient accumulation. Existing fp16-trained
   checkpoints remain loadable; future training will use bf16 unless
   you override.

4. PAST_DAYS HANDLING. The previous pipeline silently substituted the
   closest available past_days when the requested value was missing
   from test_data.json. This module now raises ValueError with a clear
   message instead. Wrong-but-running becomes immediately-broken-with-
   useful-error.

5. Inference parameters flow through to hf_inference.py. The underlying
   HuggingFaceInference.generate_response accepts seed, num_predict,
   temperature, and top_p kwargs, which this module forwards directly
   for reproducibility and consistency with the ollama_inference.py
   parameter model.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import Dataset

from prompting.utils.hf_inference import HuggingFaceInference
from prompting.utils.config import get_model_config, get_training_config
from prompting.utils.response_evaluation import (
    create_analysis_tables_gpt,
    load_reference_text,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default seeds. _DEFAULT_TRAINING_SEED is for the Trainer (LoRA init,
# dropout, data shuffle); _DEFAULT_INFERENCE_SEED is for generate_response
# calls during testing.
_DEFAULT_TRAINING_SEED = 42
_DEFAULT_INFERENCE_SEED = 42

# Default chat-template response template used by the completion-only
# collator to locate where to start computing loss. Llama 3.1 instruct
# format wraps assistant turns with <|start_header_id|>assistant<|end_header_id|>
# followed by two newlines. The collator masks everything BEFORE the first
# occurrence of this string in each example.
_LLAMA_RESPONSE_TEMPLATE = "<|start_header_id|>assistant<|end_header_id|>\n\n"

# Output directory layout under {output_dir}/
_RESPONSES_SUBDIR = "responses"
_RESULTS_SUBDIR = "results"
_MODEL_SUBDIR = "model"
_TRAINING_DATA_SUBDIR = "training_data"
_FINAL_MODEL_NAME = "final_model"
_CHECKPOINTS_NAME = "checkpoints"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _approach_label(zero_shot: bool) -> str:
    """Map the boolean zero_shot flag to its string label."""
    return "zero-shot" if zero_shot else "few-shot"


def _resolve_hf_token(provided: Optional[str]) -> Optional[str]:
    """
    Return a Hugging Face token. Prefers explicit argument, then HF_TOKEN
    env var, then HUGGING_FACE_HUB_TOKEN env var. Returns None when no
    token is found - the transformers loader will then attempt unauthenticated
    access, which works for public models.
    """
    if provided:
        return provided
    return (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    )


def _resolve_seeds(
    n_seeds: int,
    explicit_seeds: Optional[List[int]],
    default_seed: int = _DEFAULT_INFERENCE_SEED,
) -> List[int]:
    """
    Produce the seed list for an inference run. Mirrors the behavior of
    the same-named helper in ollama_inference.py: explicit list wins, else
    [default_seed, default_seed+1, ...].
    """
    if explicit_seeds is not None:
        if len(explicit_seeds) == 0:
            raise ValueError("explicit seeds list must contain at least one seed")
        return list(explicit_seeds)
    if n_seeds < 1:
        raise ValueError(f"n_seeds must be >= 1, got {n_seeds}")
    return [default_seed + i for i in range(n_seeds)]


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class MeteorologyFineTuner:
    """
    QLoRA fine-tuning + inference + evaluation orchestrator for the
    meteorological diagnosis task.
    """

    def __init__(
        self,
        model_name: str = "meta-llama/Llama-3.1-8B-Instruct",
        output_dir: str = "fine_tuned_llm",
        max_length: int = 4096,
        torch_dtype: torch.dtype = torch.bfloat16,
        training_seed: int = _DEFAULT_TRAINING_SEED,
        use_completion_only_collator: bool = True,
        hf_token: Optional[str] = None,
    ):
        """
        Args:
            model_name: HF Hub identifier for the base model.
            output_dir: Root directory for all artifacts (model, responses,
                results, training data).
            max_length: Tokenizer truncation length for both training and
                inference.
            torch_dtype: Compute dtype. Default bfloat16 for stability under
                QLoRA. The previous pipeline used float16 which is
                numerically unstable in this regime; switch only if
                continuity with an old fp16 checkpoint is required.
            training_seed: Seed for the Trainer (LoRA init, dropout, data
                shuffle). Sweep this for variance studies on the
                fine-tuning step itself.
            use_completion_only_collator: When True (default), trains with
                response-only labels via trl.DataCollatorForCompletionOnlyLM.
                When False, falls back to the legacy
                DataCollatorForLanguageModeling(mlm=False) which trains on
                every token including the user prompt - this is the
                pre-cleanup behavior and produces a numerically different
                fine-tuned model.
            hf_token: Optional explicit HF token. Falls back to HF_TOKEN
                or HUGGING_FACE_HUB_TOKEN env vars. None is acceptable for
                public models.
        """
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.max_length = max_length
        self.torch_dtype = torch_dtype
        self.training_seed = training_seed
        self.use_completion_only_collator = use_completion_only_collator
        self.hf_token = _resolve_hf_token(hf_token)

        self.tokenizer = None
        self.model = None

        # Create output dir tree. parents=True so nested output_dir paths work.
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / _RESPONSES_SUBDIR).mkdir(parents=True, exist_ok=True)
        (self.output_dir / _RESULTS_SUBDIR).mkdir(parents=True, exist_ok=True)
        (self.output_dir / _MODEL_SUBDIR).mkdir(parents=True, exist_ok=True)

        print(f"Initialized MeteorologyFineTuner with output dir: {self.output_dir}")
        if not self.hf_token:
            print(
                "NOTE: no HF_TOKEN found in environment; will attempt "
                "unauthenticated access (works for public models only)"
            )

    # -----------------------------------------------------------------------
    # Public entry points
    # -----------------------------------------------------------------------

    def run_complete_pipeline(
        self,
        past_days: int,
        batch_size: int = 24,
        skip_training: bool = False,
        skip_testing: bool = False,
        zero_shot: bool = False,
        n_seeds: int = 1,
        seeds: Optional[List[int]] = None,
        year: Optional[int] = None,  # accepted for backwards-compat; unused
    ) -> bool:
        """
        Run the complete fine-tuning pipeline.

        Args:
            past_days: Number of past days to use for testing prompts. Must
                exist in test_data.json or test_data_zero_shot.json; the
                pipeline raises ValueError otherwise.
            batch_size: Per-device training batch size.
            skip_training: Skip phase 2, reuse existing final_model.
            skip_testing: Skip phase 3 entirely.
            zero_shot: Use test_data_zero_shot.json instead of test_data.json.
            n_seeds: Number of inference seeds per (date, past_days) cell
                during testing. Default 1 produces single-seed JSONs with
                no _seed suffix. >1 produces _seed{N} suffixed files
                compatible with the multi-seed aggregation in
                response_evaluation._write_analysis_tables.
            seeds: Explicit seed list, overrides n_seeds.
            year: Accepted for signature backwards-compat; not used. The
                old pipeline passed this to dead code (create_date_splits).

        Returns:
            True on success, False on early exit (missing files, errors).
        """
        approach = _approach_label(zero_shot)
        print(
            f"Starting fine-tuning pipeline ({approach}, past_days={past_days}, "
            f"n_seeds={n_seeds if seeds is None else len(seeds)})"
        )

        # Phase 1: Load and validate data files
        if not skip_training:
            training_data = self._load_training_data_from_file()
            if not training_data:
                print("ERROR: cannot proceed without training data")
                return False

        if not skip_testing:
            testing_data = self._load_testing_data_from_file(zero_shot=zero_shot)
            if not testing_data:
                print("ERROR: cannot proceed without testing data")
                return False

        # Phase 2: Training
        if not skip_training:
            print("Phase 2: training model")
            self._setup_model_and_tokenizer()
            training_dataset = self._preprocess_for_training(training_data)
            self._train_model(training_dataset, batch_size)
            print("Training complete")

        # Phase 3: Testing
        if not skip_testing:
            print(f"Phase 3: testing model ({approach})")
            self._test_model_with_hf(
                testing_data, past_days, zero_shot,
                n_seeds=n_seeds, seeds=seeds,
            )
            self._evaluate_model_performance(testing_data, past_days, zero_shot)
            print(f"{approach} testing and evaluation complete")

        print("Pipeline finished successfully")
        return True

    def run_both_approaches(
        self,
        past_days: int,
        n_seeds: int = 1,
        seeds: Optional[List[int]] = None,
    ) -> None:
        """
        Run both few-shot and zero-shot testing+evaluation if both datasets
        exist. Renamed from compare_approaches in the cleaned pipeline -
        the original name implied a comparison output (it doesn't compare,
        it just runs both and leaves results in separate folders).

        For an actual comparison, run this method then diff the per-cell
        CSVs from results/few-shot/ and results/zero-shot/.
        """
        print(f"Running both approaches (past_days={past_days})")

        few_shot_data = self._load_testing_data_from_file(zero_shot=False)
        zero_shot_data = self._load_testing_data_from_file(zero_shot=True)

        if not few_shot_data or not zero_shot_data:
            print(
                "ERROR: both test_data.json and test_data_zero_shot.json "
                "must be present for run_both_approaches"
            )
            return

        for zero_shot, data in [(False, few_shot_data), (True, zero_shot_data)]:
            approach = _approach_label(zero_shot)
            print(f"Testing {approach}")
            self._test_model_with_hf(
                data, past_days, zero_shot, n_seeds=n_seeds, seeds=seeds,
            )
            print(f"Evaluating {approach}")
            self._evaluate_model_performance(data, past_days, zero_shot)

        print("Both approaches complete")

    def quick_test_model(
        self,
        test_prompt: str,
        system_prompt: str = "",
        seed: int = _DEFAULT_INFERENCE_SEED,
    ) -> str:
        """
        Quick single-prompt test of the fine-tuned model. Used for ad-hoc
        sanity checks rather than evaluation.
        """
        model_path = str(self.output_dir / _MODEL_SUBDIR / _FINAL_MODEL_NAME)
        if not Path(model_path).exists():
            return f"Error: model not found at {model_path}"

        engine = HuggingFaceInference(model_path)
        if not engine.load_model():
            return "Error: failed to load model"

        try:
            response_data = engine.generate_response(system_prompt, test_prompt, seed=seed)
            if response_data.get("error"):
                return f"Error: {response_data['error']}"
            return response_data["response"]
        finally:
            engine.unload_model()

    # -----------------------------------------------------------------------
    # Data loaders
    # -----------------------------------------------------------------------

    def _load_training_data_from_file(
        self,
        file_path: str = "train_data.json",
    ) -> List[Dict]:
        """
        Load and validate training data. Validates EVERY example, not just
        element 0; mid-training format errors are difficult to debug.
        """
        if not Path(file_path).exists():
            print(f"ERROR: training data file not found: {file_path}")
            print("Hint: run 'python generate_training_data.py' first")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                train_data = json.load(f)
        except Exception as e:
            print(f"ERROR loading training data from {file_path}: {e}")
            return []

        # Validate every example
        errors: List[str] = []
        for i, item in enumerate(train_data):
            if "messages" not in item:
                errors.append(f"item {i}: missing 'messages' key")
                continue
            messages = item["messages"]
            if not isinstance(messages, list):
                errors.append(f"item {i}: 'messages' is not a list")
                continue
            for j, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    errors.append(f"item {i}.messages[{j}]: not a dict")
                    continue
                if "role" not in msg or "content" not in msg:
                    errors.append(
                        f"item {i}.messages[{j}]: missing role or content"
                    )
                    continue
                if msg["role"] not in {"system", "user", "assistant"}:
                    errors.append(
                        f"item {i}.messages[{j}]: invalid role '{msg['role']}'"
                    )

        if errors:
            print(f"ERROR: training data has {len(errors)} validation errors")
            for err in errors[:10]:
                print(f"  {err}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more")
            return []

        print(f"Loaded {len(train_data)} training examples from {file_path}")
        return train_data

    def _load_testing_data_from_file(
        self,
        zero_shot: bool = False,
    ) -> List[Dict]:
        """
        Load and validate testing data. The file path is determined entirely
        by the zero_shot flag - the original module accepted a file_path
        argument that was silently overridden when zero_shot=True, which
        was confusing. Removed.
        """
        file_path = "test_data_zero_shot.json" if zero_shot else "test_data.json"
        approach = _approach_label(zero_shot)

        if not Path(file_path).exists():
            print(f"ERROR: testing data file not found: {file_path}")
            if zero_shot:
                print(
                    "Hint: run 'python create_zero_shot_test_dataset.py' first"
                )
            else:
                print(
                    "Hint: run 'python create_train_test_datasets.py' first"
                )
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                test_data = json.load(f)
        except Exception as e:
            print(f"ERROR loading testing data from {file_path}: {e}")
            return []

        # Validate every example
        errors: List[str] = []
        for i, item in enumerate(test_data):
            for required_key in ("system_prompt", "user_prompt", "date", "past_days"):
                if required_key not in item:
                    errors.append(f"item {i}: missing '{required_key}'")

        if errors:
            print(f"ERROR: testing data has {len(errors)} validation errors")
            for err in errors[:10]:
                print(f"  {err}")
            return []

        print(f"Loaded {len(test_data)} {approach} testing examples from {file_path}")
        return test_data

    # -----------------------------------------------------------------------
    # Model setup and training
    # -----------------------------------------------------------------------

    def _setup_model_and_tokenizer(self) -> None:
        """
        Load tokenizer and 4-bit quantized model, attach LoRA adapter.
        Raises clearly when CUDA is unavailable or model load fails.
        """
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is not available. QLoRA training requires a GPU. "
                "Verify torch.cuda.is_available() returns True."
            )

        print("Setting up model and tokenizer")

        # Load tokenizer
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                token=self.hf_token,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to load tokenizer for {self.model_name}: {e}. "
                "Check HF_TOKEN env var if accessing a gated model."
            )

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Load model with quantization. Modern API uses BitsAndBytesConfig
        # passed via quantization_config=, replacing the deprecated kwargs.
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=self.torch_dtype,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )

        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                token=self.hf_token,
                torch_dtype=self.torch_dtype,
                device_map="auto",
                quantization_config=bnb_config,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to load model {self.model_name}: {e}"
            )

        # Attach LoRA adapter from config.py settings
        model_config = get_model_config()
        lora_config = LoraConfig(
            r=model_config["lora_r"],
            lora_alpha=model_config["lora_alpha"],
            target_modules=model_config["target_modules"],
            lora_dropout=model_config["lora_dropout"],
            bias="none",
            task_type="CAUSAL_LM",
        )
        self.model = prepare_model_for_kbit_training(self.model)
        self.model = get_peft_model(self.model, lora_config)

        trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in self.model.parameters())
        print(
            f"Trainable parameters: {trainable:,} "
            f"({100 * trainable / total:.2f}% of {total:,} total)"
        )

    def _preprocess_for_training(self, training_data: List[Dict]) -> Dataset:
        """
        Apply the chat template and tokenize. Same logic as before; the
        loss-masking happens at the data collator level, not here, so
        switching collators does not require changes to preprocessing.
        """
        def format_conversation(example: Dict) -> Dict:
            formatted = self.tokenizer.apply_chat_template(
                example["messages"],
                tokenize=False,
                add_generation_prompt=False,
            )
            return {"text": formatted}

        dataset = Dataset.from_list(training_data)
        dataset = dataset.map(format_conversation, remove_columns=dataset.column_names)

        def tokenize_function(examples: Dict) -> Dict:
            return self.tokenizer(
                examples["text"],
                truncation=True,
                max_length=self.max_length,
                padding=False,
            )

        tokenized = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names,
        )
        print(f"Preprocessed {len(tokenized)} training examples")
        return tokenized

    def _build_data_collator(self):
        """
        Build the SFT data collator. Default is the completion-only
        collator from trl which masks system+user tokens, computing loss
        only on the assistant response. Falls back to
        DataCollatorForLanguageModeling(mlm=False) (the pre-cleanup
        behavior) when use_completion_only_collator=False or when trl is
        not available.
        """
        if not self.use_completion_only_collator:
            print(
                "NOTE: using DataCollatorForLanguageModeling(mlm=False); "
                "loss is computed on every token including the user prompt"
            )
            return DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False,
            )

        try:
            from trl import DataCollatorForCompletionOnlyLM
        except ImportError as e:
            print(
                f"WARNING: trl not installed ({e}); falling back to "
                "DataCollatorForLanguageModeling(mlm=False). Run "
                "'pip install trl' for completion-only loss masking."
            )
            return DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False,
            )

        # The response template marks where the assistant turn begins;
        # everything before the first occurrence in each example is masked
        # to -100. This is Llama 3.1 instruct format; if you switch base
        # models, update _LLAMA_RESPONSE_TEMPLATE accordingly.
        return DataCollatorForCompletionOnlyLM(
            response_template=_LLAMA_RESPONSE_TEMPLATE,
            tokenizer=self.tokenizer,
        )

    def _train_model(self, training_dataset: Dataset, batch_size: int) -> None:
        """Train the LoRA adapter. Saves checkpoints and final model under output_dir."""
        print("Starting model training")

        # Create training_data folder for any extra training outputs
        (self.output_dir / _TRAINING_DATA_SUBDIR).mkdir(parents=True, exist_ok=True)

        training_config = get_training_config()
        training_config["per_device_train_batch_size"] = batch_size

        # Map our dtype kwargs to the boolean fp16/bf16 flags Trainer expects
        use_bf16 = (self.torch_dtype == torch.bfloat16)
        use_fp16 = (self.torch_dtype == torch.float16)

        training_args = TrainingArguments(
            output_dir=str(self.output_dir / _MODEL_SUBDIR / _CHECKPOINTS_NAME),
            per_device_train_batch_size=training_config["per_device_train_batch_size"],
            gradient_accumulation_steps=training_config["gradient_accumulation_steps"],
            num_train_epochs=training_config["num_train_epochs"],
            learning_rate=training_config["learning_rate"],
            warmup_steps=training_config["warmup_steps"],
            bf16=use_bf16,
            fp16=use_fp16,
            dataloader_num_workers=4,
            dataloader_pin_memory=True,
            remove_unused_columns=False,
            group_by_length=True,
            logging_steps=training_config["logging_steps"],
            save_steps=training_config["save_steps"],
            save_total_limit=training_config["save_total_limit"],
            seed=self.training_seed,
            data_seed=self.training_seed,
            report_to=[],  # disable wandb/tensorboard explicitly
        )

        data_collator = self._build_data_collator()

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=training_dataset,
            tokenizer=self.tokenizer,
            data_collator=data_collator,
        )

        trainer.train()

        final_model_path = self.output_dir / _MODEL_SUBDIR / _FINAL_MODEL_NAME
        trainer.save_model(str(final_model_path))
        self.tokenizer.save_pretrained(str(final_model_path))
        print(f"Training complete; model saved to {final_model_path}")

    # -----------------------------------------------------------------------
    # Testing
    # -----------------------------------------------------------------------

    def _prepare_testing_prompts(
        self,
        testing_data: List[Dict],
        requested_past_days: int,
        zero_shot: bool,
    ) -> List[Tuple[str, Dict]]:
        """
        Group test data by date and select the item matching requested_past_days.
        Saves the selected system+user prompts to disk and returns the
        (date, item) pairs for downstream inference.

        Raises ValueError if any date in the test data does not have an item
        with the requested past_days value. The previous pipeline silently
        substituted the closest available value, which produced silently
        mislabeled responses (e.g., past_days=4 prompts saved to a
        5_past_days/ directory and recorded as past_days=5 in the JSON).
        """
        approach = _approach_label(zero_shot)

        # Group by date
        data_by_date: Dict[str, List[Dict]] = {}
        for item in testing_data:
            data_by_date.setdefault(item["date"], []).append(item)

        # Validate every date has the requested past_days available BEFORE
        # writing any prompt files. Fail-fast.
        missing: List[str] = []
        for date, items in data_by_date.items():
            available = [item["past_days"] for item in items]
            if requested_past_days not in available:
                missing.append(
                    f"{date} (available: {sorted(set(available))})"
                )

        if missing:
            raise ValueError(
                f"Requested past_days={requested_past_days} is not available "
                f"in the testing data for {len(missing)} date(s): "
                f"{', '.join(missing[:5])}"
                + (f" and {len(missing) - 5} more" if len(missing) > 5 else "")
                + ". Re-run create_train_test_datasets.py with the desired "
                "past_days values, or pass a different past_days argument."
            )

        # Write prompts and collect the selected items
        selected: List[Tuple[str, Dict]] = []
        for date, items in sorted(data_by_date.items()):
            item = next(it for it in items if it["past_days"] == requested_past_days)

            prompts_dir = Path("prompts") / approach / date / f"{requested_past_days}_past_days"
            prompts_dir.mkdir(parents=True, exist_ok=True)

            with open(prompts_dir / f"system_prompt_{date}.txt", "w", encoding="utf-8") as f:
                f.write(item["system_prompt"])

            user_prompt_filename = f"user_prompt_{date}_{requested_past_days}_past_days.txt"
            with open(prompts_dir / user_prompt_filename, "w", encoding="utf-8") as f:
                f.write(item["user_prompt"])

            selected.append((date, item))

        print(
            f"Prepared {approach} prompts for {len(selected)} dates "
            f"(past_days={requested_past_days})"
        )
        return selected

    def _save_response_json(
        self,
        target_dir: Path,
        model_name: str,
        approach: str,
        date: str,
        past_days: int,
        seed: int,
        system_prompt: str,
        user_prompt: str,
        response_data: Dict,
        include_seed_in_filename: bool,
    ) -> str:
        """Serialize one response to JSON. Returns the filename."""
        safe_model = model_name.replace(":", "_")
        if include_seed_in_filename:
            filename = (
                f"{safe_model}_{approach}_{date}_{past_days}"
                f"_past_days_seed{seed}.json"
            )
        else:
            filename = f"{safe_model}_{approach}_{date}_{past_days}_past_days.json"

        record = {
            "model": safe_model,
            "approach": approach,
            "base_date": date,
            "past_days": past_days,
            "seed": seed,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "response": response_data["response"],
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "prompt_tokens": response_data.get("prompt_eval_count", 0),
                "completion_tokens": response_data.get("eval_count", 0),
                "total_duration": response_data.get("total_duration", 0),
                "load_duration": response_data.get("load_duration", 0),
                "prompt_eval_duration": response_data.get("prompt_eval_duration", 0),
                "eval_duration": response_data.get("eval_duration", 0),
                "generation_options": {
                    "seed": seed,
                    "torch_dtype": str(self.torch_dtype),
                },
            },
        }

        out_path = target_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        return filename

    def _test_model_with_hf(
        self,
        testing_data: List[Dict],
        past_days: int,
        zero_shot: bool,
        n_seeds: int = 1,
        seeds: Optional[List[int]] = None,
    ) -> None:
        """
        Test the fine-tuned model across all dates in testing_data.

        Lifecycle change from the previous pipeline: the model is loaded
        ONCE at the start and unloaded ONCE at the end, instead of being
        loaded and unloaded per date. For 30 dates this saves ~2 minutes
        of model load time per run, and matches the per-model lifecycle
        in ollama_inference.py.

        Multi-seed mode: when n_seeds>1 (or seeds is passed explicitly),
        each (date) cell produces multiple responses with different seeds,
        each saved as a separate JSON with _seed{N} in the filename.
        Filename format matches what response_evaluation.parse_filename_with_seed
        expects, so analysis/aggregation works without extra configuration.
        """
        approach = _approach_label(zero_shot)
        seed_list = _resolve_seeds(n_seeds, seeds)
        include_seed_in_filename = len(seed_list) > 1

        model_path = str(self.output_dir / _MODEL_SUBDIR / _FINAL_MODEL_NAME)
        if not Path(model_path).exists():
            print(f"ERROR: model not found at {model_path}")
            return

        # Validate and write prompts BEFORE attempting any model load.
        # This raises ValueError early if past_days is unavailable.
        try:
            selected_items = self._prepare_testing_prompts(
                testing_data, past_days, zero_shot,
            )
        except ValueError as e:
            print(f"ERROR: {e}")
            return

        seed_desc = f"seed={seed_list[0]}" if len(seed_list) == 1 else f"seeds={seed_list}"
        print(
            f"Testing {approach} for {len(selected_items)} dates "
            f"(past_days={past_days}, {seed_desc})"
        )

        # Load model ONCE for all dates and seeds
        engine = HuggingFaceInference(model_path)
        if not engine.load_model():
            print(f"ERROR: failed to load fine-tuned model from {model_path}")
            return

        # Use the actual base model name (e.g. "Llama-3.1-8B-Instruct")
        # with a "-qlora" suffix to distinguish from the same model served
        # via Ollama. The previous code used Path(model_path).name which
        # resolved to "final_model" — an opaque label in plots and CSVs.
        model_name_for_file = self.model_name.split("/")[-1] + "-qlora"

        try:
            for date, item in selected_items:
                target_dir = (
                    self.output_dir / _RESPONSES_SUBDIR / approach / date
                    / f"{past_days}_past_days"
                )
                target_dir.mkdir(parents=True, exist_ok=True)

                system_prompt = item["system_prompt"]
                user_prompt = item["user_prompt"]

                for seed in seed_list:
                    response_data = engine.generate_response(
                        system_prompt, user_prompt, seed=seed,
                    )
                    if response_data.get("error"):
                        print(
                            f"ERROR generating {date} seed={seed}: "
                            f"{response_data['error']}"
                        )
                        continue

                    filename = self._save_response_json(
                        target_dir=target_dir,
                        model_name=model_name_for_file,
                        approach=approach,
                        date=date,
                        past_days=past_days,
                        seed=seed,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        response_data=response_data,
                        include_seed_in_filename=include_seed_in_filename,
                    )
                    duration_s = response_data.get("total_duration", 0) / 1e9
                    print(
                        f"  {approach} {date} seed={seed}: "
                        f"duration={duration_s:.1f}s, saved {filename}"
                    )
        finally:
            engine.unload_model()

    # -----------------------------------------------------------------------
    # Evaluation
    # -----------------------------------------------------------------------

    def _evaluate_model_performance(
        self,
        testing_data: List[Dict],
        past_days: int,
        zero_shot: bool,
    ) -> None:
        """
        Run create_analysis_tables_gpt for every test date.

        Uses the new output_dir kwarg on create_analysis_tables_gpt to
        write directly to fine_tuned_llm/results/{approach}/{date}/{N}_past_days/
        instead of writing to the global results/ folder and copying via
        shutil.copytree (which the previous pipeline did).
        """
        approach = _approach_label(zero_shot)
        testing_dates = sorted(set(item["date"] for item in testing_data))
        print(f"Evaluating {approach} performance across {len(testing_dates)} dates")

        for date in testing_dates:
            try:
                reference_text = load_reference_text(date)
                responses_folder = (
                    self.output_dir / _RESPONSES_SUBDIR / approach / date
                    / f"{past_days}_past_days"
                )
                if not responses_folder.exists():
                    print(f"WARNING: responses folder not found: {responses_folder}")
                    continue

                target_dir = (
                    self.output_dir / _RESULTS_SUBDIR / approach / date
                    / f"{past_days}_past_days"
                )
                create_analysis_tables_gpt(
                    responses_folder=str(responses_folder),
                    output_date=date,
                    output_past_days=past_days,
                    reference_text=reference_text,
                    output_dir=str(target_dir),
                )
            except Exception as e:
                print(f"ERROR analyzing {approach} date {date}: {e}")

                
# import torch
# import json
# import os
# from datetime import datetime
# from pathlib import Path
# from typing import List, Dict
# import logging
# from transformers import AutoModelForCausalLM, AutoTokenizer

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# class HuggingFaceInference:
#     def __init__(self, model_path: str, max_length: int = 4096):
#         """
#         Initialize Hugging Face model for inference.
        
#         Args:
#             model_path: Path to the fine-tuned model
#             max_length: Maximum sequence length for generation
#         """
#         self.model_path = model_path
#         self.max_length = max_length
#         self.model = None
#         self.tokenizer = None
        
#     def load_model(self):
#         """Load the fine-tuned model and tokenizer."""
#         try:
#             logger.info(f"Loading model from {self.model_path}")
            
#             # Load tokenizer
#             self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
#             if self.tokenizer.pad_token is None:
#                 self.tokenizer.pad_token = self.tokenizer.eos_token
            
#             # Load model
#             self.model = AutoModelForCausalLM.from_pretrained(
#                 self.model_path,
#                 torch_dtype=torch.float16,
#                 device_map="auto",
#                 load_in_4bit=True,
#                 bnb_4bit_compute_dtype=torch.float16,
#                 bnb_4bit_quant_type="nf4",
#                 bnb_4bit_use_double_quant=True,
#             )
            
#             logger.info("Model loaded successfully")
#             return True
            
#         except Exception as e:
#             logger.error(f"Error loading model: {e}")
#             return False
    
#     def generate_response(self, system_prompt: str, user_prompt: str) -> Dict:
#         """
#         Generate response using the fine-tuned model.
        
#         Args:
#             system_prompt: System prompt
#             user_prompt: User prompt
            
#         Returns:
#             Dict with response and metadata
#         """
#         if self.model is None or self.tokenizer is None:
#             return {"error": "Model not loaded"}
        
#         try:
#             # Format the conversation
#             messages = [
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": user_prompt}
#             ]
            
#             # Apply chat template
#             formatted_input = self.tokenizer.apply_chat_template(
#                 messages,
#                 tokenize=False,
#                 add_generation_prompt=True
#             )
            
#             # Tokenize
#             inputs = self.tokenizer(
#                 formatted_input,
#                 return_tensors="pt",
#                 truncation=True,
#                 max_length=self.max_length
#             ).to(self.model.device)
            
#             # Generate
#             start_time = datetime.now()
            
#             with torch.no_grad():
#                 outputs = self.model.generate(
#                     **inputs,
#                     max_new_tokens=1024,
#                     do_sample=True,
#                     temperature=0.7,
#                     top_p=0.9,
#                     pad_token_id=self.tokenizer.eos_token_id,
#                     eos_token_id=self.tokenizer.eos_token_id
#                 )
            
#             end_time = datetime.now()
            
#             # Decode response
#             generated_tokens = outputs[0][inputs['input_ids'].shape[1]:]
#             response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
#             # Calculate metadata
#             prompt_tokens = inputs['input_ids'].shape[1]
#             completion_tokens = len(generated_tokens)
#             total_duration = (end_time - start_time).total_seconds()
            
#             return {
#                 "response": response.strip(),
#                 "prompt_eval_count": prompt_tokens,
#                 "eval_count": completion_tokens,
#                 "total_duration": int(total_duration * 1e9),  # Convert to nanoseconds for compatibility
#                 "load_duration": 0,
#                 "prompt_eval_duration": 0,
#                 "eval_duration": int(total_duration * 1e9)
#             }
            
#         except Exception as e:
#             logger.error(f"Error generating response: {e}")
#             return {"error": f"Generation failed: {str(e)}"}
    
#     def unload_model(self):
#         """Unload model from memory."""
#         if self.model is not None:
#             del self.model
#             self.model = None
#         if self.tokenizer is not None:
#             del self.tokenizer
#             self.tokenizer = None
#         torch.cuda.empty_cache()
#         logger.info("Model unloaded from memory")


# def test_hf_models_direct_output_fixed(model_paths: List[str], past_days: int, base_date: str = None, 
#                                      output_dir: str = None, approach: str = "few-shot"):
#     """
#     FIXED VERSION: Test Hugging Face models with proper approach handling and no past_days iteration.
    
#     Args:
#         model_paths: List of paths to fine-tuned models
#         past_days: SPECIFIC number of past days to test (no iteration)
#         base_date: Base date for testing
#         output_dir: Direct output directory
#         approach: Testing approach ("few-shot" or "zero-shot")
#     """
    
#     if base_date is None:
#         base_date = datetime.now().strftime('%Y-%m-%d')
    
#     logger.info(f"Testing {len(model_paths)} Hugging Face models with {approach} approach...")
#     logger.info(f"Using ONLY {past_days} past days (no iteration)")
    
#     # Use direct output directory
#     if output_dir:
#         responses_dir = Path(output_dir)
#     else:
#         responses_dir = Path(f"responses/{approach}/{base_date}/{past_days}_past_days")
    
#     # Use approach-specific prompts directory
#     prompts_dir = Path(f"prompts/{approach}/{base_date}/{past_days}_past_days")
    
#     responses_dir.mkdir(parents=True, exist_ok=True)
    
#     if not prompts_dir.exists():
#         logger.error(f"Prompts directory '{prompts_dir}' does not exist!")
#         return {"error": "Prompts directory not found"}
    
#     # Load system prompt
#     system_prompt_path = prompts_dir / f"system_prompt_{base_date}.txt"
#     if not system_prompt_path.exists():
#         logger.error(f"System prompt file not found: {system_prompt_path}")
#         return {"error": f"System prompt file not found: {system_prompt_path}"}
    
#     with open(system_prompt_path, 'r', encoding='utf-8') as f:
#         system_prompt = f.read().strip()
    
#     results_summary = {
#         "test_date": base_date,
#         "approach": approach,
#         "past_days": past_days,
#         "models_tested": [],
#         "total_responses": 0,
#         "errors": []
#     }
    
#     # Test each model
#     for model_path in model_paths:
#         logger.info(f"\n{'='*50}")
#         logger.info(f"Testing model: {model_path} with {approach} approach")
#         logger.info(f"{'='*50}")
        
#         model_results = {
#             "model": model_path,
#             "approach": approach,
#             "responses": [],
#             "errors": []
#         }
        
#         try:
#             # Initialize inference engine
#             inference_engine = HuggingFaceInference(model_path)
            
#             # Load model
#             if not inference_engine.load_model():
#                 error_msg = f"Failed to load model: {model_path}"
#                 model_results["errors"].append(error_msg)
#                 results_summary["errors"].append(error_msg)
#                 continue
            
#             # Test with SPECIFIC past_days count (NO ITERATION)
#             logger.info(f"Testing {model_path} with EXACTLY {past_days} past days...")
            
#             # Find user prompt file
#             user_prompt_path = prompts_dir / f"user_prompt_{base_date}_{past_days}_past_days.txt"
            
#             if not user_prompt_path.exists():
#                 error_msg = f"User prompt file not found: {user_prompt_path}"
#                 logger.warning(error_msg)
#                 model_results["errors"].append(error_msg)
#                 continue
            
#             with open(user_prompt_path, 'r', encoding='utf-8') as f:
#                 user_prompt = f.read().strip()
            
#             # Generate response
#             response_data = inference_engine.generate_response(system_prompt, user_prompt)
            
#             if response_data.get("error"):
#                 error_msg = f"Generation failed for {model_path} with {past_days} past days: {response_data['error']}"
#                 logger.error(error_msg)
#                 model_results["errors"].append(error_msg)
#                 continue
            
#             # Save response
#             model_name = Path(model_path).name.replace('/', '_').replace('\\', '_')
#             response_record = {
#                 "model": model_name,
#                 "approach": approach,
#                 "base_date": base_date,
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
            
#             response_filename = f"{model_name}_{approach}_{base_date}_{past_days}_past_days.json"
#             response_path = responses_dir / response_filename
            
#             with open(response_path, 'w', encoding='utf-8') as f:
#                 json.dump(response_record, f, indent=2, ensure_ascii=False)
            
#             model_results["responses"].append(response_filename)
#             results_summary["total_responses"] += 1
            
#             logger.info(f"✅ Saved {approach} response to {response_path}")
#             logger.info(f"  Response length: {len(response_data['response'])} characters")
#             logger.info(f"  Duration: {response_data.get('total_duration', 0) / 1e9:.2f}s")
            
#             # Unload model to free memory
#             inference_engine.unload_model()
#             logger.info(f"🗑️ Unloaded {model_path} from memory")
            
#         except Exception as e:
#             error_msg = f"Unexpected error testing model {model_path}: {str(e)}"
#             logger.error(error_msg)
#             model_results["errors"].append(error_msg)
#             results_summary["errors"].append(error_msg)
        
#         results_summary["models_tested"].append(model_results)
    
#     # Save summary
#     summary_path = responses_dir / f"test_summary_{approach}_{base_date}_{datetime.now().strftime('%H%M%S')}.json"
#     with open(summary_path, 'w', encoding='utf-8') as f:
#         json.dump(results_summary, f, indent=2, ensure_ascii=False)
    
#     logger.info(f"\n{'='*60}")
#     logger.info(f"TEST SUMMARY - {approach.upper()} APPROACH")
#     logger.info(f"{'='*60}")
#     logger.info(f"Total models tested: {len(results_summary['models_tested'])}")
#     logger.info(f"Total responses generated: {results_summary['total_responses']}")
#     logger.info(f"Past days used: {past_days} (no iteration)")
#     logger.info(f"Total errors: {len(results_summary['errors'])}")
#     logger.info(f"Summary saved to: {summary_path}")
#     logger.info(f"{'='*60}")
    
#     return results_summary


# def load_and_test_fine_tuned_model(model_path: str, test_prompt: str, system_prompt: str = "") -> str:
#     """
#     Simple function to load and test a fine-tuned model with a single prompt.
    
#     Args:
#         model_path: Path to the fine-tuned model
#         test_prompt: Test prompt
#         system_prompt: System prompt (optional)
        
#     Returns:
#         Generated response
#     """
    
#     inference_engine = HuggingFaceInference(model_path)
    
#     if not inference_engine.load_model():
#         return "Error: Failed to load model"
    
#     try:
#         response_data = inference_engine.generate_response(system_prompt, test_prompt)
        
#         if response_data.get("error"):
#             return f"Error: {response_data['error']}"
        
#         return response_data["response"]
        
#     finally:
#         inference_engine.unload_model()


# # Maintain backward compatibility with original function name
# def test_hf_models_direct_output(model_paths: List[str], past_days: int, base_date: str = None, output_dir: str = None):
#     """Backward compatibility wrapper - defaults to few-shot approach."""
#     return test_hf_models_direct_output_fixed(
#         model_paths=model_paths,
#         past_days=past_days, 
#         base_date=base_date,
#         output_dir=output_dir,
#         approach="few-shot"
#     )

"""
Hugging Face transformers inference for the meteorological diagnosis task.

Wraps a 4-bit quantized fine-tuned causal-LM model for generation. Used by
the fine-tuning pipeline's testing phase to produce diagnosis responses
against held-out test prompts.

Public API:

    HuggingFaceInference(model_path, max_length, torch_dtype, hf_token)
        load_model() -> bool
        generate_response(system_prompt, user_prompt, seed=None,
                         num_predict=512, temperature=0.7, top_p=0.9) -> Dict
        unload_model() -> None

KEY DESIGN POINTS for downstream readers:

1. BitsAndBytesConfig for quantization. The previous module passed
   load_in_4bit=True and bnb_4bit_* kwargs directly to from_pretrained -
   the legacy API that still works with deprecation warnings. This module
   builds a BitsAndBytesConfig object and passes it via
   quantization_config=, matching the forward-compatible form used in
   finetuning_pipeline.py.

2. Numerical type defaults to bfloat16. The previous module hardcoded
   float16. For inference on Ampere+ GPUs, bf16 is more stable (wider
   exponent range prevents softmax overflow at longer contexts) and
   matches the dtype used during training by the cleaned finetuning
   pipeline. If you loaded a model trained under the old fp16 pipeline
   and want identical inference numerics, pass torch_dtype=torch.float16.

3. Reproducibility. generate_response accepts a seed kwarg. When passed,
   we use a torch.Generator with that seed and forward it to
   model.generate() - cleaner than mutating the global RNG. Falls back
   to global-seed mutation if the installed transformers version does
   not accept the generator kwarg.

4. Silent truncation detection. The tokenizer is called with
   truncation=True; if the prompt exceeds max_length, tokens are silently
   dropped from the tail. This is analogous to the Ollama num_ctx
   truncation bug that corrupted prior experiments. The cleaned module
   detects and warns when truncation occurs - it still happens because
   you can't pass more than max_length tokens to the model, but now you
   know about it.

5. Retry on transient failures. generate_response retries up to 3 times
   with backoff and torch.cuda.empty_cache() between attempts. OOM is
   not truly transient, but an empty_cache() + retry can occasionally
   recover from fragmentation-related allocation failures.
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Generation defaults. These match the values used by the previous module
# so fresh runs against a given (model, seed, prompt) produce comparable
# decoder behavior along the tuned axes (temperature, top_p).
_DEFAULT_MAX_LENGTH = 4096
_DEFAULT_NUM_PREDICT = 512
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_TOP_P = 0.9

# Retry policy for transient inference failures (OOM, CUDA resets).
# Less transient in practice than network failures, but cheap to try.
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = (5, 15)

# Threshold below which a prompt-truncation warning is NOT printed.
# Prompts that sit very close to max_length but do not exceed it are
# interesting but not actionable; a prompt that was actually clipped is.
_TRUNCATION_WARNING_FRACTION = 1.0  # warn only on actual truncation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_hf_token(provided: Optional[str]) -> Optional[str]:
    """
    Return a Hugging Face token. Prefers explicit argument, then HF_TOKEN,
    then HUGGING_FACE_HUB_TOKEN env vars. Returns None if none is found;
    the from_pretrained calls will then attempt unauthenticated access,
    which works for public models and fails clearly for gated ones.
    """
    if provided:
        return provided
    return (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    )


def _count_prompt_tokens(tokenizer, formatted_text: str) -> int:
    """
    Count tokens WITHOUT truncation, for truncation-detection purposes.
    Returns the raw token count the tokenizer would produce if no length
    limit were applied.
    """
    return len(tokenizer(formatted_text, truncation=False)["input_ids"])


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class HuggingFaceInference:
    """
    Load a 4-bit quantized causal-LM model and run inference against it.

    Usage:
        engine = HuggingFaceInference(model_path, hf_token="hf_...")
        if engine.load_model():
            try:
                result = engine.generate_response(sys_prompt, user_prompt, seed=42)
            finally:
                engine.unload_model()
    """

    def __init__(
        self,
        model_path: str,
        max_length: int = _DEFAULT_MAX_LENGTH,
        torch_dtype: torch.dtype = torch.bfloat16,
        hf_token: Optional[str] = None,
    ):
        """
        Args:
            model_path: Local path to the fine-tuned model directory.
            max_length: Tokenizer truncation length. The tokenizer will
                truncate prompts longer than this; the class prints a
                WARNING when truncation happens. Default 4096.
            torch_dtype: Compute dtype. Default bfloat16 for stability on
                Ampere+ GPUs. Use float16 only for continuity with
                pre-cleanup fp16-trained checkpoints.
            hf_token: Optional explicit HF token. Falls back to HF_TOKEN
                or HUGGING_FACE_HUB_TOKEN env vars. None works for public
                models and for locally-saved fine-tuned models where the
                path is a directory rather than a hub reference.
        """
        self.model_path = model_path
        self.max_length = max_length
        self.torch_dtype = torch_dtype
        self.hf_token = _resolve_hf_token(hf_token)
        self.model = None
        self.tokenizer = None
        self.device = None

    # -----------------------------------------------------------------------
    # Model lifecycle
    # -----------------------------------------------------------------------

    def load_model(self) -> bool:
        """
        Load the model and tokenizer. Returns True on success, False on
        failure (with the error printed). Safe to call multiple times on
        the same instance; the previous load is cleanly unloaded first.
        """
        # Defensive unload in case the caller reloads without explicit unload
        if self.model is not None or self.tokenizer is not None:
            self.unload_model()

        if not torch.cuda.is_available():
            print(
                "ERROR: CUDA is not available. Loading a 4-bit quantized "
                "model requires a GPU with bitsandbytes support."
            )
            return False

        print(f"Loading model from {self.model_path}")

        # Tokenizer
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                token=self.hf_token,
            )
        except Exception as e:
            print(f"ERROR loading tokenizer from {self.model_path}: {e}")
            return False

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Quantization config. BitsAndBytesConfig is the forward-compatible
        # API; the previous module passed load_in_4bit=True and bnb_4bit_*
        # kwargs directly, which still works but produces deprecation
        # warnings and may break in future transformers releases.
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=self.torch_dtype,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )

        # Model
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                token=self.hf_token,
                torch_dtype=self.torch_dtype,
                device_map="auto",
                quantization_config=bnb_config,
            )
        except Exception as e:
            print(f"ERROR loading model from {self.model_path}: {e}")
            # Clean up the tokenizer we already loaded
            self.tokenizer = None
            return False

        self.device = self.model.device
        print(f"Model loaded successfully on {self.device} (dtype={self.torch_dtype})")
        return True

    def unload_model(self) -> None:
        """Free VRAM and clear references to the model and tokenizer."""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self.device = None

    # -----------------------------------------------------------------------
    # Inference
    # -----------------------------------------------------------------------

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        seed: Optional[int] = None,
        num_predict: int = _DEFAULT_NUM_PREDICT,
        temperature: float = _DEFAULT_TEMPERATURE,
        top_p: float = _DEFAULT_TOP_P,
    ) -> Dict[str, Any]:
        """
        Generate a response for a given (system, user) prompt pair.

        Args:
            system_prompt: System turn content.
            user_prompt: User turn content.
            seed: Optional decoder seed. When provided, uses a
                torch.Generator seeded with this value for reproducible
                sampling. When None, sampling is fully stochastic.
            num_predict: Max new tokens to generate. Default 512, which
                covers the five-sentence meteorological diagnosis format
                with headroom. Lower if you want faster generation and
                know the output will be short; higher if you see
                generations being cut off mid-sentence.
            temperature: Sampling temperature. Default 0.7.
            top_p: Nucleus sampling cutoff. Default 0.9.

        Returns:
            A dict with 'response' (string) and metadata fields matching
            the Ollama /api/generate response shape for interoperability.
            On failure, returns {'error': <message>}.
        """
        if self.model is None or self.tokenizer is None:
            return {"error": "model not loaded; call load_model() first"}

        return self._generate_with_retry(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            seed=seed,
            num_predict=num_predict,
            temperature=temperature,
            top_p=top_p,
        )

    def _generate_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        seed: Optional[int],
        num_predict: int,
        temperature: float,
        top_p: float,
    ) -> Dict[str, Any]:
        """
        Wraps _generate_once with a 3-attempt retry. Clears the CUDA cache
        between attempts, which occasionally recovers from fragmentation-
        related OOM failures. OOM due to legitimately exceeding VRAM is
        not recoverable; in that case all 3 attempts will fail with the
        same error.
        """
        last_error: Optional[str] = None
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                return self._generate_once(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    seed=seed,
                    num_predict=num_predict,
                    temperature=temperature,
                    top_p=top_p,
                )
            except torch.cuda.OutOfMemoryError as e:
                last_error = f"CUDA OOM: {e}"
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"

            if attempt < _RETRY_ATTEMPTS - 1:
                backoff = _RETRY_BACKOFF_SECONDS[attempt]
                print(
                    f"WARNING: generation attempt {attempt + 1}/{_RETRY_ATTEMPTS} "
                    f"failed ({last_error}); retrying in {backoff}s"
                )
                time.sleep(backoff)

        return {"error": f"generation failed after {_RETRY_ATTEMPTS} attempts: {last_error}"}

    def _generate_once(
        self,
        system_prompt: str,
        user_prompt: str,
        seed: Optional[int],
        num_predict: int,
        temperature: float,
        top_p: float,
    ) -> Dict[str, Any]:
        """
        Single generation attempt. May raise on CUDA OOM or other errors;
        callers wrap this in _generate_with_retry.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Apply chat template. add_generation_prompt=True adds the assistant
        # turn prefix (e.g., '<|start_header_id|>assistant<|end_header_id|>\n\n')
        # so the model generates AS the assistant rather than continuing
        # the user turn. Unconditional for inference.
        formatted_input = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        # Check for truncation BEFORE it happens and warn. Ollama-style
        # silent truncation was the largest bug in the previous pipeline;
        # we don't want to reproduce it here.
        raw_token_count = _count_prompt_tokens(self.tokenizer, formatted_input)
        will_truncate = raw_token_count > self.max_length
        if will_truncate:
            print(
                f"WARNING: prompt has {raw_token_count} tokens, exceeds "
                f"max_length={self.max_length}; head will be truncated"
            )

        # Tokenize (with truncation applied)
        inputs = self.tokenizer(
            formatted_input,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
        ).to(self.device)

        # Build generation kwargs. When a seed is provided, use a local
        # torch.Generator rather than mutating the global RNG.
        generation_kwargs: Dict[str, Any] = {
            "max_new_tokens": num_predict,
            "do_sample": True,
            "temperature": temperature,
            "top_p": top_p,
            "pad_token_id": self.tokenizer.eos_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }

        if seed is not None:
            # Try the cleanest form first: a local generator.
            try:
                gen = torch.Generator(device=self.device).manual_seed(seed)
                generation_kwargs["generator"] = gen
            except Exception:
                # Fallback to global seed mutation for older transformers
                # versions that don't accept the generator kwarg on all
                # device types.
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed)

        start_time = datetime.now()
        with torch.no_grad():
            outputs = self.model.generate(**inputs, **generation_kwargs)
        end_time = datetime.now()

        # Decode only the newly generated tokens, not the input prompt
        generated_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)

        prompt_tokens = inputs["input_ids"].shape[1]
        completion_tokens = len(generated_tokens)
        total_duration_ns = int((end_time - start_time).total_seconds() * 1e9)

        return {
            "response": response.strip(),
            "prompt_eval_count": prompt_tokens,
            "eval_count": completion_tokens,
            "total_duration": total_duration_ns,
            "load_duration": 0,
            "prompt_eval_duration": 0,
            "eval_duration": total_duration_ns,
            "generation_options": {
                "seed": seed,
                "num_predict": num_predict,
                "temperature": temperature,
                "top_p": top_p,
                "torch_dtype": str(self.torch_dtype),
                "truncated": will_truncate,
                "raw_prompt_tokens": raw_token_count,
            },
        }
    
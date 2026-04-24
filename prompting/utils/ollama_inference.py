# import requests
# import json
# from datetime import datetime
# from pathlib import Path
# import time
# import logging
# from typing import List, Dict
# import os

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# def download_models_only(models_list: List[str], ollama_url: str = "http://localhost:11434") -> Dict:
#     """
#     Download/pull multiple Ollama models WITHOUT loading them into memory.
#     Models will be cached locally but unloaded from VRAM after download.
    
#     Args:
#         models_list: List of model names to download
#         ollama_url: Ollama API base URL
    
#     Returns:
#         dict: Summary of download results
#     """
    
#     logger.info(f"Starting download of {len(models_list)} models...")
#     logger.info("Models will be cached locally but NOT kept in memory")
    
#     download_results = {
#         "total_models": len(models_list),
#         "successful_downloads": [],
#         "failed_downloads": [],
#         "download_times": {},
#         "total_time": 0
#     }
    
#     overall_start = time.time()
    
#     for i, model_name in enumerate(models_list, 1):
#         logger.info(f"\n{'='*60}")
#         logger.info(f"Downloading model {i}/{len(models_list)}: {model_name}")
#         logger.info(f"{'='*60}")
        
#         try:
#             # Download the model
#             download_start = time.time()
#             success = pull_model_only(model_name, ollama_url)
#             download_time = time.time() - download_start
            
#             download_results["download_times"][model_name] = download_time
            
#             if success:
#                 download_results["successful_downloads"].append(model_name)
#                 logger.info(f"✅ Successfully downloaded {model_name} in {download_time:.2f}s")
                
#                 # Immediately unload from memory to free VRAM
#                 unload_success = unload_model_from_memory(model_name, ollama_url)
#                 if unload_success:
#                     logger.info(f"📤 Unloaded {model_name} from VRAM (kept on disk)")
#                 else:
#                     logger.warning(f"⚠️  Could not unload {model_name} from VRAM")
                    
#             else:
#                 download_results["failed_downloads"].append(model_name)
#                 logger.error(f"❌ Failed to download {model_name}")
                
#         except Exception as e:
#             download_results["failed_downloads"].append(model_name)
#             logger.error(f"❌ Error downloading {model_name}: {str(e)}")
            
#         # Small delay between downloads to be nice to the system
#         if i < len(models_list):
#             time.sleep(2)
    
#     download_results["total_time"] = time.time() - overall_start
    
#     # Print summary
#     logger.info(f"\n{'='*80}")
#     logger.info("DOWNLOAD SUMMARY")
#     logger.info(f"{'='*80}")
#     logger.info(f"Total models requested: {download_results['total_models']}")
#     logger.info(f"Successfully downloaded: {len(download_results['successful_downloads'])}")
#     logger.info(f"Failed downloads: {len(download_results['failed_downloads'])}")
#     logger.info(f"Total time: {download_results['total_time']:.2f}s")
    
#     if download_results["successful_downloads"]:
#         logger.info(f"\n✅ Successfully downloaded models:")
#         for model in download_results["successful_downloads"]:
#             time_taken = download_results["download_times"][model]
#             logger.info(f"   - {model} ({time_taken:.2f}s)")
    
#     if download_results["failed_downloads"]:
#         logger.info(f"\n❌ Failed to download:")
#         for model in download_results["failed_downloads"]:
#             logger.info(f"   - {model}")
    
#     logger.info(f"\n💾 All models are now cached locally but not loaded in VRAM")
#     logger.info(f"{'='*80}")
    
#     # return download_results

# def pull_model_only(model_name: str, ollama_url: str) -> bool:
#     """
#     Download/pull a single model using Ollama API.
#     This downloads the model to local cache but also loads it into memory.
#     """
#     try:
#         url = f"{ollama_url}/api/pull"
#         payload = {"name": model_name}
        
#         logger.info(f"📥 Pulling model: {model_name}...")
        
#         # Make the pull request
#         response = requests.post(url, json=payload, stream=True, timeout=1800)  # 30 min timeout
        
#         if response.status_code == 200:
#             # Parse streaming response to show progress
#             total_size = 0
#             downloaded_size = 0
            
#             for line in response.iter_lines():
#                 if line:
#                     try:
#                         data = json.loads(line.decode('utf-8'))
                        
#                         # Show download progress
#                         if 'total' in data and 'completed' in data:
#                             total_size = data['total']
#                             downloaded_size = data['completed']
                            
#                             if total_size > 0:
#                                 progress = (downloaded_size / total_size) * 100
#                                 logger.info(f"   Progress: {progress:.1f}% ({downloaded_size/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB)")
                        
#                         # Check for completion
#                         if data.get('status') == 'success' or 'success' in str(data):
#                             logger.info(f"   Download completed!")
#                             return True
                            
#                     except json.JSONDecodeError:
#                         continue
            
#             return True
#         else:
#             logger.error(f"Failed to pull model {model_name}: {response.status_code} - {response.text}")
#             return False
            
#     except requests.exceptions.RequestException as e:
#         logger.error(f"Network error pulling model {model_name}: {str(e)}")
#         return False
#     except Exception as e:
#         logger.error(f"Unexpected error pulling model {model_name}: {str(e)}")
#         return False

# def unload_model_from_memory(model_name: str, ollama_url: str) -> bool:
#     """
#     Unload a model from VRAM while keeping it cached on disk.
#     Uses a dummy API call with keep_alive=0 to unload the model.
#     """
#     try:
#         url = f"{ollama_url}/api/generate"
#         payload = {
#             "model": model_name,
#             "prompt": "",  # Empty prompt
#             "keep_alive": 0,  # Unload immediately after this call
#             "stream": False
#         }
        
#         response = requests.post(url, json=payload, timeout=30)
        
#         if response.status_code == 200:
#             return True
#         else:
#             logger.warning(f"Could not unload model {model_name}: {response.status_code}")
#             return False
            
#     except Exception as e:
#         logger.warning(f"Error unloading model {model_name}: {str(e)}")
#         return False

# def check_local_models(ollama_url: str = "http://localhost:11434") -> List[str]:
#     """
#     Check which models are available locally (downloaded but not necessarily loaded).
#     """
#     try:
#         url = f"{ollama_url}/api/tags"
#         response = requests.get(url, timeout=30)
        
#         if response.status_code == 200:
#             data = response.json()
#             models = [model['name'] for model in data.get('models', [])]
            
#             logger.info(f"Found {len(models)} locally cached models:")
#             for model in models:
#                 logger.info(f"   - {model}")
            
#             return models
#         else:
#             logger.error(f"Could not list local models: {response.status_code}")
#             return []
            
#     except Exception as e:
#         logger.error(f"Error checking local models: {str(e)}")
#         return []

# def load_model_for_inference(model_name: str, ollama_url: str, keep_alive: str = "10m") -> bool:
#     """
#     Load a previously downloaded model into memory for inference.
    
#     Args:
#         model_name: Name of the model to load
#         ollama_url: Ollama API URL
#         keep_alive: How long to keep the model in memory (e.g., "10m", "1h", "-1" for forever)
#     """
#     try:
#         url = f"{ollama_url}/api/generate"
#         payload = {
#             "model": model_name,
#             "prompt": "",  # Empty prompt just to load the model
#             "keep_alive": keep_alive,
#             "stream": False
#         }
        
#         logger.info(f"🔄 Loading {model_name} into VRAM (keep_alive: {keep_alive})...")
#         response = requests.post(url, json=payload, timeout=120)
        
#         if response.status_code == 200:
#             logger.info(f"✅ Model {model_name} loaded into memory")
#             return True
#         else:
#             logger.error(f"Failed to load model {model_name}: {response.status_code}")
#             return False
            
#     except Exception as e:
#         logger.error(f"Error loading model {model_name}: {str(e)}")
#         return False

# # Modified version of your original testing function
# def test_downloaded_models(models_list: List[str], past_days: int, base_date: str = None, 
#                          ollama_url: str = "http://localhost:11434", keep_alive: str = "30m"):
#     """
#     Test models that have already been downloaded. 
#     Loads them one by one for testing, then optionally unloads them.
    
#     Args:
#         models_list: List of model names that should already be downloaded
#         past_days: Number of past days to test
#         base_date: Base date for testing
#         ollama_url: Ollama API URL  
#         keep_alive: How long to keep each model loaded during testing
#     """
    
#     # First check which models are available locally
#     local_models = check_local_models(ollama_url)
#     missing_models = [m for m in models_list if m not in local_models]
    
#     if missing_models:
#         logger.warning(f"These models are not downloaded yet: {missing_models}")
#         logger.warning(f"Please run download_models_only() first or remove them from the list")
        
#         # Filter to only test models that are available
#         models_list = [m for m in models_list if m in local_models]
    
#     if not models_list:
#         logger.error("No models available for testing!")
#         return
    
#     logger.info(f"Testing {len(models_list)} downloaded models...")
    
#     # Setup directories and other stuff (same as your original code)
#     responses_dir = Path(f"responses\\{base_date}\\{past_days}_past_days")
#     prompts_dir = Path(f"prompts\\{base_date}\\{past_days}_past_days")
    
#     os.makedirs(responses_dir, exist_ok=True)

#     if not prompts_dir.exists():
#         logger.error(f"Prompts directory '{prompts_dir}' does not exist!")
#         return {"error": "Prompts directory not found"}
    
#     # Use today's date if base_date not provided
#     if base_date is None:
#         base_date = datetime.now().strftime('%Y-%m-%d')
    
#     # Load system prompt
#     system_prompt_path = prompts_dir / f"system_prompt_{base_date}.txt"
#     if not system_prompt_path.exists():
#         logger.error(f"System prompt file not found: {system_prompt_path}")
#         return {"error": f"System prompt file not found: {system_prompt_path}"}
    
#     with open(system_prompt_path, 'r', encoding='utf-8') as f:
#         system_prompt = f.read().strip()
    
#     results_summary = {
#         "test_date": base_date,
#         "models_tested": [],
#         "total_responses": 0,
#         "errors": []
#     }
    
#     # Test each model
#     for model_name in models_list:
#         logger.info(f"\n{'='*50}")
#         logger.info(f"Testing model: {model_name}")
#         logger.info(f"{'='*50}")
        
#         model_results = {
#             "model": model_name,
#             "responses": [],
#             "errors": []
#         }
        
#         try:
#             # Load model into memory
#             if not load_model_for_inference(model_name, ollama_url, keep_alive):
#                 error_msg = f"Failed to load model: {model_name}"
#                 model_results["errors"].append(error_msg)
#                 results_summary["errors"].append(error_msg)
#                 continue
            
#             # Test with different past_days counts
#             for current_past_days in range(past_days, 0, -1):
#                 logger.info(f"\nTesting {model_name} with {current_past_days} past days...")
                
#                 # Find user prompt file
#                 user_prompt_path = prompts_dir / f"user_prompt_{base_date}_{current_past_days}_past_days.txt"
                
#                 if not user_prompt_path.exists():
#                     error_msg = f"User prompt file not found: {user_prompt_path}"
#                     logger.warning(error_msg)
#                     model_results["errors"].append(error_msg)
#                     continue
                
#                 with open(user_prompt_path, 'r', encoding='utf-8') as f:
#                     user_prompt = f.read().strip()
                
#                 # Make API call (using your existing function)
#                 response_data = call_ollama_api_with_keep_alive(
#                     model_name=model_name,
#                     system_prompt=system_prompt,
#                     user_prompt=user_prompt,
#                     ollama_url=ollama_url,
#                     keep_alive=keep_alive
#                 )
                
#                 if response_data.get("error"):
#                     error_msg = f"API call failed for {model_name} with {current_past_days} past days: {response_data['error']}"
#                     logger.error(error_msg)
#                     model_results["errors"].append(error_msg)
#                     continue
                
#                 # Save response (same as your original code)
#                 response_record = {
#                     "model": model_name,
#                     "base_date": base_date,
#                     "past_days": current_past_days,
#                     "system_prompt": system_prompt,
#                     "user_prompt": user_prompt,
#                     "response": response_data["response"],
#                     "metadata": {
#                         "timestamp": datetime.now().isoformat(),
#                         "prompt_tokens": response_data.get("prompt_eval_count", 0),
#                         "completion_tokens": response_data.get("eval_count", 0),
#                         "total_duration": response_data.get("total_duration", 0),
#                         "load_duration": response_data.get("load_duration", 0),
#                         "prompt_eval_duration": response_data.get("prompt_eval_duration", 0),
#                         "eval_duration": response_data.get("eval_duration", 0)
#                     }
#                 }
                
#                 response_filename = f"{model_name.replace(':', '_')}_{base_date}_{current_past_days}_past_days.json"
#                 response_path = responses_dir / response_filename
                
#                 with open(response_path, 'w', encoding='utf-8') as f:
#                     json.dump(response_record, f, indent=2, ensure_ascii=False)
                
#                 model_results["responses"].append(response_filename)
#                 results_summary["total_responses"] += 1
                
#                 logger.info(f"✅ Saved response to {response_path}")
#                 logger.info(f"  Response length: {len(response_data['response'])} characters")
#                 logger.info(f"  Duration: {response_data.get('total_duration', 0) / 1e9:.2f}s")
            
#             # Optionally unload model after testing to free memory for next model
#             unload_model_from_memory(model_name, ollama_url)
#             logger.info(f"📤 Unloaded {model_name} from VRAM")
            
#         except Exception as e:
#             error_msg = f"Unexpected error testing model {model_name}: {str(e)}"
#             logger.error(error_msg)
#             model_results["errors"].append(error_msg)
#             results_summary["errors"].append(error_msg)
        
#         results_summary["models_tested"].append(model_results)
    
#     # Save summary (same as your original code)
#     summary_path = responses_dir / f"test_summary_{base_date}_{datetime.now().strftime('%H%M%S')}.json"
#     with open(summary_path, 'w', encoding='utf-8') as f:
#         json.dump(results_summary, f, indent=2, ensure_ascii=False)
    
#     logger.info(f"\n{'='*60}")
#     logger.info("TEST SUMMARY")
#     logger.info(f"{'='*60}")
#     logger.info(f"Total models tested: {len(results_summary['models_tested'])}")
#     logger.info(f"Total responses generated: {results_summary['total_responses']}")
#     logger.info(f"Total errors: {len(results_summary['errors'])}")
#     logger.info(f"Summary saved to: {summary_path}")
#     logger.info(f"{'='*60}")
    
#     # return results_summary

# def call_ollama_api_with_keep_alive(model_name: str, system_prompt: str, user_prompt: str, 
#                                    ollama_url: str, keep_alive: str = "10m") -> Dict:
#     """
#     Modified version of your call_ollama_api with keep_alive parameter.
#     """
#     try:
#         url = f"{ollama_url}/api/generate"
#         payload = {
#             "model": model_name,
#             "prompt": user_prompt,
#             "system": system_prompt,
#             "stream": False,
#             "keep_alive": keep_alive,  # Control how long model stays in memory
#             "options": {
#                 "temperature": 0.7,
#                 "top_p": 0.9,
#             }
#         }
        
#         response = requests.post(url, json=payload, timeout=300)
        
#         if response.status_code == 200:
#             return response.json()
#         else:
#             return {"error": f"API call failed: {response.status_code} - {response.text}"}
            
#     except requests.exceptions.RequestException as e:
#         return {"error": f"Network error: {str(e)}"}
#     except Exception as e:
#         return {"error": f"Unexpected error: {str(e)}"}


"""
Ollama inference for the meteorological diagnosis pipeline.

Wraps the Ollama HTTP API to download models, load and unload them
explicitly, and run inference for every (model, past_days) combination
in a test suite. Saves each response as a JSON file with the original
prompts, the model output, and Ollama's per-call timing/token metadata.

Public API (signatures backward-compatible with the previous ollama_calls.py
module; new optional kwargs are added with defaults so existing call sites
in main.py work unchanged):

    download_models_only           pull models from the Ollama registry,
                                   unload each one after download
    test_downloaded_models         load each model in turn, run inference
                                   for past_days 1..N, save responses,
                                   print a prompt-token usage diagnostic

KEY DESIGN POINTS for downstream readers:

1. Reproducibility. Every call sets seed, temperature, top_p, num_ctx,
   and num_predict explicitly. Re-running the same (model, date, past_days,
   seed) is guaranteed to produce the same output.

   For variance estimation across decoder noise, pass n_seeds=K to
   test_downloaded_models. The function will run K inference calls per
   (model, past_days) cell using deterministic seeds derived from
   _DEFAULT_SEED (42, 43, 44, ...), writing each response to a filename
   with a _seed{seed} suffix. When n_seeds=1 (default), filename and JSON
   schema are byte-identical to single-seed runs for backwards
   compatibility with existing responses/ folders.

2. Context window safety. Ollama's default num_ctx is 4096 in 0.11.x, which
   is insufficient for past_days=2..4 in this pipeline (prompts run 4-10K
   tokens depending on tokenizer). The previous pipeline did not pass
   num_ctx and consequently every non-gpt-oss test response at past_days>=2
   was generated against a prompt silently clipped to 4096 tokens with the
   head discarded. This module sets num_ctx=16384 by default and prints a
   per-(model, past_days) prompt-token summary at the end of each test run
   so future truncation events are immediately visible.

3. Per-model overrides. If a specific model needs a different context
   window (gpt-oss has a native 8192 default in Ollama, some experiments
   may want 32K+), pass model_num_ctx_overrides={"model:tag": N}.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_OLLAMA_URL = "http://localhost:11434"

# Generation options. All five are explicitly set on every API call so the
# decoder is fully reproducible given a fixed seed.
_DEFAULT_SEED = 42
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_TOP_P = 0.9
_DEFAULT_NUM_PREDICT = 512  # max output tokens; 5-sentence diagnoses fit easily

# Context window. 16384 fits past_days up to ~5-6 across all model tokenizers
# in this pipeline with comfortable headroom. Raising num_ctx increases KV
# cache VRAM linearly: ~32 GB for a 70B model at 16K context (well within
# the A6000's 48 GB budget). Do NOT lower this without first checking the
# prompt-token summary printed at the end of test_downloaded_models -
# Ollama silently truncates prompts that exceed num_ctx, with no error.
_DEFAULT_NUM_CTX = 16384

# Default keep-alive durations for the model lifecycle.
_DEFAULT_TEST_KEEP_ALIVE = "30m"

# Network timeouts. The pull timeout is generous because models can be tens
# of GB; the inference timeout is generous to accommodate long reasoning-mode
# generations on large models.
_MODEL_PULL_TIMEOUT_SECONDS = 1800
_MODEL_LOAD_TIMEOUT_SECONDS = 120
_API_REQUEST_TIMEOUT_SECONDS = 600
_UNLOAD_TIMEOUT_SECONDS = 30

# Inter-download pause and progress-log throttling.
_DOWNLOAD_INTER_DELAY_SECONDS = 2
_DOWNLOAD_PROGRESS_LOG_INTERVAL = 0.10  # log every 10% downloaded

# Retry policy for transient API failures (network blips, brief Ollama
# crashes). Three attempts total with exponential-ish backoff.
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = (5, 15)

# Prompt-token usage warnings. If max usage exceeds num_ctx the call was
# truncated; if it exceeds 80% of num_ctx the run is approaching the limit.
_NUM_CTX_WARNING_FRACTION = 0.80


# ---------------------------------------------------------------------------
# Model lifecycle helpers (pull, unload, check, load)
# ---------------------------------------------------------------------------

def _pull_model_only(model_name: str, ollama_url: str) -> bool:
    """
    Pull a model from the Ollama registry, streaming progress. Returns True
    if the pull completed cleanly, False on any error.
    """
    url = f"{ollama_url}/api/pull"
    payload = {"name": model_name}
    print(f"Pulling model: {model_name}")

    last_progress_logged = -1.0
    try:
        response = requests.post(url, json=payload, stream=True, timeout=_MODEL_PULL_TIMEOUT_SECONDS)
        if response.status_code != 200:
            print(f"ERROR: failed to pull {model_name}: {response.status_code} - {response.text}")
            return False

        for line in response.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                continue

            # Throttled progress reporting
            total = data.get("total", 0)
            completed = data.get("completed", 0)
            if total > 0 and completed > 0:
                fraction = completed / total
                if fraction - last_progress_logged >= _DOWNLOAD_PROGRESS_LOG_INTERVAL:
                    last_progress_logged = fraction
                    print(
                        f"  {model_name}: "
                        f"{fraction * 100:.0f}% "
                        f"({completed / 1024 / 1024:.0f} / {total / 1024 / 1024:.0f} MB)"
                    )

            # Strict success check: only data['status'] == 'success'.
            # The previous code also accepted 'success' as a substring of the
            # stringified dict, which would match unrelated fields.
            if data.get("status") == "success":
                return True

        # Stream completed without an explicit success status; assume success.
        return True

    except requests.exceptions.RequestException as e:
        print(f"ERROR: network error pulling {model_name}: {e}")
        return False
    except Exception as e:
        print(f"ERROR: unexpected error pulling {model_name}: {e}")
        return False


def _unload_model_from_memory(model_name: str, ollama_url: str) -> bool:
    """
    Unload a model from VRAM by issuing a no-op generate call with
    keep_alive=0. Ollama doesn't expose a dedicated unload endpoint, so this
    indirect approach is the documented pattern.
    """
    url = f"{ollama_url}/api/generate"
    payload = {
        "model": model_name,
        "prompt": "",
        "keep_alive": 0,
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=_UNLOAD_TIMEOUT_SECONDS)
        if response.status_code == 200:
            return True
        print(f"WARNING: could not unload {model_name}: HTTP {response.status_code}")
        return False
    except Exception as e:
        print(f"WARNING: error unloading {model_name}: {e}")
        return False


def _check_local_models(ollama_url: str) -> List[str]:
    """Return the names of all locally cached Ollama models, or [] on failure."""
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=30)
        if response.status_code != 200:
            print(f"ERROR: could not list local models: HTTP {response.status_code}")
            return []
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        print(f"ERROR: could not list local models: {e}")
        return []


def _load_model_for_inference(
    model_name: str,
    ollama_url: str,
    keep_alive: str,
) -> bool:
    """Pre-load a model into VRAM via a no-op generate call. Returns success."""
    url = f"{ollama_url}/api/generate"
    payload = {
        "model": model_name,
        "prompt": "",
        "keep_alive": keep_alive,
        "stream": False,
    }
    try:
        print(f"Loading {model_name} into VRAM (keep_alive={keep_alive})")
        response = requests.post(url, json=payload, timeout=_MODEL_LOAD_TIMEOUT_SECONDS)
        if response.status_code == 200:
            return True
        print(f"ERROR: failed to load {model_name}: HTTP {response.status_code}")
        return False
    except Exception as e:
        print(f"ERROR: error loading {model_name}: {e}")
        return False


# ---------------------------------------------------------------------------
# Inference call
# ---------------------------------------------------------------------------

def _call_ollama_api(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    ollama_url: str,
    keep_alive: str,
    seed: int,
    num_ctx: int,
    num_predict: int,
    temperature: float,
    top_p: float,
) -> Dict:
    """
    One inference call. Returns the parsed Ollama response dict on success
    or {"error": <message>} on failure. The options dict explicitly sets
    every generation parameter so re-running with the same arguments is
    fully reproducible.
    """
    url = f"{ollama_url}/api/generate"
    payload = {
        "model": model_name,
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": False,
        "keep_alive": keep_alive,
        "options": {
            "seed": seed,
            "temperature": temperature,
            "top_p": top_p,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    try:
        response = requests.post(url, json=payload, timeout=_API_REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            return response.json()
        return {"error": f"HTTP {response.status_code} - {response.text}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"network error: {e}"}
    except Exception as e:
        return {"error": f"unexpected error: {e}"}


def _call_ollama_api_with_retry(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    ollama_url: str,
    keep_alive: str,
    seed: int,
    num_ctx: int,
    num_predict: int,
    temperature: float,
    top_p: float,
) -> Dict:
    """
    Wraps _call_ollama_api with retry-on-transient-failure logic. Three
    attempts total, with backoff between attempts. Returns the same shape
    as _call_ollama_api: success dict or {"error": ...}.
    """
    last_response: Dict = {"error": "no attempts made"}
    for attempt in range(_RETRY_ATTEMPTS):
        last_response = _call_ollama_api(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            ollama_url=ollama_url,
            keep_alive=keep_alive,
            seed=seed,
            num_ctx=num_ctx,
            num_predict=num_predict,
            temperature=temperature,
            top_p=top_p,
        )
        if "error" not in last_response:
            return last_response

        if attempt < _RETRY_ATTEMPTS - 1:
            backoff = _RETRY_BACKOFF_SECONDS[attempt]
            print(
                f"WARNING: API call to {model_name} failed "
                f"(attempt {attempt + 1}/{_RETRY_ATTEMPTS}): "
                f"{last_response['error']}. Retrying in {backoff}s"
            )
            time.sleep(backoff)

    return last_response


# ---------------------------------------------------------------------------
# Prompt and response file I/O
# ---------------------------------------------------------------------------

def _load_system_prompt(prompts_dir: Path, base_date: str) -> Optional[str]:
    """Load the system prompt for a given date, or None if missing."""
    path = prompts_dir / f"system_prompt_{base_date}.txt"
    if not path.exists():
        print(f"ERROR: system prompt file not found: {path}")
        return None
    return path.read_text(encoding="utf-8").strip()


def _load_user_prompt(
    prompts_dir: Path,
    base_date: str,
    past_days: int,
) -> Optional[str]:
    """Load the user prompt for a given date and past_days, or None if missing."""
    path = prompts_dir / f"user_prompt_{base_date}_{past_days}_past_days.txt"
    if not path.exists():
        print(f"WARNING: user prompt file not found: {path}")
        return None
    return path.read_text(encoding="utf-8").strip()


def _save_response_json(
    responses_dir: Path,
    model_name: str,
    base_date: str,
    past_days: int,
    system_prompt: str,
    user_prompt: str,
    response_data: Dict,
    seed: int,
    num_ctx: int,
    num_predict: int,
    temperature: float,
    top_p: float,
    include_seed_in_filename: bool,
) -> str:
    """
    Serialize one response to a JSON file. Returns the filename. Captures
    every generation parameter in the metadata so each saved response is
    self-describing and reproducible.

    When include_seed_in_filename is False (single-seed run, backwards-compat
    mode), the filename is {model}_{date}_{N}_past_days.json. When True
    (multi-seed run), the filename is {model}_{date}_{N}_past_days_seed{seed}.json
    so multiple per-cell responses can coexist without collision.
    """
    record = {
        "model": model_name,
        "base_date": base_date,
        "past_days": past_days,
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
                "num_ctx": num_ctx,
                "num_predict": num_predict,
                "temperature": temperature,
                "top_p": top_p,
            },
        },
    }
    safe_model = model_name.replace(":", "_")
    if include_seed_in_filename:
        filename = f"{safe_model}_{base_date}_{past_days}_past_days_seed{seed}.json"
    else:
        filename = f"{safe_model}_{base_date}_{past_days}_past_days.json"
    out_path = responses_dir / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return filename


# ---------------------------------------------------------------------------
# num_ctx resolution
# ---------------------------------------------------------------------------

def _resolve_num_ctx(
    model_name: str,
    default_num_ctx: int,
    overrides: Optional[Dict[str, int]],
) -> int:
    """Per-model num_ctx override if present, otherwise the default."""
    if overrides and model_name in overrides:
        return overrides[model_name]
    return default_num_ctx


def _resolve_seeds(
    n_seeds: int,
    explicit_seeds: Optional[List[int]],
) -> List[int]:
    """
    Produce the seed list for a test run.

    If explicit_seeds is given, use it verbatim (caller has full control).
    Otherwise, for n_seeds=K, generate a deterministic list derived from
    _DEFAULT_SEED: [42, 43, 44, ..., 42+K-1]. Deterministic so re-running
    the same multi-seed experiment produces identical responses.
    """
    if explicit_seeds is not None:
        if len(explicit_seeds) == 0:
            raise ValueError("explicit_seeds must contain at least one seed")
        return list(explicit_seeds)
    if n_seeds < 1:
        raise ValueError(f"n_seeds must be >= 1, got {n_seeds}")
    return [_DEFAULT_SEED + i for i in range(n_seeds)]


# ---------------------------------------------------------------------------
# Per-model and per-config inference
# ---------------------------------------------------------------------------

def _test_one_past_days_config(
    model_name: str,
    past_days: int,
    base_date: str,
    system_prompt: str,
    prompts_dir: Path,
    responses_dir: Path,
    ollama_url: str,
    keep_alive: str,
    seed: int,
    num_ctx: int,
    num_predict: int,
    temperature: float,
    top_p: float,
    token_usage_log: Dict,
    include_seed_in_filename: bool,
) -> bool:
    """
    Run inference for one (model, past_days, seed) cell. Saves the response
    JSON on success and records the prompt token count for the end-of-run
    diagnostic. Returns True on success.
    """
    user_prompt = _load_user_prompt(prompts_dir, base_date, past_days)
    if user_prompt is None:
        return False

    response_data = _call_ollama_api_with_retry(
        model_name=model_name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        ollama_url=ollama_url,
        keep_alive=keep_alive,
        seed=seed,
        num_ctx=num_ctx,
        num_predict=num_predict,
        temperature=temperature,
        top_p=top_p,
    )

    if "error" in response_data:
        print(
            f"ERROR: API call failed for {model_name} pd={past_days} seed={seed} "
            f"after {_RETRY_ATTEMPTS} attempts: {response_data['error']}"
        )
        return False

    raw_response = response_data.get("response", "")
    if not raw_response or not raw_response.strip():
        print(
            f"WARNING: empty response from {model_name} pd={past_days} seed={seed}; "
            "saving JSON anyway for inspection"
        )

    filename = _save_response_json(
        responses_dir=responses_dir,
        model_name=model_name,
        base_date=base_date,
        past_days=past_days,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_data=response_data,
        seed=seed,
        num_ctx=num_ctx,
        num_predict=num_predict,
        temperature=temperature,
        top_p=top_p,
        include_seed_in_filename=include_seed_in_filename,
    )

    prompt_tokens = response_data.get("prompt_eval_count", 0)
    duration_s = response_data.get("total_duration", 0) / 1e9
    print(
        f"  {model_name} pd={past_days} seed={seed}: "
        f"prompt_tokens={prompt_tokens}, "
        f"duration={duration_s:.1f}s, saved {filename}"
    )

    # Record for the end-of-run truncation diagnostic. Token count is
    # deterministic given the prompt, so all seeds for the same cell should
    # report identical counts.
    token_usage_log.setdefault((model_name, past_days), []).append(prompt_tokens)
    return True


def _test_one_model(
    model_name: str,
    past_days_max: int,
    base_date: str,
    system_prompt: str,
    prompts_dir: Path,
    responses_dir: Path,
    ollama_url: str,
    keep_alive: str,
    seeds: List[int],
    num_ctx: int,
    num_predict: int,
    temperature: float,
    top_p: float,
    token_usage_log: Dict,
    include_seed_in_filename: bool,
) -> int:
    """
    Run inference for one model across every (past_days, seed) combination.

    The model is loaded once and kept in VRAM while all past_days x seed
    cells are swept, then unloaded. This amortizes model-load cost across
    the entire cell matrix rather than paying it per seed.

    Returns the number of cells that completed successfully.
    """
    n_seeds = len(seeds)
    seed_label = f"seeds={seeds}" if n_seeds > 1 else f"seed={seeds[0]}"
    print(f"\nTesting {model_name} (num_ctx={num_ctx}, {seed_label})")

    if not _load_model_for_inference(model_name, ollama_url, keep_alive):
        return 0

    successes = 0
    try:
        # Outer loop: past_days (descending, matches previous behaviour).
        # Inner loop: seed. This keeps the model loaded across the full
        # sweep for maximum throughput on large models.
        for current_past_days in range(past_days_max, 0, -1):
            for seed in seeds:
                ok = _test_one_past_days_config(
                    model_name=model_name,
                    past_days=current_past_days,
                    base_date=base_date,
                    system_prompt=system_prompt,
                    prompts_dir=prompts_dir,
                    responses_dir=responses_dir,
                    ollama_url=ollama_url,
                    keep_alive=keep_alive,
                    seed=seed,
                    num_ctx=num_ctx,
                    num_predict=num_predict,
                    temperature=temperature,
                    top_p=top_p,
                    token_usage_log=token_usage_log,
                    include_seed_in_filename=include_seed_in_filename,
                )
                if ok:
                    successes += 1
    finally:
        _unload_model_from_memory(model_name, ollama_url)

    return successes


# ---------------------------------------------------------------------------
# End-of-run prompt-token diagnostic
# ---------------------------------------------------------------------------

def _print_prompt_token_summary(
    token_usage_log: Dict,
    default_num_ctx: int,
    overrides: Optional[Dict[str, int]],
) -> None:
    """
    Print a per-(model, past_days) summary of actual prompt token usage and
    flag any cells where prompts approached or exceeded num_ctx.

    This is the diagnostic that catches silent truncation. The previous
    pipeline did not have it, which is why every non-gpt-oss test response
    at past_days>=2 was being clipped to 4096 tokens with no error and no
    log entry.
    """
    if not token_usage_log:
        return

    print("\nPrompt token usage:")
    truncated_cells: List[str] = []
    near_limit_cells: List[str] = []

    for (model_name, past_days), token_list in sorted(token_usage_log.items()):
        if not token_list:
            continue
        n = len(token_list)
        tmin = min(token_list)
        tmax = max(token_list)
        tmean = sum(token_list) // n
        ctx = _resolve_num_ctx(model_name, default_num_ctx, overrides)

        # Truncation: max equals num_ctx (Ollama clipped at the ceiling).
        # Approaching limit: max >= 80% of num_ctx but below the ceiling.
        if tmax >= ctx:
            status = "TRUNCATED"
            truncated_cells.append(f"{model_name} pd={past_days}")
        elif tmax >= ctx * _NUM_CTX_WARNING_FRACTION:
            status = "near limit"
            near_limit_cells.append(f"{model_name} pd={past_days}")
        else:
            status = "ok"

        usage_pct = tmax / ctx * 100
        print(
            f"  {model_name:50s} pd={past_days}  n={n:3d}  "
            f"min={tmin:5d}  max={tmax:5d}  mean={tmean:5d}  "
            f"(num_ctx={ctx}, peak {usage_pct:.0f}%, {status})"
        )

    if truncated_cells:
        print(
            f"\nERROR: {len(truncated_cells)} (model, past_days) cells exceeded num_ctx "
            f"and were silently truncated by Ollama. Affected cells: "
            f"{', '.join(truncated_cells)}"
        )
        print(
            "Increase _DEFAULT_NUM_CTX or pass model_num_ctx_overrides for "
            "the affected models, then re-run."
        )
    elif near_limit_cells:
        print(
            f"\nWARNING: {len(near_limit_cells)} cells used >80% of num_ctx. "
            f"Consider raising num_ctx for headroom: {', '.join(near_limit_cells)}"
        )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def download_models_only(
    models_list: List[str],
    ollama_url: str = _DEFAULT_OLLAMA_URL,
) -> None:
    """
    Pull each model from the Ollama registry. After every successful pull,
    immediately unload the model from VRAM so the next pull can proceed
    without VRAM contention. Models remain cached on disk.
    """
    models_dir = os.environ.get("OLLAMA_MODELS") or str(Path.home() / ".ollama" / "models")
    print(f"[trace] Ollama models directory: {models_dir} "
          f"(source: {'OLLAMA_MODELS env var' if os.environ.get('OLLAMA_MODELS') else 'default ~/.ollama/models'})")
    print(f"Downloading {len(models_list)} models")

    downloaded_log_path = Path("downloaded_models.txt")
    already_downloaded: List[str] = []
    if downloaded_log_path.exists():
        already_downloaded = [
            line.strip() for line in downloaded_log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    print(f"[trace] Progress log: {downloaded_log_path.resolve()} "
          f"({len(already_downloaded)} already recorded)")

    successful: List[str] = []
    failed: List[str] = []
    overall_start = time.time()

    for i, model_name in enumerate(models_list, start=1):
        print(f"\nDownload {i}/{len(models_list)}: {model_name}")
        download_start = time.time()
        try:
            success = _pull_model_only(model_name, ollama_url)
        except Exception as e:
            print(f"ERROR: unexpected error downloading {model_name}: {e}")
            success = False

        if success:
            elapsed = time.time() - download_start
            print(f"Downloaded {model_name} in {elapsed:.0f}s")
            if not _unload_model_from_memory(model_name, ollama_url):
                print(f"WARNING: {model_name} downloaded but could not be unloaded from VRAM")
            successful.append(model_name)
            if model_name not in already_downloaded:
                already_downloaded.append(model_name)
                with open(downloaded_log_path, "w", encoding="utf-8") as f:
                    for name in already_downloaded:
                        f.write(f"{name}\n")
                print(f"[trace] Recorded {model_name} in {downloaded_log_path.name}")
        else:
            failed.append(model_name)

        if i < len(models_list):
            time.sleep(_DOWNLOAD_INTER_DELAY_SECONDS)

    total_time = time.time() - overall_start
    print(
        f"\nDownload complete: {len(successful)}/{len(models_list)} successful, "
        f"{len(failed)} failed, total {total_time:.0f}s"
    )
    if failed:
        print(f"Failed models: {', '.join(failed)}")


def test_downloaded_models(
    models_list: List[str],
    past_days: int,
    base_date: Optional[str] = None,
    ollama_url: str = _DEFAULT_OLLAMA_URL,
    keep_alive: str = _DEFAULT_TEST_KEEP_ALIVE,
    seed: int = _DEFAULT_SEED,
    num_ctx: int = _DEFAULT_NUM_CTX,
    num_predict: int = _DEFAULT_NUM_PREDICT,
    temperature: float = _DEFAULT_TEMPERATURE,
    top_p: float = _DEFAULT_TOP_P,
    model_num_ctx_overrides: Optional[Dict[str, int]] = None,
    n_seeds: int = 1,
    seeds: Optional[List[int]] = None,
) -> None:
    """
    Run inference for every model in models_list against every past_days
    configuration from past_days down to 1. Saves responses as JSON files
    under responses/{base_date}/{past_days}_past_days/ and prints a
    prompt-token usage diagnostic at the end.

    Variance-estimation mode (n_seeds > 1) runs inference K times per
    (model, past_days) cell using deterministic seeds starting at
    _DEFAULT_SEED. Each per-seed response gets its own JSON file with a
    _seed{seed} suffix in the filename. When n_seeds=1 (default), filename
    and JSON schema are byte-identical to single-seed runs.

    Args:
        models_list: Models to test. Each must already be downloaded.
        past_days: Highest past_days configuration to run; the function
            iterates from past_days down to 1.
        base_date: Date string in 'YYYY-MM-DD' form. If None, today's date
            is used. Determines the prompts/ and responses/ subdirectories.
        ollama_url: Ollama HTTP API base URL.
        keep_alive: How long Ollama should keep each model loaded between
            calls. Default 30 minutes covers a full past_days x seeds sweep
            for one model.
        seed: Decoder seed for single-seed runs. Ignored when n_seeds>1 or
            seeds is passed explicitly.
        num_ctx: Context window in tokens. Default _DEFAULT_NUM_CTX (16384).
            Lowering this risks silent prompt truncation; check the
            end-of-run summary if you do.
        num_predict: Max output tokens per response. Default 512.
        temperature, top_p: Standard sampler controls. Kept at the defaults
            used by the previous pipeline so existing single-seed runs can
            be compared against new runs along the seed axis only.
        model_num_ctx_overrides: Per-model num_ctx values that override the
            default. Useful when one model needs a different window from
            the rest.
        n_seeds: Number of seeds to sweep per (model, past_days) cell.
            Defaults to 1 for backwards compatibility. Set to 5 for
            typical variance-estimation runs; the seeds used will be
            [42, 43, 44, 45, 46]. When n_seeds>1, each response gets a
            filename with a _seed{seed} suffix.
        seeds: Explicit seed list, overrides n_seeds. Use for full control
            when you want specific seed values (e.g., [42, 1337, 2024]).
    """
    # Resolve base_date BEFORE constructing any paths. The previous pipeline
    # built the directory paths first and only then checked for None, which
    # produced literal "None" subdirectories on the filesystem.
    if base_date is None:
        base_date = datetime.now().strftime("%Y-%m-%d")

    # Resolve the seed sweep. When the caller wants single-seed behaviour,
    # the explicit `seed` kwarg still determines which seed is used.
    if seeds is None and n_seeds == 1:
        seed_list = [seed]
        include_seed_in_filename = False
    else:
        seed_list = _resolve_seeds(n_seeds, seeds)
        include_seed_in_filename = len(seed_list) > 1

    # Filter to models that are actually downloaded.
    local_models = _check_local_models(ollama_url)
    missing = [m for m in models_list if m not in local_models]
    if missing:
        print(f"WARNING: not downloaded yet: {missing}. Run download_models_only first.")
        models_list = [m for m in models_list if m in local_models]
    if not models_list:
        print("ERROR: no models available for testing")
        return

    # Resolve and validate paths.
    prompts_dir = Path("prompts") / base_date / f"{past_days}_past_days"
    responses_dir = Path("responses") / base_date / f"{past_days}_past_days"

    if not prompts_dir.exists():
        print(f"ERROR: prompts directory not found: {prompts_dir}")
        return
    responses_dir.mkdir(parents=True, exist_ok=True)

    # Load the system prompt once. The same system prompt applies to every
    # (model, past_days, seed) cell for a given date.
    system_prompt = _load_system_prompt(prompts_dir, base_date)
    if system_prompt is None:
        return

    seed_desc = (
        f"seed={seed_list[0]}"
        if len(seed_list) == 1
        else f"n_seeds={len(seed_list)} (seeds={seed_list})"
    )
    print(
        f"Testing {len(models_list)} models for {base_date} "
        f"(past_days 1..{past_days}, {seed_desc}, num_ctx={num_ctx})"
    )
    if model_num_ctx_overrides:
        print(f"Per-model num_ctx overrides: {model_num_ctx_overrides}")

    token_usage_log: Dict = {}
    total_responses = 0

    for model_name in models_list:
        model_num_ctx = _resolve_num_ctx(model_name, num_ctx, model_num_ctx_overrides)
        try:
            model_successes = _test_one_model(
                model_name=model_name,
                past_days_max=past_days,
                base_date=base_date,
                system_prompt=system_prompt,
                prompts_dir=prompts_dir,
                responses_dir=responses_dir,
                ollama_url=ollama_url,
                keep_alive=keep_alive,
                seeds=seed_list,
                num_ctx=model_num_ctx,
                num_predict=num_predict,
                temperature=temperature,
                top_p=top_p,
                token_usage_log=token_usage_log,
                include_seed_in_filename=include_seed_in_filename,
            )
            total_responses += model_successes
        except Exception as e:
            print(f"ERROR: unexpected error testing {model_name}: {e}")

    print(
        f"\nTesting complete: {total_responses} responses generated for {base_date} "
        f"across {len(models_list)} models "
        f"({len(seed_list)} seed{'s' if len(seed_list) > 1 else ''} per cell)"
    )

    _print_prompt_token_summary(token_usage_log, num_ctx, model_num_ctx_overrides)

    # Auto-include the fine-tuned QLoRA model, if present on disk, in the
    # same responses/ folder. This makes the fine-tuned model appear as just
    # another row in every downstream CSV and plot, alongside the Ollama
    # models, with zero manual merging.
    _test_finetuned_on_ollama_prompts(
        base_date=base_date,
        past_days_max=past_days,
        prompts_dir=prompts_dir,
        responses_dir=responses_dir,
        seeds=seed_list,
        num_ctx=num_ctx,
        num_predict=num_predict,
        temperature=temperature,
        top_p=top_p,
        include_seed_in_filename=include_seed_in_filename,
    )


_FINETUNED_ADAPTER_DIR = Path("fine_tuned_llm") / "model" / "final_model"
_FINETUNED_MODEL_LABEL = "Llama-3.1-8B-Instruct-qlora"


def _test_finetuned_on_ollama_prompts(
    base_date: str,
    past_days_max: int,
    prompts_dir: Path,
    responses_dir: Path,
    seeds: List[int],
    num_ctx: int,
    num_predict: int,
    temperature: float,
    top_p: float,
    include_seed_in_filename: bool,
) -> None:
    """
    If a fine-tuned QLoRA adapter exists on disk, run it against the same
    prompts the Ollama models just consumed and write responses into the
    same responses/ folder so downstream analysis picks it up as another
    row. Silently no-ops when the adapter is absent.

    Imports HuggingFaceInference lazily so the heavy transformers/peft
    stack is not loaded for Ollama-only runs.
    """
    if not _FINETUNED_ADAPTER_DIR.exists():
        return

    system_prompt = _load_system_prompt(prompts_dir, base_date)
    if system_prompt is None:
        print(
            f"WARNING: skipping fine-tuned model for {base_date}; "
            "system prompt not found"
        )
        return

    try:
        from prompting.utils.hf_inference import HuggingFaceInference
    except Exception as e:
        print(f"WARNING: cannot import HuggingFaceInference; skipping fine-tuned: {e}")
        return

    print(
        f"\nTesting fine-tuned model {_FINETUNED_MODEL_LABEL} "
        f"(num_ctx={num_ctx}, seeds={seeds})"
    )

    engine = HuggingFaceInference(str(_FINETUNED_ADAPTER_DIR), max_length=num_ctx)
    if not engine.load_model():
        print("ERROR: failed to load fine-tuned model; skipping")
        return

    successes = 0
    try:
        for current_past_days in range(past_days_max, 0, -1):
            user_prompt = _load_user_prompt(prompts_dir, base_date, current_past_days)
            if user_prompt is None:
                continue

            for seed in seeds:
                response_data = engine.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    seed=seed,
                    num_predict=num_predict,
                    temperature=temperature,
                    top_p=top_p,
                )
                if "error" in response_data:
                    print(
                        f"ERROR: fine-tuned generation failed pd={current_past_days} "
                        f"seed={seed}: {response_data['error']}"
                    )
                    continue

                filename = _save_response_json(
                    responses_dir=responses_dir,
                    model_name=_FINETUNED_MODEL_LABEL,
                    base_date=base_date,
                    past_days=current_past_days,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_data=response_data,
                    seed=seed,
                    num_ctx=num_ctx,
                    num_predict=num_predict,
                    temperature=temperature,
                    top_p=top_p,
                    include_seed_in_filename=include_seed_in_filename,
                )
                successes += 1
                duration_s = response_data.get("total_duration", 0) / 1e9
                print(
                    f"  {_FINETUNED_MODEL_LABEL} pd={current_past_days} seed={seed}: "
                    f"duration={duration_s:.1f}s, saved {filename}"
                )
    finally:
        engine.unload_model()

    print(
        f"Fine-tuned model complete: {successes} responses written to {responses_dir}"
    )

# Meteorological Diagnosis LLM Evaluation Pipeline

Romanian-language meteorological diagnosis generation and evaluation using
LLMs. Compares Ollama-hosted open-source models, OpenAI API models, and a
QLoRA-finetuned Llama 3.1 8B against structured reference diagnoses from
ANM (Romania's National Meteorological Administration).


## File inventory

Every module in `prompting/utils/` after the cleanup, with its provenance.

| Module | Role | Source |
|---|---|---|
| `check_data_availability.py` | Validate that CSV station data exists for a date range | Edited in place |
| `config.py` | Calendar split (train/test dates), LoRA hyperparameters, Trainer args | Edited in place |
| `input_extraction.py` | Extract weather data from CSVs and forecast text from PDFs | **New: combined** `extract_data_from_tables.py` + `extract_pdf_data.py` |
| `prompt_construction.py` | Build system/user prompt pairs for both PDF-context and GPT-CoT tracks | **New: combined** `create_prompts.py` + `create_prompts_gpt.py` |
| `ollama_inference.py` | Download and run inference against Ollama-hosted models | Renamed from `ollama_calls.py` |
| `hf_inference.py` | Load a 4-bit quantized HF model and run inference | Edited in place |
| `finetuning_pipeline.py` | QLoRA fine-tuning orchestrator (train + test + evaluate) | Renamed from `llama_finetuning_pipeline.py` |
| `finetune_integration.py` | Thin CLI wrapper between `main.py` and `finetuning_pipeline.py` | Edited in place |
| `response_evaluation.py` | Compute ROUGE/BLEU/METEOR/BERTScore/Jaccard against references | **New: combined** `postprocessing_romanian.py` + `postprocessing_romanian_gpt.py` |
| `judge_evaluation.py` | LLM-as-a-judge scoring and aggregation tables | **New: combined** `llm_as_a_judge.py` + `judge_analysis_table.py` |
| `dataset_creation.py` | Generate `train_data.json`, `test_data.json`, `test_data_zero_shot.json` | **New: combined** `generate_training_data.py` + `create_train_test_datasets.py` + `create_zero_shot_test_dataset.py` |
| `diagnoses_formatting.py` | Extract yearly PDF diagnoses and reformat via gpt-5-mini into 5-sentence structure | Renamed from `create_dataset.py` |
| `model_select_gui.py` | GUI for interactive model selection | Untouched |
| `main.py` | Top-level CLI dispatcher | Edited in place |

Files to delete (replaced by the modules above):

`extract_data_from_tables.py`, `extract_pdf_data.py`, `create_prompts.py`,
`create_prompts_gpt.py`, `ollama_calls.py`, `llama_finetuning_pipeline.py`,
`postprocessing_romanian.py`, `postprocessing_romanian_gpt.py`,
`llm_as_a_judge.py`, `judge_analysis_table.py`, `generate_training_data.py`,
`create_train_test_datasets.py`, `create_zero_shot_test_dataset.py`,
`create_dataset.py`, `update_test_prompts.py`.


## Environment setup

```
conda activate meteollm          # Python 3.12.7

# Step 1: Install PyTorch with CUDA 12.6 support (CPU-only will NOT work)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# Step 2: Install remaining dependencies
pip install -r requirements.txt --break-system-packages

# Step 3: Download NLTK data (one-time)
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('wordnet')"
```

Verify CUDA is available:

```
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, device: {torch.cuda.get_device_name(0)}')"
```

Required environment variables (set before running any pipeline step):

```
set OPENAI_API_KEY=sk-...        # for prompt generation, judge analysis, diagnoses formatting
set HF_TOKEN=hf_...              # for gated HF models (Llama 3.1); not needed for local fine-tuned models
```

The previous codebase had these keys hardcoded in source files. All
hardcoded keys have been removed and must be rotated in your OpenAI and
HuggingFace dashboards.


## Data flow

```
PDF forecasts (date/all_diagnosis_forecast_text/{year}/{month}/{day}/*.pdf)
    |
    v
diagnoses_formatting.py --mode via main.py --generate_training_dataset_for_year
    |
    v
formatted_diagnoses_{year}/formatted_diagnoses_{year}.json   <-- ground truth
    |
    +---> dataset_creation.py --mode training      --> train_data.json
    +---> dataset_creation.py --mode few_shot_test  --> test_data.json
    +---> dataset_creation.py --mode zero_shot_test --> test_data_zero_shot.json
            |
            v
    finetuning_pipeline.py (via main.py --finetune)
        train_data.json --> QLoRA training --> fine_tuned_llm/model/final_model/
        test_data.json  --> inference      --> fine_tuned_llm/responses/{approach}/
                                           --> fine_tuned_llm/results/{approach}/

CSV station data (date/bucuresti/*.csv)
    |
    v
main.py --timestamp / --get_test_time_interval
    |
    +---> prompt generation --> prompts/{date}/{N}_past_days/
    +---> ollama_inference  --> responses/{date}/{N}_past_days/
    +---> response_evaluation --> results/{date}/{N}_past_days/
    +---> judge_evaluation    --> llm_as_a_judge/{judge}/{date}/{N}_past_days/
```


## Run scenarios

### 1. Format yearly diagnoses (one-time data preparation)

Extracts Bucharest-section text from every PDF for a year and reformats
each diagnosis into 5 structured sentences via gpt-5-mini. Produces the
`formatted_diagnoses_{year}.json` file that everything downstream reads.

Supports incremental checkpointing: if the run fails partway through,
rerunning the same command skips already-formatted dates.

```
python main.py --generate_training_dataset_for_year 2024 --judge gpt-5-mini
```

### 2. Generate training and test datasets

Creates the JSON files consumed by the fine-tuning pipeline. All three
modes use the same `--past_days` value for consistent historical context.

```
# All three at once (recommended for fresh setup)
python dataset_creation.py --mode all --year 2024 --past_days 4

# Or individually
python dataset_creation.py --mode training --year 2024 --past_days 4
python dataset_creation.py --mode few_shot_test --year 2024 --past_days 4
python dataset_creation.py --mode zero_shot_test --year 2024 --past_days 4
```

Training and few-shot test modes call gpt-5-mini for in-context CoT
exemplars (requires `OPENAI_API_KEY`). Zero-shot test mode does not
require an API key.

### 3. Single-date Ollama inference (PDF-context track)

The original pipeline path. Extracts data for one date, generates prompts
from both PDF forecasts and CSV station data, and runs inference.

```
# Generate prompts and test models
python main.py --timestamp 2024-09-30 --past_days 4 --test_models

# With multi-seed variance estimation (3 seeds per model)
python main.py --timestamp 2024-09-30 --past_days 4 --test_models --n_seeds 3

# Download models first (if not already pulled)
python main.py --timestamp 2024-09-30 --past_days 4 --download_models

# Run statistical analysis on existing responses
python main.py --timestamp 2024-09-30 --past_days 4 --statistical_analysis

# Run LLM-as-a-judge evaluation
python main.py --timestamp 2024-09-30 --past_days 4 --judge_analysis
```

### 4. Multi-date Ollama inference (GPT-CoT track)

The newer pipeline path. Generates dates from a range, uses GPT-CoT
prompts, and runs inference across all dates.

```
# Generate GPT-CoT prompts for a date range
python main.py --get_test_time_interval 2024-01-01 2024-12-31 --past_days 4 --generate_prompts_gpt

# Test models across the date range
python main.py --get_test_time_interval 2024-01-01 2024-12-31 --past_days 4 --test_models

# With 3 inference seeds and custom context window
python main.py --get_test_time_interval 2024-01-01 2024-12-31 --past_days 4 --test_models --n_seeds 3 --num_ctx 16384

# Statistical analysis
python main.py --get_test_time_interval 2024-01-01 2024-12-31 --past_days 4 --statistical_analysis

# Judge analysis with 2 judge runs per response for variance
python main.py --get_test_time_interval 2024-01-01 2024-12-31 --past_days 4 --judge_analysis --n_judge_runs_per_response 2
```

### 5. Fine-tuning pipeline

QLoRA fine-tuning of Llama 3.1 8B Instruct using the pre-generated
dataset files. Requires `train_data.json` and `test_data.json` (or
`test_data_zero_shot.json`) to exist.

```
# Full pipeline: train + test (few-shot)
python main.py --finetune --year 2024 --past_days 4

# Full pipeline: train + test (zero-shot)
python main.py --finetune --year 2024 --past_days 4 --zero_shot

# Training only (skip testing)
python main.py --finetune --year 2024 --skip_testing

# Testing only (skip training, reuse existing model)
python main.py --finetune --year 2024 --past_days 4 --skip_training

# Testing with multi-seed variance estimation
python main.py --finetune --year 2024 --past_days 4 --skip_training --n_seeds 3

# Run both approaches (few-shot + zero-shot testing)
python main.py --finetune --year 2024 --past_days 4 --skip_training --compare

# Use legacy collator (to reproduce pre-cleanup training behavior)
python main.py --finetune --year 2024 --past_days 4 --legacy_collator

# Sweep training seed for variance study
python main.py --finetune --year 2024 --past_days 4 --training_seed 43
```


## New CLI flags reference

| Flag | Type | Default | Used by |
|---|---|---|---|
| `--n_seeds` | int | 1 | Ollama inference, fine-tuning test phase |
| `--n_judge_runs_per_response` | int | 1 | Judge analysis |
| `--training_seed` | int | 42 | Fine-tuning training phase |
| `--legacy_collator` | flag | off | Fine-tuning training phase |
| `--num_ctx` | int | 16384 | Ollama inference |

All flags default to backward-compatible values. Passing none of them
reproduces the behavior of the cleaned pipeline; the only behavioral
difference from the pre-cleanup codebase is the set of bug fixes below.


## Research-affecting bugs fixed in this cleanup

These bugs affected numerical results in the dissertation report. Numbers
derived from affected runs should be regenerated.

### 1. Silent Ollama context truncation (num_ctx=4096)

Ollama 0.11.x defaults to `num_ctx=4096` for most models. Every
non-gpt-oss model at `past_days >= 2` hit this ceiling, silently dropping
prompt tokens. The report's finding that "more past days hurts performance"
and "GPT-OSS dominates" were truncation artifacts, not genuine model
behavior.

**Fix:** `num_ctx=16384` default, explicit in every call, with end-of-run
truncation warnings.

### 2. Silent past_days substitution in fine-tuning

`test_data.json` contained only `past_days=4` entries, but the default
`past_days=5` triggered silent substitution: `past_days=4` prompts were
saved to `5_past_days/` directories and labeled as `past_days=5` in
response JSONs. All `past_days=5` fine-tuning numbers in the report
are invalid.

**Fix:** hard `ValueError` instead of silent substitution.

### 3. Training-vs-test prompt format mismatch

`generate_training_data.py` used a hand-rolled prompt builder with a
3-day historical cap. `create_train_test_datasets.py` used
`create_meteorological_prompts` with full N-day context plus gpt-5-mini
CoT exemplars. The fine-tuned model was trained on one format and
tested against a different one.

**Fix:** both training and testing now use `create_meteorological_prompts`.
Requires retraining.

### 4. DataCollatorForLanguageModeling trained on every token

The pre-cleanup pipeline computed loss on the entire sequence including
system and user prompts, training the model to memorize input format
rather than learn output generation.

**Fix:** default switched to `DataCollatorForCompletionOnlyLM`, which
masks non-response tokens. Use `--legacy_collator` to reproduce the old
behavior.

### 5. BERTScore `lang='en'` on Romanian text

BERTScore was computed with the English-language model. Romanian text
produces systematically lower scores under the English tokenizer.

**Fix:** switched to `xlm-roberta-large` with batch size 64.

### 6. Hardcoded API keys in source files

The OpenAI key `sk-proj-VKbMa_...` and HF token `hf_HTsq...` were
hardcoded in at least 6 locations across the codebase. Both have been
exposed in every context window they were loaded into.

**Fix:** all hardcoded keys removed; replaced with `OPENAI_API_KEY` and
`HF_TOKEN` environment variable resolution. **Rotate both keys
immediately.**

### 7. Inconsistent past_days defaults across scripts

Training data used `past_days=5`, few-shot test data used `past_days=4`,
zero-shot test data used `past_days=5`. Three different historical
context windows across datasets that should be consistent.

**Fix:** single `--past_days` CLI parameter in `dataset_creation.py`
applies to all three modes.

### 8. No seeds in TrainingArguments

Training was non-reproducible: different LoRA initialization, data
order, and dropout masks on every run.

**Fix:** `seed=42` and `data_seed=42` defaults; `--training_seed` CLI
flag for sweeps.

### 9. Broken validate_yearly_extraction

The validation function looked in `formatted_diagnoses_year/` but the
writer saved to `formatted_diagnoses_{year}/`. The function has been
broken (silently finding nothing) for the lifetime of the project.

**Fix:** `validate_yearly_extraction` now accepts and defaults to the
correct output folder.


## What needs rerunning before the next report

1. **Rotate API keys.** Both the OpenAI and HuggingFace tokens found in
   the codebase are compromised and must be replaced.

2. **Regenerate datasets.** Run `dataset_creation.py --mode all` with
   consistent `--past_days` to produce matched-format training and test
   data.

3. **Retrain the fine-tuned model.** The existing `final_model` was
   trained with mismatched prompts, the legacy collator, no seeds, and
   fp16. Retrain with the cleaned pipeline to get valid numbers.

4. **Rerun Ollama inference.** Previous runs at `past_days >= 2` were
   truncated at 4096 tokens. Rerun with the default `num_ctx=16384`.

5. **Rerun evaluation.** BERTScore results under `lang='en'` are
   incomparable with the new `xlm-roberta-large` scores. Regenerate
   all analysis tables.

6. **Rerun judge analysis.** Previous judge runs used hardcoded API keys
   and did not support multi-run variance estimation. Rerun with
   `--n_judge_runs_per_response 3` for error bars.

After these steps, every number in the report is traceable to a
reproducible, seeded, format-matched pipeline run.


## Complete example: full evaluation run for July 2024

The commands below produce a complete evaluation with 3-seed variance
estimation for both Ollama models and the fine-tuned model, including
combined plots.

### Block A: Ollama models on July 10th

```
ollama serve

python main.py --get_test_time_interval 2024-07-10 2024-07-10 --past_days 4 --download_models
python main.py --get_test_time_interval 2024-07-10 2024-07-10 --past_days 4 --generate_prompts_gpt
python main.py --get_test_time_interval 2024-07-10 2024-07-10 --past_days 4 --test_models --n_seeds 3
python main.py --get_test_time_interval 2024-07-10 2024-07-10 --past_days 4 --statistical_analysis
python main.py --get_test_time_interval 2024-07-10 2024-07-10 --past_days 4 --judge_analysis --n_judge_runs_per_response 3
```

Output: `responses/2024-07-10/`, `results/2024-07-10/`,
`llm_as_a_judge/gpt-5-mini/2024-07-10/`.

### Block B: Retrain and test the fine-tuned model

The fine-tuned model tests on the six dates defined in `config.py`
(30th of January, March, May, July, September, November). This block
retrains from scratch with the cleaned pipeline and then runs inference.

```
python dataset_creation.py --mode all --year 2024 --past_days 4
python main.py --finetune --year 2024 --past_days 4 --skip_testing
python main.py --finetune --year 2024 --past_days 4 --skip_training --n_seeds 3
```

Output: `fine_tuned_llm/model/final_model/` (adapter weights),
`fine_tuned_llm/responses/few-shot/` and `fine_tuned_llm/results/few-shot/`
for each of the six test dates.

### Block C: Combine both pipelines on July 30th

To get both Ollama models and the fine-tuned model in the same CSVs and
plots, run Ollama on July 30th, merge the fine-tuned responses into the
Ollama responses folder, and re-evaluate.

```
python main.py --get_test_time_interval 2024-07-30 2024-07-30 --past_days 4 --test_models --n_seeds 3
xcopy /S /Y fine_tuned_llm\responses\few-shot\2024-07-30\4_past_days\*.json responses\2024-07-30\4_past_days\
python main.py --get_test_time_interval 2024-07-30 2024-07-30 --past_days 4 --statistical_analysis
python main.py --get_test_time_interval 2024-07-30 2024-07-30 --past_days 4 --judge_analysis --n_judge_runs_per_response 3
```

Output: `results/2024-07-30/` and `llm_as_a_judge/gpt-5-mini/2024-07-30/`
now contain both Ollama and fine-tuned model rows.

### Block D: Generate plots

```
python generate_metric_plots.py
python generate_plots_llm_as_a_judge.py
```

Output: `plots/` and `plots_llm_as_a_judge/`.

### Date coverage observation

The fine-tuned model can only be evaluated on the six dates in
`config.get_testing_dates()` because those are the dates for which
`test_data.json` contains prompts. The cleaned pipeline raises a hard
`ValueError` if you request a date not present in the test data (the
previous pipeline silently substituted the closest available date,
producing mislabeled results).

This means:

- **On the six config dates (Jan/Mar/May/Jul/Sep/Nov 30th):** full
  comparison between all Ollama models and `Llama-3.1-8B-Instruct-qlora`
  in the same plots.
- **On any other date (e.g., July 10th):** Ollama models only.

To add the fine-tuned model to an arbitrary date, either modify
`config.get_testing_dates()` to include that date before running
`dataset_creation.py --mode few_shot_test`, or manually append an entry
to `test_data.json` with the correct prompt format.

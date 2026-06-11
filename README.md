# Meteorological Diagnosis LLM Evaluation Pipeline

Romanian-language meteorological diagnosis generation and evaluation using
LLMs. Compares Ollama-hosted open-source models, OpenAI API models, and a
QLoRA-finetuned Llama 3.1 8B against structured reference diagnoses from
ANM (Romania's National Meteorological Administration).


## File inventory

Every module in `prompting/utils/` after the cleanup, with its provenance.

| Module | Role | Source |
|---|---|---|
| `check_data_availability.py` | CSV data-quality + preparation utilities. Hosts `check_data_availability` (per-date temporal completeness for the Bucharest hourly CSV) plus a CLI with eight subcommands — `stations`, `monthly_coverage`, `regions`, `temperature`, `county_matrix`, `county_precip`, `county_wind`, `county_nebulosity` — covering cross-file station coverage, per-station monthly-registry audits, the regions/county lookup builder, monthly mean-temperature analysis with neighbour fill, the (T, C) target temperature matrix, and the three auxiliary-variable matrices (precipitation, wind, nebulosity) used as additional input channels by the multi-variable baselines. See "Data preparation utilities" below. | Edited in place |
| `baselines.py` | Time-series forecasting baselines on the county-day matrices. Six baselines (mean, persistence, linear regression, N-BEATS, iTransformer, PatchTST) under one CLI, with 4-fold expanding-window cross-validation, per-county z-score normalisation (log1p for precipitation), horizon-weighted Huber loss, multi-variable input with temp-only output, per-fold weight checkpoints, run labels for before/after experiments, decoupled training/plotting, and a 32-class temperature classification with target-vs-prediction distribution plots. See "Forecasting baselines" below. | **New** |
| `llm_comparison.py` | Unified LLM-vs-baseline comparison framework. Three CLI subcommands (`run`, `baseline_eval`, `plot`): runs the (5 input modes × 7 folds) matrix per Ollama LLM, scores each prediction with both the hyperbolic per-station manual algorithm and an OpenAI gpt-5-mini judge, bridges the W=H=6 baseline checkpoints into the same JSON shape so a single plotter merges both. Includes a Romanian zone parser (regions, climatic zones, cardinal subdivisions with diacritic-insensitive matching), a token-limit detector that writes a separate log when prompts truncate or outputs hit `done_reason=length`, and an OpenAI judge client that reads `OPENAI_API_KEY` from the env only. See "LLM-vs-baseline comparison framework" below. | **New** |
| `config.py` | Calendar split (train/test dates), LoRA hyperparameters, Trainer args | Edited in place |
| `input_extraction.py` | Extract weather data from CSVs and forecast text from PDFs | **New: combined** `extract_data_from_tables.py` + `extract_pdf_data.py` |
| `prompt_construction.py` | Build system/user prompt pairs for both PDF-context and GPT-CoT tracks | **New: combined** `create_prompts.py` + `create_prompts_gpt.py` |
| `ollama_inference.py` | Download and run inference against Ollama-hosted models; auto-includes the QLoRA adapter (if present) on the same prompts | Renamed from `ollama_calls.py` |
| `hf_inference.py` | Load a 4-bit quantized HF model and run inference | Edited in place |
| `finetuning_pipeline.py` | QLoRA fine-tuning orchestrator (train + test + evaluate) | Renamed from `llama_finetuning_pipeline.py` |
| `finetune_integration.py` | Thin CLI wrapper between `main.py` and `finetuning_pipeline.py` | Edited in place |
| `response_evaluation.py` | Compute ROUGE/BLEU/METEOR/BERTScore/Jaccard against references | **New: combined** `postprocessing_romanian.py` + `postprocessing_romanian_gpt.py` |
| `judge_evaluation.py` | LLM-as-a-judge scoring and aggregation tables; accepts `output_dir` override so the fine-tuning pipeline can direct its zero-shot judge output into `fine_tuned_llm/` | **New: combined** `llm_as_a_judge.py` + `judge_analysis_table.py` |
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

# Step 1: Install PyTorch with CUDA 12.6 support 
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
python -c "import torch; assert torch.cuda.is_available(), 'CPU torch still installed'; print('OK:', torch.cuda.get_device_name(0))"

# Step 2: Install remaining dependencies
pip install -r requirements.txt --break-system-packages

# Step 3: Download NLTK data (one-time)
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('wordnet')"
```

Required environment variables (set once, persisted in the Windows
registry via `setx`):

```
setx OPENAI_API_KEY "sk-..."     # prompt generation, judge analysis, diagnoses formatting
setx HF_TOKEN       "hf_..."     # gated HF models (Llama 3.1); not needed for local fine-tuned models
```

`setx` writes to `HKCU\Environment`, so the variables become available to
**new** processes. Close and reopen your terminal (or editor) after
running these once — the current shell is not updated. Verify with
`echo %OPENAI_API_KEY%` (cmd) or `echo $OPENAI_API_KEY` (Git Bash). Do
not commit a wrapper script: prior `set_keys.cmd` conventions have been
removed from the repo to keep secrets out of the working tree.

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
    |       (on the same prompts, if fine_tuned_llm/model/final_model/
    |        exists, the QLoRA adapter is loaded via hf_inference and its
    |        responses are written into the SAME responses/{date}/ folder
    |        with model label "Llama-3.1-8B-Instruct-qlora")
    +---> response_evaluation --> results/{date}/{N}_past_days/
    +---> judge_evaluation    --> llm_as_a_judge/{judge}/{date}/{N}_past_days/
```

The fine-tuned model therefore appears as just another row in every
downstream CSV and plot whenever the adapter is present on disk — no
manual merge step. The fine-tuning pipeline continues to produce its
own zero-shot evaluation under `fine_tuned_llm/results/zero-shot/`
(including a `judge/` subtree added in the latest cleanup), which the
comparison plotter reads to isolate the training effect.


## Data preparation utilities

`prompting/utils/check_data_availability.py` exposes a CLI with eight
subcommands that inspect and shape the raw ANM CSVs in `date/`. Each
writes artefacts back into the same folder (or a custom location via
`--date_folder`).

Subcommand summary:

| Subcommand | Purpose | Output |
|---|---|---|
| `stations` | Cross-file station-coverage audit | `station_coverage.json` |
| `monthly_coverage` | Per-station monthly-registry audit | `missing_dates_{year}.json` |
| `regions` | Build the station → region/county lookup | `stations_by_region.json` |
| `temperature` | Monthly per-station / per-region / per-county / global mean temperature | `temperature_{month}.json` |
| `county_matrix` | (T, 41) county-day **mean temperature** matrix (target variable for forecasting) | `daily_county_mean.csv` + metadata |
| `county_precip` | (T, 41) county-day **precipitation** matrix (auxiliary input) | `daily_county_precip.csv` + metadata |
| `county_wind` | (T, 41) county-day **wind speed** matrix (auxiliary input) | `daily_county_wind.csv` + metadata |
| `county_nebulosity` | (T, 41) county-day **cloud cover** matrix (auxiliary input) | `daily_county_nebulosity.csv` + metadata |
| `combine_stations_metadata` | Merge the three station classification axes (region, climatic zone, regional cardinal direction) into one lookup file used by the LLM-vs-baseline comparison framework | `stations_metadata.json` |

```
python -m prompting.utils.check_data_availability <subcommand> [--flags]
```

The expected input set in `date/`:

| File | Purpose |
|---|---|
| `DateZilniceTemp_*.csv` | Daily Tamax24 / Tamin24 per station. Missing values encoded as `-999` |
| `DateZilnicePrecip_*.csv` | Daily R24 (24-hour precipitation) per station |
| `SirDate_*.csv` | Hourly observations (Rff1 wind, Nop nebulosity, ww/ix weather codes) |
| `statii_meteo.csv` | Authoritative station registry. Columns include `cod_wmo_CODST` (WMO synoptic code), `regiune_CMR` (ANM Centru Meteorologic Regional), `judet_JU` (county code), `nume_NUME` (station name) |

### `stations` — cross-file station coverage audit

Scans every top-level CSV in `--date_folder`, extracts the unique
station names from each, and reports the strict intersection plus the
per-file diff against that intersection. Writes
`station_coverage.json`.

```
python -m prompting.utils.check_data_availability stations --strict
```

`--strict` exits 1 when files disagree, suitable for CI. On the
current data every file holds the same 168 stations
(`all_files_consistent: true`).

### `monthly_coverage` — per-station monthly registry audit

For one CSV, identifies stations with **fully missing months** (all
days absent) and **partially missing months** (at least one day
absent, with the missing dates enumerated). Writes
`missing_dates_{year}.json` with the year derived from the audited
months. "Missing" means the (station, day) row is absent from the CSV
— sentinel-valued readings still count as present (use `temperature`
for sentinel handling).

```
python -m prompting.utils.check_data_availability monthly_coverage --csv_glob "DateZilniceTemp_*.csv"
```

By default, only months whose calendar bounds are fully covered by
the data range are audited; pass `--include_partial_months` to also
flag boundary months. On the 2024 temperature CSV: 2 stations with
fully-missing months (HOREZU 1550 Jan–Apr; IANCA Jan–Sep), 12 with
partial gaps, 156 clean.

### `regions` — build the stations → region/county lookup

Joins `statii_meteo.csv` to the measurement CSV via
`cod_wmo_CODST == Cod sinoptic` (a numeric WMO/synoptic code match —
clean 168/168 overlap; sidesteps the diacritic and abbreviation
differences between the two name conventions). Writes
`stations_by_region.json` with the nested structure
`region → county → [stations]`.

```
python -m prompting.utils.check_data_availability regions
```

The nested form is the source of truth: `_load_station_metadata`
walks it to derive both `{station → region}` and `{station → county}`
mappings. Per-station details (judet code, WMO code) are intentionally
not duplicated into this JSON — they live in `statii_meteo.csv`.

Re-run any time `statii_meteo.csv` changes. Current data: 168 stations
across 7 ANM regions (Banat-Crisana 28, Dobrogea 23, Moldova 23,
Muntenia 31, Oltenia 21, TransilvaniaN 15, TransilvaniaS 27) and 41
counties.

### `temperature` — monthly mean temperature with neighbour fill

Reads the daily temperature CSV and computes per-station, per-region,
per-county, and global mean temperature for one month, after filling
sentinel-marked missing cells from neighbouring days. Writes
`temperature_{month}.json`.

```
python -m prompting.utils.check_data_availability temperature --month 2024-03 --fill_window_days 3
```

Fill semantics: each missing (station, day, column) cell averages the
valid values from days `t-N..t+N` for the same station, excluding `t`
itself so a valid centre doesn't bias its own fill. The window may
extend outside the target month. Tmax and Tmin are filled
independently; cells with no valid neighbour stay missing and are
dropped from downstream means.

Per-region and per-county means use **macro-average** of per-station
monthly means inside each group — each station counts equally,
matching the global-mean convention. Drives the same `--regions_filename`
(default `stations_by_region.json`) for both groupings, and surfaces
stations the regions file expected but that had no usable data for
the target month under `stations_missing`.

### `county_matrix` — multivariate baseline input tensor

Builds the (T, C) county-day mean-temperature matrix that the
forecasting baselines (see below) consume as input. Pipeline:

```
raw rows
  → sentinel masking (sentinel → NaN)
  → station-level neighbour fill (±--fill_window_days)
  → per-station daily mean = (Tamax + Tamin) / 2
  → per-county daily mean (macro average of station means)
  → wide matrix: rows = date, columns = county code
  → fallback fill for any county-day NaN:
       (a) same-day region mean
       (b) same-day global mean if region also NaN
```

```
python -m prompting.utils.check_data_availability county_matrix
```

Writes two files:

- `daily_county_mean.csv` — wide matrix indexed by `date` (YYYY-MM-DD)
  with one column per county code (41 columns, alphabetical). On
  current 2024 data: 367 × 41, **no NaN cells** — loads straight into a
  PyTorch tensor.
- `daily_county_mean_metadata.json` — provenance + fallback audit.
  Records `station_fill_stats` (per-column missing/filled/remaining
  counts), `matrix_fill_stats` (cells from county aggregation vs each
  fallback path), and the exact `(date, county)` pairs each fallback
  was applied to.

On the current data, 15,046 of 15,047 cells come from direct county
aggregation; the single fallback hit was `2024-09-30 / BR` (Brăila
has only the BRAILA station, which had a one-day registry gap), filled
from the Muntenia regional mean. The IANCA nine-month gap is invisible
at the county level because Constanța (CT) has 8 other stations.

Use as the **target** input to the forecasting baselines (see below).
Combine with the three auxiliary-variable matrices (`county_precip`,
`county_wind`, `county_nebulosity` below) for the multi-variable
input case.

### `county_precip` — auxiliary precipitation matrix

Mirrors `county_matrix` but on `DateZilnicePrecip_*.csv`, producing a
(T, 41) matrix of **raw R24 in mm/day**. Two differences from temp:

1. **Date attribution shift (`--date_shift_days -1` by default).** ANM
   stamps each precipitation row with the ~05:30 morning observation
   time of date D, but the R24 value reports the 24-hour accumulation
   ending at that moment — i.e. the rain that fell on (D − 1). The
   shift moves the matrix index from "observation date" to "calendar
   day the rain actually fell on". Pass `--date_shift_days 0` to
   disable.
2. **No transform at write time.** The CSV stores raw mm/day so the
   file is interpretable as a physical quantity. The baseline pipeline
   applies `log1p` before z-score at training time (precipitation is
   heavily right-skewed: most days near zero, occasional heavy events).

```
python -m prompting.utils.check_data_availability county_precip
```

Writes `daily_county_precip.csv` (367 × 41, no NaN cells, raw mm/day)
and `daily_county_precip_metadata.json` (same fallback audit + an
explicit `date_shift_days` field plus a written-out
`date_shift_explanation`).

### `county_wind` — auxiliary wind matrix

Mirrors `county_matrix` but on the **hourly** `SirDate_*.csv` (column
`Rff1`, wind speed in m/s). Two-stage reduction:

```
STAGE A: hourly readings  →  (station, day):
           mean of valid Rff1 over the ~24 hourly readings within
           each calendar day, per station

STAGE B: (station, day)  →  (county, day) wide matrix:
           identical to county_matrix
           (neighbour fill → county mean → region/global fallback)
```

Stage A uses the **calendar day** (00:00–23:59), not the meteorological
08:30→06:30 window the LLM-prompt pipeline uses, so the date axis
aligns 1:1 with `daily_county_mean.csv` for direct multi-variable
stacking.

```
python -m prompting.utils.check_data_availability county_wind
```

Writes `daily_county_wind.csv` (367 × 41, raw m/s) and
`daily_county_wind_metadata.json`. On the 2024 data:
~24,400 hourly rows carried the `-999` sentinel; the remaining
60,326 valid (station, day) cells reduced cleanly with no
region/global fallback needed.

### `county_nebulosity` — auxiliary cloud cover matrix

Same shape as `county_wind` but operating on `Nop` (cloud cover, WMO
2700 octa scale). The sentinel set is wider: `-999`, `NaN`, the
string sentinel `/` (observation not made), and **`9` (sky obscured
/ unobservable)** are all treated as missing per the WMO 2700 scheme.
Valid values are `0` (clear sky) … `8` (fully overcast). The
station-day reduction is **mean** of valid 0..8 values (continuous
float, more informative for regression than the discrete mode used
by the LLM-prompt pipeline).

```
python -m prompting.utils.check_data_availability county_nebulosity
```

Writes `daily_county_nebulosity.csv` (367 × 41, values in `[0, 8]`)
and `daily_county_nebulosity_metadata.json`. On the 2024 data the
sentinel breakdown is detailed in the metadata: ~600K `/`, 30,254 `9`
obscured (filtered), 0 `-999`.

### `combine_stations_metadata` — unified station classification lookup

Merges the three single-axis classification JSONs into a single file
that the LLM-vs-baseline comparison framework uses to resolve zone
mentions in Romanian text:

```
stations_by_region.json                 region   -> county -> [stations]
stations_by_climatology.json            climatic zone     -> [stations]
stations_by_regional_cardinal_points.json  region+cardinal -> [stations]
```

merge into

```
stations_metadata.json
  - stations_by_region                  (verbatim)
  - stations_by_climatology             (verbatim)
  - stations_by_regional_cardinal_points (verbatim)
  - stations_by_county                  derived: county -> [stations]
  - station_to_county                   derived: station -> county
```

```
python -m prompting.utils.check_data_availability combine_stations_metadata
```

Run any time one of the three source files changes. Default 2024 data:
168 stations, 7 regions, 41 counties, 9 climatic zones, 28 regional
cardinal-point cells.

### Combined input shape for the baselines

```
Single-variable input  (temp only):    (W, 41)
Multi-variable input  (T+P+W+N stack): (W, 41 × 4) = (W, 164)
Output (always temperature):           (H, 41)
```

Position in the tensor encodes county identity within a variable block
(channel 0 = AB, channel 40 = VS), and the variable blocks are stacked
in the order the loader receives them: target (temp) first, then
extras in the order passed to `--extra_csvs`.


## Forecasting baselines

Time-series forecasting baselines on the (T, C) county-day mean
temperature matrix from `county_matrix`. Six baselines, selectable
through a single CLI dispatcher (`prompting/utils/baselines.py`):

| Baseline | Type | Architecture |
|---|---|---|
| `mean` | Closed-form | Predict the per-channel mean of the input window, repeated H times |
| `persistence` | Closed-form | Predict the last input timestep, repeated H times |
| `linear_regression` | Trained | Direct multi-output linear: flatten `(W, C)` → `Linear(W·C → H·C)` → reshape |
| `nbeats` | Trained | Generic N-BEATS: stack of 3 blocks × 4 FC layers each, backcast residual connections, forecast accumulation |
| `itransformer` | Trained | **iTransformer** (Liu et al., ICLR 2024). Each county becomes one token embedded from its W-step series; self-attention runs across the 41 variate tokens; per-token linear head emits the H-step forecast. Variate-mixing, no decoder |
| `patchtst` | Trained | **PatchTST** (Nie et al., ICLR 2023). Each county's W-step series is split into overlapping patches (`patch_len=4`, `stride=2`); attention runs across temporal patches; the same encoder weights process every county independently. Channel-independent, no decoder |

iTransformer attends across counties (cross-county correlations,
no temporal attention); PatchTST attends across temporal patches
within each county (channel-independent, no cross-county influence).
The two architectures are deliberately complementary.

### Shape conventions

```
Single-variable mode (default):
    Input matrix:    (T, 41) = (367, 41)        daily mean temperature
    Per sample:      X = (W, 41) = (10, 41)     input window
                     Y = (H, 41) = (10, 41)     forecast target

Multi-variable mode (--extra_csvs):
    Input matrix:    (T, C·K)                   K = 1 + len(--extra_csvs)
                     For the canonical "temp + precip + wind + nebulosity"
                     stack: K = 4, channels = 164
    Per sample:      X = (W, 164)               input window with all variables
                     Y = (H, 41)                forecast target — TEMPERATURE ONLY
    Date axis:       intersection across every loaded CSV
                     (precip is backshifted by 1 day so its date span and the
                      others' reduce to a common 2024-01-01..2024-12-31 window)

Channel layout (multi-variable):
    Channels  0..40  -> temperature (target, alphabetical by county)
    Channels 41..81  -> precipitation (same county order)
    Channels 82..122 -> wind
    Channels 123..163-> nebulosity

Channel order within each variable block: alphabetical by county code
(AB, AG, AR, B, ..., VS). Position encodes BOTH county identity AND
variable identity - no explicit embedding required.
```

One sample per windowed slide along the day axis (not per county). The
auxiliary variables are **inputs only**; the output is always
temperature for all 41 counties.

### Normalisation

**Per-county z-score, fit on the training fold only** (no leakage), with
a per-variable transform applied first:

```
                              transform before z-score
  variable_label              ----------------------------
  mean_temp                   identity
  precip                      log1p   (R24 is heavily right-skewed
                                       with a zero-mass on dry days;
                                       log1p compresses the long tail
                                       while keeping zeros at zero)
  wind                        identity
  nebulosity                  identity

For each variable block of C channels in the training fold:
    1. apply the variable's transform
    2. compute (mu_i, sigma_i) per channel i, i.e. per county
    3. (X - mu) / sigma                          on test inputs too
    4. predictions stay in z-score space during training
    5. denormalise predictions back to degC before metrics
       (target = identity transform, so this is just `pred * sigma + mu`)
```

The scaler returns `(mean, std, transforms)` of shape `(C·K,), (C·K,), [K]`.
The target scaler reuses the first C entries of the input scaler since
target (temperature, identity-transformed) is the first variable block.

Closed-form baselines (Mean, Persistence) skip the scaler — they are
scale-equivariant by construction. When multi-variable input is passed
they slice the **target block** (first C channels) out of `X` before
computing their statistic, so their predictions only ever depend on
past temperatures, not on precip/wind/nebulosity.

Reported RMSE/MAE for every baseline are always in °C in the original
space.

### Loss (trained baselines)

Exponential horizon-weighted **Huber** loss:

```
w_t   = exp(-decay * t)                       t in {0, ..., H-1}
h(a)  = 0.5 * a^2                             if |a| <= delta
      = delta * (|a| - 0.5 * delta)           otherwise
loss  = mean_{B, H, C} ( w_t * h(pred - target) )
```

`--decay 0.05` weights step 1 ~1.0 and step 10 ~0.61. `--huber_delta 1.0`
puts the MSE/MAE transition at one z-score std. Direct multi-output —
all H steps are emitted in a single forward pass; no autoregressive
rollout during training.

### Walk-forward cross-validation

4 folds (default), expanding window. The windowed sample axis is split
into `--folds + 1 = 5` near-equal slices; fold `i` trains on slices
`0..i` and tests on slice `i+1`. For the 348 windowed samples in the
2024 data:

| Fold | Train samples | Test samples |
|---|---|---|
| 1 | 69  | 70 |
| 2 | 139 | 69 |
| 3 | 208 | 70 |
| 4 | 278 | 70 |

Each fold's trained model is fit from scratch on its train slice with
a fold-specific seed (`--seed + fold_index`). **Fold 4 is the
largest-training-set instance and is the closest match to the model
that would be deployed for future predictions** — read fold 4 as the
deployment row when comparing baselines.

### Multi-variable inputs (auxiliary channels)

`--extra_csvs` stacks one or more auxiliary `daily_county_*.csv` files
alongside the target temperature matrix to produce a wider input
tensor. The output remains temperature-only:

```cmd
%PY% -m prompting.utils.baselines --baseline all --epochs 500 ^
    --extra_csvs daily_county_precip.csv daily_county_wind.csv daily_county_nebulosity.csv
```

**Closed-form baselines are auto-skipped in this mode.** Because Mean
and Persistence slice the target block (first `C` channels) before
computing their statistic, the auxiliary channels never reach them
and their predictions would be essentially identical between the
temp-only and multi-variable runs (modulo a one-sample fold-edge
shift from the date intersection). When `--extra_csvs` is set, the
runner prints a `Note: skipping closed-form baselines [...]` line and
only trains the four learned baselines. The matching temp-only run
already produced the reference Mean/Persistence curves, so the
comparison plot picks them up automatically — you get 10 lines in
total (Mean and Persistence each once; the four trained baselines
twice — `[temp_only]` and `[with_aux]`).

What each model does with the extra channels:

| Baseline | How auxiliary channels enter |
|---|---|
| `mean`, `persistence` | **Skipped** when `--extra_csvs` is set (see above). The temp-only run produces the canonical curve |
| `linear_regression` | Flattens `(W, C·K)` and projects to `(H, C)` through one fully-connected layer. Auxiliary inputs influence every output via the linear map |
| `nbeats` | Residual lives in `(W·C·K)`-dim space; the forecast head writes only `(H·C)` values, so backcast and forecast have asymmetric dimensions |
| `itransformer` | Each of the `C·K` variates becomes a token; self-attention runs across all of them (so e.g. a temperature variate token can attend to a precip variate token in another county). Final head produces `(B, C·K, H)`; the first `C` tokens are sliced as the output |
| `patchtst` | Channel-independent — every variate runs through the same shared encoder. Final head produces `(B, C·K, H)`; the first `C` tokens are sliced as the output. Cross-variable structure is **not** modelled (the architectural contrast with iTransformer) |

### Weight save/load and run labels

For before/after experiments, two CLI flags let multiple runs coexist:

- **`--label SUFFIX`** appends `_SUFFIX` to the metrics JSON name and
  any saved checkpoints, so the temp-only run and the multi-variable
  run can sit side by side under one `--output_dir`. The plotter reads
  the label from each JSON and prints `<baseline> [<label>]` in the
  legend.
- **`--save_weights`** saves a per-`(baseline, fold)` checkpoint to
  `{output_dir}/checkpoints/{baseline}{_label}_fold{i}.pt`. Each
  checkpoint contains:
  - `model_class` + `model_init_kwargs` — enough to reconstruct the
    right `nn.Module` subclass
  - `model_state_dict` — learned weights
  - `scaler` — `x_mean`, `x_std`, `transforms`, `n_channels_per_var`,
    `y_mean`, `y_std`
  - `metadata` — `variable_labels`, `counties`, `window`, `horizon`,
    `epochs`, `seed`, `train_date_range`

The `load_fold_checkpoint(path)` helper in `prompting/utils/baselines.py`
rehydrates a fully-loaded model + scaler from a checkpoint file
without needing any of the original CLI flags.

### Temperature classification (test-time)

In addition to RMSE/MAE, every fold's predictions and targets are
bucketed into a **32-class temperature scheme**:

```
class  0      <-20 degC
classes 1..30 contiguous 2-degC bins from -20 to +40:
              [-20,-18), [-18,-16), ..., [38,40)
class 31      >= +40 degC
```

Per-fold counts of both arrays are saved as `target_class_counts` and
`prediction_class_counts` (lists of 32 ints each) inside each
metrics JSON's `per_fold[i]` block.

The plotter renders two kinds of figures:

- `class_distribution_target.png` — single figure, 2×2 grid (one
  subplot per fold), bars colour-coded by class on the `RdYlBu_r`
  palette (blue = cold, red = hot). The same test-set targets across
  all baselines, drawn once as a reference.
- `class_distribution_{baseline}{_label}.png` — one figure per
  metrics JSON, also a 2×2 grid. Two bars per class side-by-side:
  solid colour-coded target, hatched colour-coded prediction. The
  asymmetry between the two bars at each class shows where the model
  over- or under-predicts that part of the temperature range.

### Standardised plot scales

All per-fold and class-distribution figures use a **single global
y-axis range** computed from the worst data point across every
loaded run, with a small headroom multiplier and a tick-friendly
ceiling (next whole degree for error plots, next 100 for class
counts). This means:

- The 4 fold subplots of `per_horizon_rmse_per_fold.png` share the
  same y-range — and that range is also fixed if you re-plot after
  changing the JSON set, so two runs of `--plot_only` produce
  visually-comparable PNGs.
- Every `class_distribution_*.png` figure uses the same y-range, so
  `mean` vs `linear_regression [with_aux]` are directly comparable
  at a glance without re-eyeballing the axis.

This replaces matplotlib's auto-scaling per figure, which used to
make the worst baseline pin the others against the bottom edge.

### Autoregressive multi-step rollout

A trained model only produces an H-step direct forecast. To probe
how it degrades over longer horizons (e.g. 30 days), the
`--autoregressive_*` flags feed the model's own predictions back as
input for the next chunk, repeating until the requested total is
reached.

**Flags** (all three needed to activate this mode; replaces
training):

| Flag | Default | Purpose |
|---|---|---|
| `--autoregressive_total_days N` | required | How many days to predict in total (e.g. 30) |
| `--autoregressive_start_date YYYY-MM-DD` | required | First day of the initial input window. Days `[start, start + W − 1]` are the known input; days `[start + W, start + W + N − 1]` are predicted |
| `--autoregressive_fold I` | 4 | Which fold's checkpoint to use. Default 4 = the largest-training-set / deployable model |

**Mechanics**

For each trained-baseline checkpoint matching the fold under
`{output_dir}/checkpoints/`:

1. Load the model + scaler + constructor kwargs from the checkpoint.
2. Take the known input window of W days starting at `start_date`,
   normalise it via the saved scaler, run one forward pass to produce
   H predicted days.
3. Slide the window by H days, replacing the new tail with the H
   predicted values. For multi-variable checkpoints the auxiliary
   channels of the new tail come from **ground-truth** values in the
   data matrix (the aux variables are not autoregressively forecast,
   only the target). For temp-only checkpoints there's nothing else
   to fill.
4. Run the next forward pass on the slid window. Repeat until
   `total_days` steps have been produced.

**Per-baseline figure** (`autoregressive_{baseline}{_label}_fold{i}_{start_date}_{N}d.png`):

A side-by-side two-panel layout:

- **LEFT**: the model's **initial** single-shot prediction (just one
  forward pass, the first H days). Ground truth (solid black) +
  initial prediction (dashed). Title carries the initial RMSE.
- **RIGHT**: the model's **full autoregressive** trajectory across all
  `total_days`. Ground truth (solid black) + autoregressive prediction
  (solid colour). Vertical guide lines mark every H-step chunk
  boundary so the typical degradation pattern (each subsequent chunk
  drifts further from the truth) is visible. Title carries the
  overall AR RMSE plus the first-chunk and last-chunk RMSEs so the
  degradation magnitude is explicit.

Y-axis is shared between the two subplots so the comparison is fair.

**Closed-form baselines have no checkpoints** (they're parameter-free),
so the autoregressive mode only emits figures for the four trained
baselines.

**Command**

```cmd
%PY% -m prompting.utils.baselines ^
    --autoregressive_total_days 30 ^
    --autoregressive_start_date 2024-11-01 ^
    --autoregressive_fold 4
```

Use `--extra_csvs ...` alongside the flags to run the rollout against
multi-variable checkpoints (the aux channels will come from
ground-truth values in the matrix).

### Workflow

Training and plotting are **decoupled**. Training writes JSONs (and
optionally checkpoints); plotting reads the JSONs and produces all
per-fold figures.

**End-to-end before/after experiment**

```cmd
set PY=C:\Users\sateliti1\AppData\Local\anaconda3\envs\meteollm\python.exe
cd /d F:\Claudiu\metframe

REM ---- 1. Build all four county-day matrices (one-time, until source CSVs change) ----
%PY% -u -m prompting.utils.check_data_availability county_matrix
%PY% -u -m prompting.utils.check_data_availability county_precip
%PY% -u -m prompting.utils.check_data_availability county_wind
%PY% -u -m prompting.utils.check_data_availability county_nebulosity

REM ---- 2. Train all baselines on temperature only (BEFORE) ----
%PY% -u -m prompting.utils.baselines --baseline all --epochs 500 ^
    --label temp_only --save_weights

REM ---- 3. Train all baselines with auxiliary inputs (AFTER) ----
REM      `--baseline all` is still used; the runner auto-skips closed-form
REM      baselines for this multi-variable pass and only trains the four
REM      learned ones. The 'Note: skipping closed-form baselines [...]'
REM      console line confirms it.
%PY% -u -m prompting.utils.baselines --baseline all --epochs 500 ^
    --label with_aux --save_weights ^
    --extra_csvs daily_county_precip.csv daily_county_wind.csv daily_county_nebulosity.csv

REM ---- 4. Regenerate all plots from the JSONs ----
%PY% -u -m prompting.utils.baselines --plot_only

REM ---- 5. Interactive zoom (optional) ----
%PY% -u -m prompting.utils.baselines --plot_only --show

REM ---- 6. (Optional) autoregressive rollout from fold 4 deployable model ----
%PY% -u -m prompting.utils.baselines ^
    --autoregressive_total_days 30 --autoregressive_start_date 2024-11-01 ^
    --autoregressive_fold 4

REM ---- 7. (Optional) autoregressive on multi-variable models ----
%PY% -u -m prompting.utils.baselines ^
    --autoregressive_total_days 30 --autoregressive_start_date 2024-11-01 ^
    --autoregressive_fold 4 ^
    --extra_csvs daily_county_precip.csv daily_county_wind.csv daily_county_nebulosity.csv
```

Tips:

- `--baseline all` runs every baseline in sequence (mean → persistence → linear_regression → nbeats → itransformer → patchtst). Pick a single baseline by name to run it alone.
- Delete or move a subset of `*_metrics.json` files between `--plot_only` invocations to plot only the ones you care about — no retraining needed.
- `--show` opens interactive matplotlib windows with the zoom/pan/home toolbar so you can drill into regions where baselines cross. Blocks until every window is closed.

### Outputs

After the full before/after pipeline (steps 1–5 above) plus the
optional autoregressive rollout (step 6):

```
baselines/
├── mean_temp_only_metrics.json                       ← closed-form, only one variant
├── persistence_temp_only_metrics.json                ← closed-form, only one variant
├── linear_regression_temp_only_metrics.json
├── linear_regression_with_aux_metrics.json
├── nbeats_temp_only_metrics.json
├── nbeats_with_aux_metrics.json
├── itransformer_temp_only_metrics.json
├── itransformer_with_aux_metrics.json
├── patchtst_temp_only_metrics.json
├── patchtst_with_aux_metrics.json
│
├── per_horizon_rmse_per_fold.png         ← 10 lines overlaid, 4 subplots
├── per_horizon_mae_per_fold.png          ← 10 lines overlaid, 4 subplots
├── fold_distributions.png                ← target value distributions per fold
├── class_distribution_target.png         ← reference: target class hist per fold
├── class_distribution_mean_temp_only.png
├── class_distribution_persistence_temp_only.png
├── class_distribution_{trained-baseline}_temp_only.png    ← 4 of these
├── class_distribution_{trained-baseline}_with_aux.png     ← 4 of these
│
├── autoregressive_{baseline}_{label}_fold4_{date}_30d.png  ← one per trained
│                                                              checkpoint, when
│                                                              --autoregressive_*
│                                                              is used
│
└── checkpoints/                          ← only when --save_weights was set
    ├── linear_regression_temp_only_fold{1..4}.pt
    ├── linear_regression_with_aux_fold{1..4}.pt
    ├── nbeats_temp_only_fold{1..4}.pt
    ├── ...
    └── patchtst_with_aux_fold{1..4}.pt
```

(Mean and Persistence are closed-form, so they have no checkpoints —
their predictions are deterministic from `X` alone. They also only
appear under `temp_only` because the runner skips them for the
multi-variable pass.)

Each baseline's JSON carries:

- `baseline`, `label`, `variable_labels` — identifying which variant produced this file
- `aggregate_across_folds` — mean RMSE/MAE overall and per-horizon (computed for inspection but **not plotted**; averaging across folds hides the training-set-size effect)
- `per_fold[i]` — RMSE/MAE overall, per-horizon, per-county, plus `n_train_samples`, `n_test_samples`, `train_date_range`, `test_date_range`, `target_class_counts` (list of 32 ints), `prediction_class_counts` (list of 32 ints)
- `training` (trained baselines only) — `epochs`, `lr`, `weight_decay`, `loss: horizon_weighted_huber`, `huber_delta`, `batch_size`, `normalize`, `seed`, plus baseline-specific hparams

The per-fold error plots are 2×2 grids (one subplot per fold) with
every baseline-label combo overlaid. Mean and Persistence are drawn
dashed; the four trained baselines are solid. `sharex/sharey=True`
so absolute error levels are visually comparable across folds. Each
subplot's title includes `n_train` so the training-set-size axis is
explicit.

### CLI reference

| Flag | Default | Used by |
|---|---|---|
| `--baseline` | required | All. `all` runs every baseline in sequence. Not required when `--plot_only` is set |
| `--window` | 10 | All |
| `--horizon` | 10 | All |
| `--folds` | 4 | All |
| `--csv_filename` | `daily_county_mean.csv` | Target-variable matrix; always the first channel block of the input |
| `--extra_csvs` | none | Trained / closed-form. Space-separated list of additional `daily_county_*.csv` files to stack as input channels. Output stays temperature-only |
| `--decay` | 0.05 | Trained (loss horizon weights) |
| `--huber_delta` | 1.0 | Trained (Huber transition threshold) |
| `--epochs` | 300 | Trained |
| `--lr` | 1e-3 | Trained (AdamW) |
| `--weight_decay` | 1e-4 | Trained (AdamW) |
| `--batch_size` | 32 | Trained |
| `--no_normalize` | off | Trained (disable per-county z-score; precip log1p is also skipped) |
| `--seed` | 42 | Trained |
| `--label` | empty | All. Suffix appended to JSON / checkpoint filenames so before/after runs coexist |
| `--save_weights` | off | Trained. Save per-(baseline, fold) checkpoints to `{output_dir}/checkpoints/` |
| `--hidden` | 128 | `nbeats` only |
| `--n_blocks` | 3 | `nbeats` only |
| `--n_layers` | 4 | `nbeats` only (FC layers per block) |
| `--d_model` | 128 | `itransformer`, `patchtst` |
| `--n_heads` | 4 | `itransformer`, `patchtst` |
| `--n_enc_layers` | 3 | `itransformer`, `patchtst` |
| `--ff` | 256 | `itransformer`, `patchtst` |
| `--dropout` | 0.1 | `itransformer`, `patchtst` |
| `--patch_len` | 4 | `patchtst` only (must be ≤ `--window`) |
| `--stride` | 2 | `patchtst` only |
| `--device` | auto | Trained (auto picks CUDA when available) |
| `--output_dir` | `baselines` | All |
| `--plot_only` | — | Mode switch: skip training, just regenerate figures |
| `--show` | off | With `--plot_only`, also open interactive zoomable windows |
| `--autoregressive_total_days` | none | Mode switch: skip training and run an N-day autoregressive rollout from saved checkpoints. Requires `--save_weights` to have been used at training time |
| `--autoregressive_start_date` | none | Required with `--autoregressive_total_days`. First day of the initial input window in `YYYY-MM-DD` |
| `--autoregressive_fold` | 4 | Which fold's checkpoint to use for the rollout (4 = deployable) |


## LLM-vs-baseline comparison framework

`prompting/utils/llm_comparison.py` evaluates open-source Ollama LLMs
and the forecasting baselines on a common axis: produce a Romanian
paragraph describing temperature ranges per ANM zone for a target
month, then score it against the ANM ground-truth paragraph. The
framework is the bridge between the qualitative ANM-style narrative
and the quantitative county-day matrix used by the baselines, and it
produces a single comparison plot that includes both families.

### Three subcommands

| Subcommand | Purpose | Output |
|---|---|---|
| `run` | Runs the (5 input modes × 7 folds) test matrix for **one** Ollama LLM and writes a per-model JSON for the plotter | `llm_runs/llm_runs_<model>.json` plus, if any prompt truncates or any output is cut off, an append-only line in `llm_runs/logs/token_limits_<model>.log` |
| `baseline_eval` | Walks every `_fold4.pt` checkpoint under `baselines/checkpoints/`, runs an autoregressive rollout at K∈{6, 12, 18, 24} known days of the target month (default November, matches the LLM runner's `daily_test_month`), synthesises a paragraph from per-zone aggregates, scores with the same manual + (optional) judge pipeline used for LLMs | `llm_runs/llm_runs_baseline_<baseline>_<label>.json` (one per checkpoint, schema-compatible with `run`) |
| `postprocess` | Re-applies the fluent-Romanian rewriter over every `llm_runs_*.json` without rerunning any LLM. Useful for iterating on the rewriter (quantifier handling, snapping, unit formats) once raw paragraphs are already on disk | Updates `predicted_paragraph_fluent` in place; optionally writes `.json.bak` backups |
| `plot` | Aggregates every `llm_runs/llm_runs_*.json` (LLMs and baselines together), writes a flat CSV summary, per-scenario accuracy curves vs fold size, manual-vs-judge agreement scatter, and a side-by-side top-3-paragraphs comparison per model (ranked by manual + by judge) | `llm_runs/plots/summary.csv`, `llm_runs/plots/llm_{manual,judge}_accuracy_{monthly,daily}.png`, `llm_runs/plots/manual_vs_judge_<model>.png`, `llm_runs/plots/top3_comparison_<model>_by_{manual,judge}_accuracy.png` |

```
python -m prompting.utils.llm_comparison <subcommand> [--flags]
```

### Eight input modes × two scenarios = 56 evaluations per model

The runner iterates a Cartesian product:

```
modes:      historic_only                  text from past months' ANM diagnoses
            historic_plus_temp             text + per-zone monthly temperature
            historic_plus_aux              text + temp + precip + wind + nebulosity
            temp_only                      no text, just per-zone temperature
            aux_only                       no text, no temp, just aux numbers
            historic_only_with_prior       historic_only + target-month paragraphs
                                           from prior years (default 3 most recent)
            historic_plus_temp_with_prior  historic_plus_temp + prior-year context
            historic_plus_aux_with_prior   historic_plus_aux + prior-year context
scenarios:  monthly  folds = (3, 6, 9)         K known months -> predict month K+1
            daily    folds = (6, 12, 18, 24)   K known days   -> predict full month
                                               (default target = November)
```

A "fold" here is the number of **known** historical units (months or
days) the model sees in the user prompt — the scenario analogue of
the baselines' `--folds` count.

The three `*_with_prior` modes augment their base mode with target-
month ANM paragraphs from the `--n_prior_years` years preceding the
target year (default 3, counting down). With `--year 2024
--n_prior_years 3`, each `*_with_prior` user prompt has an extra
`CARACTERIZARI ISTORICE PENTRU LUNA <X> DIN ANII ANTERIORI` section
showing paragraphs from 2023, 2022 and 2021 (whichever
`historic_data_<year>.json` files are present in `--date_folder`;
missing years are silently skipped). Setting `--n_prior_years 0`
filters the prior-year modes out of the run, falling back to the
original 5×7 = 35-eval matrix.

The November default for the daily scenario gives the model the
longest possible in-year context window (10 prior months of ANM
text, Jan..Oct) — change with `--daily_test_month` if you want a
different seasonal regime.

### Zone vocabulary

Every paragraph (GT or model output) is parsed via an exhaustive
Romanian-language regex + lookup that recognises three classification
axes simultaneously, with diacritic-insensitive matching so
`Muntenia` / `muntenia` / `în Muntenia` / `sud-estul Munteniei` all
resolve correctly:

| Axis | Examples | Resolution |
|---|---|---|
| **Region** | `Muntenia`, `Transilvania`, `Banatului`, `nordul Moldovei` | one of the 7 ANM regions, optionally with a cardinal direction (`N`, `S`, `E`, `V`) |
| **Climatic zone** | `Delta Dunării`, `Litoralul Mării Negre`, `Subcarpaţii`, `Depresiuni intramontane` | one of the 9 ANM climatic zones |
| **Regional cardinal** | `sud-est`, `nord-vest` | resolved to the first component per spec (`sud-est` → `S`, `nord-vest` → `N`); `interiorul arcului carpatic` maps to `Depresiuni intramontane` |

Each zone record carries `axis`, `ident`, optional `cardinal`, and the
expanded `stations` list. Used in two places:

- **Prompt construction** — the known months' GT paragraphs are
  parsed, the zones are deduped across months, and the result becomes
  the "main regions" the model must cover.
- **Output parsing** — every sentence of the model's reply is split,
  zones in the sentence are mapped to the nearest `[a, b]` interval
  in the same sentence (by character distance, so word order doesn't
  matter), producing a `{zone, interval}` record per sentence.

### Required output format — the `[x, y]` brackets

The system prompt is explicit:

```
Output a Romanian paragraph covering every main region listed below.
For each region (or subdivision) emit a sentence with a TEMPERATURE
range of the form [x, y] where x and y are the boundaries of a
2 degC bin (i.e. y - x = 2 and x is even).

Examples:
    In Muntenia, mediile lunare au fost cuprinse intre [22, 24] degC.
    Pe Litoralul Marii Negre, valorile au variat intre [16, 18] degC.

Do NOT use fluent Romanian here for the interval - the post-processor
will reword [x, y] into "intre x si y degC" automatically.
```

**Output is ALWAYS temperature, never aux variables.** The system
prompt has a dedicated CONSTRANGERE FUNDAMENTALA section that forbids
emitting `[x, y]` intervals for precipitation (mm), wind (m/s) or
nebulosity (octa) even in `historic_plus_aux` and `aux_only` modes
where the user prompt contains those numbers as input context. Every
`[x, y]` the model emits is implicitly in °C; the unit `°C` may
appear *after* the brackets but no other unit ever may. This is
critical because the regex parser is unit-agnostic — without the
constraint, a `[5, 15] mm` for rain would be ingested as a 5–15 °C
temperature interval and `manual_score` would produce nonsense
distances against the GT.

**Integer-anchored 2 °C grid + automatic snapping.** Format rule 2
of the system prompt also requires `x` and `y` to be integers, `x`
even, and `y = x + 2` — i.e. intervals must sit on the standard ANM
grid `..., [-4, -2], [-2, 0], [0, 2], [2, 4], ...`. Some models will
nonetheless emit floats, odd-anchored integers, or off-width pairs.
Rather than drop those predictions, the parser snaps them by
midpoint via `_snap_to_2c_bin` (in `prompting/utils/llm_comparison.py`):

```
m         = (x_raw + y_raw) / 2
bin_start = 2 * floor(m / 2)
[x_snap, y_snap] = [bin_start, bin_start + 2]
```

Examples:

| Raw bracket | Snapped | Reason |
|---|---|---|
| `[0, 2]` | `[0, 2]` | already on the grid |
| `[10.5, 12.5]` | `[10, 12]` | floats → snap down |
| `[1, 3]` | `[2, 4]` | odd anchor → snap up |
| `[10, 13]` | `[10, 12]` | width = 3 → corrected to 2 |
| `[-4.1, -2.1]` | `[-4, -2]` | floats across zero |

Both `manual_score` and the fluent post-processor use the snapped
form, so the human-readable text and the scored intervals stay
consistent. Each per-eval JSON record carries a
`manual_score.format_compliance` block:

```
format_compliance:
    n_intervals_total      total [x, y] brackets extracted
    n_snapped_to_2c_grid   how many needed snapping
    compliance_ratio       1 - snapped/total   (1.0 = fully compliant)
```

A `snapped=N/M` note also appears next to the accuracy line in the
runner's console output when `N > 0`, so format violations are
visible during the run. Per-record `interval_raw` is kept alongside
the snapped `interval` for after-the-fact auditing of which models
need the strictest prompt enforcement.

### Top-3 paragraph comparison figure

For each model the plotter renders two large composite PNGs ranking
the model's three best evaluations: one **by manual_accuracy**, one
**by judge_accuracy**. Each composite is a 3×4 grid:

```
GT paragraph text   |   GT zone -> [a, b] table   |   PRED paragraph (filtered)   |   PRED zone -> [a, b] table
```

per row, with a header per cell stating scenario / fold_n / mode /
target_month plus both accuracy scores. The zone tables are
re-extracted at plot time via the same parser `manual_score` uses
(zone vocabulary lookup + interval pairing), so the side tables show
exactly what the scorer was actually consuming, not what the prose
*looked* like it said.

The extractor handles both formats out of the box:

- **Prediction side** — `[a, b]` brackets (the model's compliant
  format).
- **GT side** — fluent Romanian (`"între 4 și 6 °C"`, `"peste 6 °C"`,
  `"sub 0 °C"`); `peste A` → `[A, A+2]`, `sub A` → `[A-2, A]`,
  `intre A si B` → `[A, B]`, all snapped to the 2 °C grid afterwards.
  This is what makes the GT column populate at all — without fluent
  recognition the GT table would be empty.

Use this figure to read at a glance: which scenario/fold/mode each
model excels in, how close its fluent prose actually gets to ANM
style, whether the zone coverage matches (same set of regions /
climatic zones / cardinal subdivisions present in both columns),
and where the manual and judge rankings disagree (a row appearing
in only one of the two PNGs means the two scorers picked different
bests for that model).

### Fluent post-processing — quantifier-aware, paragraph-aware

Manual scoring consumes the raw brackets; humans (and the judge
in some debug workflows) read the **fluent** paragraph. The
rewriter turns `[a, b]` and the optional Romanian quantifier word
in front of it into grammatical prose, snapping the bracket onto
the 2 °C grid in the same pass. Quantifier handling is paragraph-
aware so a directional word only collapses to a single value when
the bracket actually sits at the corresponding extreme of the
paragraph:

| Quantifier | Collapses to | Only if |
|---|---|---|
| `sub` / `de la` | `sub a` / `de la a` | the bracket has the LOWEST `a` of any bracket in the paragraph |
| `peste` / `până la` | `peste b` / `până la b` | the bracket has the HIGHEST `b` of any bracket in the paragraph |
| `intre` (default) | `intre a si b` | always |
| anything else at a non-extreme bracket | `intre a si b` | quantifier word is silently DROPPED |

Examples (the last one shows the drop behaviour — `sub` on the
upper bin and `peste` on the lower bin are physically nonsensical,
so both quantifiers vanish):

```
IN:  pe crestele montane inregistrandu-se valori sub [0, 2] °C
OUT: pe crestele montane inregistrandu-se valori sub 0 °C

IN:  In Muntenia mediile au fost intre [10, 12] °C, iar pe creste sub [-8, -6] °C
OUT: In Muntenia mediile au fost intre 10 si 12 °C, iar pe creste sub -8 °C

IN:  Pe litoral peste [16, 18] °C, in Maramures sub [4, 6] °C, in Muntenia intre [12, 14] °C
OUT: Pe litoral peste 18 °C, in Maramures sub 4 °C, in Muntenia intre 12 si 14 °C

IN:  sub [10, 12] si peste [4, 6]
OUT: intre 10 si 12 °C si intre 4 si 6 °C
```

Diacritic variants (`pana` / `pâna` / `pană` / `până`, `intre` /
`între` / `într?e`) and unit forms (`°C`, `oC`, `degC`, `C`) are
all accepted on the input side.

**Re-running fluent processing on already-finished runs** is what
the `postprocess` CLI subcommand is for — no LLM inference is
re-issued. The rewriter is fast (pure regex over a few thousand
records); iterating on its rules takes a fraction of a second over
a complete `llm_runs/` directory.

```
python -m prompting.utils.llm_comparison postprocess [--llm_runs_dir llm_runs] [--backup]
```

`--backup` writes a `.json.bak` copy of every file before
overwriting, so a problematic rewriter change can be rolled back
without losing the raw LLM outputs. Without it, rewriter changes
are applied in place.

The post-processor consumes the brackets in two passes:

1. **Parse** each `[a, b]` (rounding to integers; tolerating `oC`,
   `degC`, `°C`, `C` as units) into the structured `pred_records`
   list that the manual scorer consumes.
2. **Rewrite** each `[a, b]` into fluent Romanian (`intre a si b
   degC`), including the case where the bracket is already preceded
   by `intre`/`între`, so the duplicate word isn't introduced. Both
   the raw and the rewritten paragraph are persisted side-by-side
   in the JSON (`predicted_paragraph_raw` and
   `predicted_paragraph_fluent`).

### Manual scoring — the hyperbolic per-station distance

The closed-form scorer (`manual_score` in `llm_comparison.py`) takes
the predicted paragraph + the GT paragraph and produces an accuracy in
`[0, 1]`. It looks up the **monthly mean** `T(s)` per station for the
target month (from `temperature_YYYY-MM.json`) and computes:

```
For each station s in (GT_stations ∪ predicted_stations):
    let interval = [a, b] if s is predicted, else (None)
    if s in GT and s in predicted:
        d(s) = max(0, a - T(s), T(s) - b)                     intersection
    elif s in GT and s NOT in predicted:
        d(s) = w                                              missed
    else:  # predicted, not in GT
        d(s) = max(point-to-interval distance, w)             false positive

d_bar    = mean over s of d(s)
accuracy = 1 / (1 + d_bar / w)             hyperbolic; w = 2 degC
error    = 1 - accuracy
```

Hyperbolic normalisation maps `d_bar = 0` → accuracy `1.00`, `d_bar =
w` → `0.50`, `d_bar = 2w` → `0.33`. The penalty `w` for missed
stations matches the bin width, so a model that doesn't mention any
zone scores the same as one that names every wrong bin by 2 °C.
Stations with no usable `T(s)` are counted under `unscorable` but do
not enter `d_bar`.

The per-evaluation JSON record carries:

```
manual_score:
    accuracy        float
    d_bar           float in degC
    w               2.0
    counts          { intersection, missed, false_pos, unscorable }
```

The full per-station table and the parsed prediction records are kept
on the in-memory dict but stripped from the persisted JSON to keep
file sizes tractable across the 35-evaluation matrix.

### LLM-as-judge — OpenAI gpt-5-mini by default

A second, qualitative score comes from a separate language-model
judge. The judge follows a 4-step procedure laid out in its system
prompt: extract zones + intervals from each paragraph as **two
lists of `[zone, [a, b]]` pairs** (one per paragraph), write a
one-sentence motivation explaining the differences between the two
lists, then emit a single integer accuracy score on the last line
wrapped in `[N]`. The bracketed format makes the aggregate score
unambiguous to extract — `parse_judge_score` picks the last
single-integer bracket in the reply, ignoring the many `[a, b]`
temperature ranges the lists contain. The judge sees **the raw
output with brackets intact** (not the fluent rewrite), GT
paragraph, and nothing else — no scenario, mode, or fold metadata,
so it's a blind pairwise comparison.

```
JUDGE SYSTEM PROMPT (4 steps):
  1. Extract REFERINTA -> list of [zona, [a, b]] pairs.
  2. Extract PREDICTIE -> a second list of [zona, [a, b]] pairs.
  3. One-sentence motivation: differences between the two lists
     (missing/extra zones, distance between intervals).
  4. Print the chosen accuracy score on the last line as [N].

JUDGE USER PROMPT:
    REFERINTA:
    <full ANM paragraph for the target month>

    PREDICTIE:
    <raw model output with [x, y] brackets>

    Raspunde urmand procedura din 4 pasi.
    Ultima linie a raspunsului tau trebuie sa fie [N],
    unde N este scorul de acuratete.
```

Default backend: **OpenAI Responses API, `gpt-5-mini`, `reasoning.effort=
"minimal"`, `max_output_tokens=2048`**. The 2K output cap
comfortably accommodates the two lists + the one-sentence motivation
+ the final `[N]` for typical 25–30-zone paragraphs. The key is read
from `OPENAI_API_KEY` only — there is no fallback file, no config
key, no hardcoded literal.

```
setx OPENAI_API_KEY "sk-..."     # one-time, persisted; reopen terminal after
```

CLI flags:

| Flag | Default | Meaning |
|---|---|---|
| `--judge_provider` | `openai` | `openai` or `ollama`. `ollama` routes the judge through a local model so the run is offline (no API calls) |
| `--judge_model` | `gpt-5-mini` (OpenAI) / `--model` (Ollama) | Override the judge model id |

The OpenAI judge runs in parallel with the Ollama predictor (different
backends, no VRAM contention). The Ollama judge shares the loaded
weights with the predictor when `--judge_model == --model`; otherwise
expect VRAM thrashing unless `$env:OLLAMA_MAX_LOADED_MODELS = "2"` is
set and you have headroom for both models in GPU.

### Token-limit detection

Every chat call populates a `.last_meta` dict on the client with the
provider's stop-reason and token usage. After each `(predictor, judge)`
pair the runner derives a `truncation_flags` block that is persisted
in the per-evaluation JSON and, **only when something tripped**,
appended as one human-readable line in
`llm_runs/logs/token_limits_<model>.log`.

What's caught:

| Condition | Detected via | Meaning |
|---|---|---|
| **Output truncated** | Ollama `done_reason == "length"`; OpenAI `incomplete_details.reason == "max_output_tokens"` | The model hit its output cap before finishing. The reply is potentially incomplete |
| **Input near limit** | Ollama `prompt_eval_count / num_ctx >= 0.95` | Ollama silently drops the front of the messages array when the prompt exceeds `num_ctx`. A fill ratio near 1.0 means content may already be missing from what the model sees. OpenAI raises explicitly, so the error path catches that side |

Healthy runs do not even create the `logs/` directory. The threshold
`_NEAR_LIMIT_FRACTION = 0.95` lives at the top of the runner section
in [llm_comparison.py](prompting/utils/llm_comparison.py); easy to tune.

Inspect a specific row's flags from the per-model JSON:

```
python -c "import json; d = json.load(open('llm_runs/llm_runs_gpt-oss_latest.json', encoding='utf-8')); r = next(x for x in d['results'] if x['scenario']=='monthly' and x['fold_n']==6 and x['mode']=='historic_only'); print(r['truncation_flags'])"
```

### Bridging the baselines into the LLM JSON shape

`baseline_eval` reuses the existing AR rollout machinery to evaluate
the W=H=6 baseline checkpoints against the **same daily-scenario
folds** as the LLMs. The bridge:

1. For each `K ∈ {6, 12, 18, 24}` known-day point on November 2024
   (the default `--daily_test_month`):
   - Locate the input window as the **last W = 6** of the K known
     days (so K=6 uses Nov 1–6, K=12 uses Nov 7–12, …, K=24 uses
     Nov 19–24).
   - Run an autoregressive rollout to fill `30 − K` predicted days.
   - Splice known days (from `daily_county_mean.csv`) + predicted
     days → a `(30, 41)` full-month per-county DataFrame.
2. For each zone in the LLM's known-month zone set (i.e. zones
   deduped from January through October ANM paragraphs):
   - Compute the predicted **monthly mean** across the zone's
     counties × all 30 days.
   - Snap to a 2 °C bin `[2·floor(mean/2), 2·floor(mean/2) + 2]`.
3. Concatenate one sentence per zone into a synthetic paragraph in
   the same format the LLMs are asked to emit:
   `"In <zone_label>, mediile lunare au fost cuprinse intre [a, b] °C."`
4. Score the synthetic paragraph with `manual_score` (and optionally
   `llm_judge_score`) against the November GT paragraph.
5. Write `llm_runs/llm_runs_baseline_<baseline>_<label>.json` with
   the same record schema as `run`. The plotter picks it up
   automatically — no flags, no extra command.

The retrain-label → LLM-mode map:

```
--label wh6_target  ->  mode = "temp_only"
--label wh6_aux     ->  mode = "historic_plus_aux"
```

so baseline rows overlay LLM rows of the matching input regime in
the same colour on the comparison curves.

**Perfect-knowledge bound:** running the bridge with the GT daily
matrix in place of any model's prediction (i.e. an oracle baseline)
scores manual accuracy ≈ **0.648** on November 2024 (d̄ ≈ 1.09 °C,
168 intersections, 0 misses / false positives across the
30-zone November set). That 0.648 is the ceiling — accuracy is
bounded under 1.00 because the 2 °C floor anchoring discards
sub-2 °C precision. Real baselines and LLMs sit below this line.
(The April 2024 equivalent is ≈ 0.56 with d̄ ≈ 1.57 °C — the bound
shifts with the seasonal temperature spread.)

### CLI reference — `run`

Runs the test matrix for ONE Ollama LLM, persisting after every
evaluation so a crash loses at most one prediction.

| Flag | Default | Purpose |
|---|---|---|
| `--model` | required | Ollama model id, e.g. `gpt-oss:latest`, `llama3.1:70b-instruct-q4_K_S`, `llama3.1:8b-instruct-q4_K_M`, `gemma3:27b-it-q4_K_M` |
| `--judge_provider` | `openai` | `openai` (default, uses `OPENAI_API_KEY`) or `ollama` for offline runs |
| `--judge_model` | provider-default | `gpt-5-mini` for OpenAI; `--model` for Ollama |
| `--dry_run` | off | Use a mock client that returns canned Romanian paragraphs — no HTTP, no GPU. Verifies orchestration end-to-end |
| `--ollama_base_url` | `http://localhost:11434` | |
| `--num_ctx` | 36864 | Ollama context window. The largest user prompt the runner produces is the `*_with_prior` daily mode at K=24 with 3 prior years of November paragraphs + 10 in-year prior months + 24 days of per-zone data ≈ ~30K tokens; 36864 leaves headroom for the model's output |
| `--n_prior_years` | 3 | How many years before `--year` contribute target-month ANM paragraphs to the three `*_with_prior` modes. Counting down: with `--year 2024 --n_prior_years 3`, paragraphs from 2023/2022/2021 are loaded. Missing files silently skipped. 0 disables the prior-year modes entirely |
| `--temperature` | 0.2 | Low so the `[x, y]` format constraint is consistently honoured |
| `--keep_alive` | `30m` | Keeps the model loaded in GPU between calls |
| `--date_folder` | `date` | Holds `stations_metadata.json`, `temperature_*.json`, `daily_county_*.csv`, `historic_data_*.json` |
| `--historic_data_filename` | `historic_data_2024.json` | |
| `--year` | 2024 | |
| `--daily_test_month` | 11 (November) | Month used for the daily scenario; consistent across folds. November gives the longest in-year context (Jan..Oct as prior months) |
| `--output_dir` | `llm_runs` | Per-model JSON + token-limit log directory |
| `--modes` | all eight | Subset to run; useful for debugging. With `--n_prior_years 0`, the three `*_with_prior` modes are auto-filtered |
| `--n_prior_years` | 3 | Years before `--year` whose target-month paragraphs feed the `*_with_prior` modes. Counting down: 2024 → 2023/2022/2021. Missing files silently skipped. 0 disables the prior-year modes |

### CLI reference — `baseline_eval`

| Flag | Default | Purpose |
|---|---|---|
| `--baselines_dir` | `baselines` | Holds `checkpoints/` from the W=H=6 retrain |
| `--output_dir` | `llm_runs` | Where baseline JSONs land (same dir as LLM JSONs so `plot` picks them up) |
| `--fold` | 4 | Which fold's checkpoint to use (deployable) |
| `--year` | 2024 | |
| `--daily_test_month` | 11 (November) | Must match the LLM run's value |
| `--date_folder` | `date` | |
| `--historic_data_filename` | `historic_data_2024.json` | |
| `--use_openai_judge` | off | Also score with gpt-5-mini, mirroring the LLM eval. Manual scoring alone is usually enough for the comparison plot |
| `--judge_model` | `gpt-5-mini` | OpenAI judge model id when `--use_openai_judge` is set |
| `--device` | auto | `auto`/`cpu`/`cuda` for the AR rollout |

### CLI reference — `plot`

| Flag | Default | Purpose |
|---|---|---|
| `--llm_runs_dir` | `llm_runs` | Folder scanned for `llm_runs_*.json` (LLMs and baselines together) |
| `--output_dir` | `<llm_runs_dir>/plots` | CSV + PNGs land here |
| `--show` | off | Also call `plt.show()` after writing files |

### End-to-end command set

```cmd
set PY=C:\Users\sateliti1\AppData\Local\anaconda3\envs\meteollm\python.exe
cd /d F:\Claudiu\metframe

REM 1. One-time data prep (skip if stations_metadata.json + temperature_*.json + daily_county_*.csv already exist)
%PY% -m prompting.utils.check_data_availability combine_stations_metadata
for %m in (01 02 04 05 06 07 08 09 10 11 12) do %PY% -m prompting.utils.check_data_availability temperature --month 2024-%m

REM 2. Retrain the baselines with W=H=6 so a single forward chunk = one LLM daily fold
%PY% -m prompting.utils.baselines --baseline all --window 6 --horizon 6 --folds 4 ^
    --patch_len 2 --stride 2 --save_weights --label wh6_target
%PY% -m prompting.utils.baselines --baseline all --window 6 --horizon 6 --folds 4 ^
    --patch_len 2 --stride 2 --save_weights --label wh6_aux ^
    --extra_csvs daily_county_precip.csv daily_county_wind.csv daily_county_nebulosity.csv

REM 3. Bridge the baseline checkpoints into the LLM JSON schema
%PY% -m prompting.utils.llm_comparison baseline_eval --fold 4

REM 4. Run each Ollama LLM (default judge = OpenAI gpt-5-mini, key from OPENAI_API_KEY)
%PY% -m prompting.utils.llm_comparison run --model gpt-oss:latest
%PY% -m prompting.utils.llm_comparison run --model llama3.1:8b-instruct-q4_K_M
%PY% -m prompting.utils.llm_comparison run --model llama3.1:70b-instruct-q4_K_S
%PY% -m prompting.utils.llm_comparison run --model gemma3:27b-it-q4_K_M

REM 5. Unified comparison plot (baselines + LLMs overlaid)
%PY% -m prompting.utils.llm_comparison plot
```

### Outputs

After the full pipeline:

```
llm_runs/
├── llm_runs_gpt-oss_latest.json                       <- one per Ollama model
├── llm_runs_llama3.1_8b-instruct-q4_K_M.json
├── llm_runs_llama3.1_70b-instruct-q4_K_S.json
├── llm_runs_gemma3_27b-it-q4_K_M.json
│
├── llm_runs_baseline_linear_regression_wh6_target.json   <- one per baseline x label
├── llm_runs_baseline_linear_regression_wh6_aux.json
├── llm_runs_baseline_nbeats_wh6_target.json
├── ... (8 baseline JSONs total: 4 trained x 2 labels)
│
├── logs/
│   └── token_limits_<model>.log                       <- only if anything tripped
│
└── plots/
    ├── summary.csv                                    <- one row per (model, scenario, fold, mode)
    ├── llm_manual_accuracy_monthly.png                <- LLMs only (baselines have no monthly scenario)
    ├── llm_manual_accuracy_daily.png                  <- LLMs + baselines overlaid, colour by mode
    ├── llm_judge_accuracy_monthly.png
    ├── llm_judge_accuracy_daily.png
    ├── manual_vs_judge_<model>.png                    <- one per model, y=x ref + Spearman corr
    ├── top3_comparison_<model>_by_manual_accuracy.png <- top-3 evals by manual score, side by side
    └── top3_comparison_<model>_by_judge_accuracy.png  <- top-3 evals by judge score, side by side
```

Each per-evaluation record in the JSON contains:

```
scenario               "monthly" or "daily"
fold_n                 K (months for monthly, days for daily)
mode                   one of the five input modes
target_month           1..12
year                   2024
n_zones, zones         the input zone set the model was asked to cover
gt_paragraph           verbatim ANM paragraph for the target month
predicted_paragraph_raw    model output with [x, y] intact
predicted_paragraph_fluent post-processed Romanian
manual_score           { accuracy, d_bar, w, counts }
judge_score            { judge_accuracy, judge_score_int, judge_raw_reply }
truncation_flags       { predictor: {...}, judge: {...} } - see "Token-limit detection"
input_prompt_chars     len(system) + len(user)
output_chars           len(predicted_paragraph_raw)
```

Inspecting a specific row interactively:

```
python -c "import json; d = json.load(open('llm_runs/llm_runs_gpt-oss_latest.json', encoding='utf-8')); r = next(x for x in d['results'] if x['scenario']=='monthly' and x['fold_n']==6 and x['mode']=='historic_only'); import pprint; pprint.pp(r)"
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
from both PDF forecasts and CSV station data, and runs inference against
every model in `models_to_test.txt`. When `fine_tuned_llm/model/final_model/`
exists on disk, the QLoRA adapter is **automatically loaded after the
Ollama sweep** and run against the exact same prompts; its responses
land in the same `responses/{date}/` folder under the model label
`Llama-3.1-8B-Instruct-qlora`, so statistical and judge analyses pick
it up with no extra flags or merge steps.

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

Scope note: this pipeline handles **training** and the **zero-shot
generalization test**. The few-shot test against Ollama-format prompts
is no longer produced here — it runs automatically inside
`--test_models` whenever the adapter exists on disk (see scenario 3).
The zero-shot track writes statistical metrics to
`fine_tuned_llm/results/zero-shot/{date}/{N}_past_days/` and judge
metrics under the same folder's `judge/analysis/` subtree.

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
| `--num_ctx` | int | 16384 | Ollama inference, fine-tuning test phase (HF tokenizer truncation) |
| `--num_predict` | int | 512 | Ollama inference, fine-tuning test phase (max output tokens) |
| `--batch_size` | int | 2 | Fine-tuning training phase (per-device batch). On a 48GB A6000 with `--max_seq_length 16384`, sizes above 2 OOM. |
| `--max_seq_length` | int | 16384 | Fine-tuning training phase (tokenizer truncation length). Must be >= the longest tokenized training example, otherwise the response tail is dropped and the data collator masks the label sequence. |

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

### 10. Training-side silent max_length truncation

Symmetric to bug 1 but on the training path. `config.py` documented
`max_length=16384` in `MODEL_CONFIG`, but `MeteorologyFineTuner` never
read that key — the constructor defaulted to `max_length=4096` and
`finetune_integration.py` called it without an override. Training
examples that exceed 4096 tokens (p99 ≈ 11K, max ≈ 11.6K on the 2024
dataset at past_days=4) were truncated, dropping the response tail.
`DataCollatorForCompletionOnlyLM` then failed to find the response
template in the truncated sequence and masked every label to -100,
producing "This instance will be ignored in loss calculation"
warnings and near-zero gradient signal per affected step.

**Fix:** new `--max_seq_length` CLI flag (default 16384) wired through
`finetune_integration.run_finetuning_pipeline` and
`run_comparison_pipeline` to `MeteorologyFineTuner(max_length=...)`.
The dead `MODEL_CONFIG["max_length"]` entry was removed.

### 11. Training-side CLI batch_size default OOM'd on documented hardware

`config.py` documented `_DEFAULT_BATCH_SIZE = 2` (tuned for the 48GB
A6000), but the CLI default in `main.py` was `--batch_size 24` and
`finetune_integration.py` passed the CLI value straight through to
`TrainingArguments`, overriding the config. None of the documented
`--finetune` commands passed an explicit `--batch_size`, so every
run on the documented hardware hit CUDA OOM at the first step at
`max_seq_length=16384`.

**Fix:** CLI default lowered to `--batch_size 2`. Dead
`TRAINING_CONFIG["per_device_train_batch_size"]` and
`_DEFAULT_BATCH_SIZE` entries were removed from `config.py`; the CLI
flag is now the single source of truth.


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
estimation for all Ollama models, the base `llama3.1:8b` reference, and
the fine-tuned QLoRA adapter, plus a three-way comparison plot set.

Use `cmd.exe` (not Git Bash) so `setx`-persisted env vars are visible.
Set a short Python alias once per session:

```cmd
cd /d F:\Claudiu\metframe
set PY=C:\Users\sateliti1\AppData\Local\anaconda3\envs\meteollm\python.exe
```

### Block A: Data preparation (one-time)

```cmd
REM Step 1 - PDF to diagnoses (skip if formatted_diagnoses_2024/formatted_diagnoses_2024.json already exists).
REM This is the long step (~12h, calls gpt-5-mini per date).
%PY% -u main.py --generate_training_dataset_for_year 2024 --judge gpt-5-mini

REM Step 2 - produce train_data.json / test_data.json / test_data_zero_shot.json
%PY% -u dataset_creation.py --mode all --year 2024 --past_days 4

REM Verify the six held-out test dates are present in test_data.json.
REM These are the 30th of Jan/Mar/May/Jul/Sep/Nov per config.get_testing_dates() —
REM the dates the QLoRA model is evaluated on. File is UTF-8; encoding must
REM be passed explicitly under Windows default cp1252.
%PY% -c "import json; d=json.load(open('test_data.json', encoding='utf-8')); dates=sorted({x['date'] for x in d}); print('dates:', dates)"
```

Reminder: the calendar split in [config.py](prompting/utils/config.py)
uses days 1-25 of every month for training and the 30th of
Jan/Mar/May/Jul/Sep/Nov for held-out testing. Any date whose day number
falls in 1-25 (e.g. July 10) is in the training set; evaluating the
fine-tuned model on such a date measures memorization, not
generalization, so the unified evaluation below runs only on the six
held-out test dates.

### Block B: Train the QLoRA adapter

```cmd
ollama serve

%PY% -u main.py --finetune --year 2024 --past_days 4 --skip_testing --training_seed 42
```

Output: `fine_tuned_llm/model/final_model/` (adapter weights). Once
this folder exists, every subsequent `--test_models` run will
automatically include the fine-tuned model alongside the Ollama ones.

### Block C: Unified few-shot evaluation on the six held-out dates

Runs the Ollama models + the QLoRA adapter (auto-included by
`--test_models` now that the adapter exists on disk) on each of the
six held-out config dates, using the matching prompts in
`prompts/{date}/`. `cmd.exe`'s `for %d in (...)` syntax iterates the
dates per phase so the model download happens once and each phase
finishes across all dates before the next begins.

```cmd
REM One-time: download every model in models_to_test.txt. Idempotent —
REM already-pulled models are skipped.
%PY% -u main.py --get_test_time_interval 2024-01-30 2024-01-30 --past_days 4 --download_models

REM Phase 1: generate prompts for every test date.
for %d in (2024-01-30 2024-03-30 2024-05-30 2024-07-30 2024-09-30 2024-11-30) do %PY% -u main.py --get_test_time_interval %d %d --past_days 4 --generate_prompts_gpt

REM Phase 2: run inference. Every Ollama model + the QLoRA adapter, all seeds, all past_days.
for %d in (2024-01-30 2024-03-30 2024-05-30 2024-07-30 2024-09-30 2024-11-30) do %PY% -u main.py --get_test_time_interval %d %d --past_days 4 --test_models --n_seeds 3 --num_ctx 16384 --num_predict 1024

REM Phase 3: statistical analysis.
for %d in (2024-01-30 2024-03-30 2024-05-30 2024-07-30 2024-09-30 2024-11-30) do %PY% -u main.py --get_test_time_interval %d %d --past_days 4 --statistical_analysis

REM Phase 4: LLM-as-a-judge analysis with 3 judge runs per response for variance.
for %d in (2024-01-30 2024-03-30 2024-05-30 2024-07-30 2024-09-30 2024-11-30) do %PY% -u main.py --get_test_time_interval %d %d --past_days 4 --judge_analysis --n_judge_runs_per_response 3
```

Output (per date): `responses/{date}/`, `results/{date}/`,
`llm_as_a_judge/gpt-5-mini/{date}/` — all containing both Ollama models
(with the Q4_K_M base `llama3.1:8b-instruct-q4_K_M` acting as the
untrained reference) and the fine-tuned row
`Llama-3.1-8B-Instruct-qlora`.

Rough compute envelope: ~9 Ollama models × 4 past_days × 3 seeds × 30 s
per response + the QLoRA sweep + the judge calls ≈ 2-3 hours per date
on an RTX A6000. The full six-date sweep therefore runs overnight.

### Block D: Zero-shot fine-tuned evaluation (for the comparison plot)

The zero-shot track runs on all six held-out config dates and now
sweeps past_days 1..4 internally (one inference per (date, past_days,
seed) cell). Responses, statistical metrics, and judge metrics all
land under `fine_tuned_llm/results/zero-shot/`.

```cmd
%PY% -u main.py --finetune --year 2024 --past_days 4 --skip_training --zero_shot --n_seeds 3 --num_ctx 16384 --num_predict 1024
```

### Block E: Plots

```cmd
%PY% -u generate_metric_plots.py
%PY% -u generate_plots_llm_as_a_judge.py
%PY% -u generate_comparison_plots.py
```

Output:
- `plots/` and `plots_llm_as_a_judge/` — all 10 rows per date (9 Ollama + QLoRA) with variance error bars across every metric.
- `plots_comparison/` — three-series focused comparison (fine-tuned few-shot vs fine-tuned zero-shot vs base `llama3.1:8b` Q4_K_M) for both statistical metrics and the judge score. Includes a Q4_K_M vs NF4+bf16 quantization footnote on each figure.

### Date coverage notes

| Track | Dates available | Gating file |
|---|---|---|
| Ollama few-shot | Any date with CSV data, past_days sweep 1..N | `prompts/{date}/` (generated on demand) |
| Fine-tuned few-shot (unified) | Same as Ollama — wherever `--test_models` runs | `fine_tuned_llm/model/final_model/` must exist |
| Fine-tuned zero-shot | Six dates in `config.get_testing_dates()`, past_days sweep 1..N | `test_data_zero_shot.json` (now contains one entry per (date, past_days) pair) |

The fine-tuned few-shot track is no longer restricted to `config` dates
because it now reads prompts from `prompts/{date}/`, the same source as
the Ollama models. Only the zero-shot track remains bound to the
`test_data_zero_shot.json` date set, but within those dates it now
sweeps the full past_days axis 1..N (one entry per (date, past_days)
pair), so its line on the comparison plot spans the same x-range as
the few-shot curves instead of being a single point. On dates outside
the zero-shot set the third series is simply absent from the plot.

Caveat about the sweep interpretation: increasing past_days in the
zero-shot track does not turn it into few-shot. The prompt body grows
with more raw numerical history (weather readings for additional past
days) but still contains zero worked examples of the diagnosis task —
no reference diagnoses, no reasoning chains. What the sweep measures is
whether the model can leverage longer numerical trends when making
comparative statements, independent of in-context exemplars.

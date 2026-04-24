# #################################################################
# ####################### llm_as_a_judge.py #######################
# #################################################################





# import os
# import json
# import pandas as pd
# import re
# from glob import glob
# from typing import Optional, List, Tuple
# import numpy as np
# from openai import OpenAI
# import time

# from prompting.utils.postprocessing_romanian_gpt import extract_response_text, parse_filename

# def create_judge_analysis(responses_folder: str, reference_text: str, n_past_days: int,
#                          judge_model: str = "gpt-5-mini", api_key: str = None):
#     """
#     Creates analysis tables using LLM-as-a-Judge approach to evaluate responses.
#     Processes all past_days configurations (1 through n_past_days) and stores results in the same folder.
    
#     Args:
#         responses_folder: Base path to responses folder (e.g., "responses\\2024-03-16\\4_past_days") 
#         reference_text: Reference text (ground truth)
#         n_past_days: Number of past days for output folder structure
#         judge_model: Name of the judge model
#         api_key: OpenAI API key
#     """
    
#     # Initialize OpenAI client
#     if api_key:
#         client = OpenAI(api_key=api_key)
#     else:
#         client = OpenAI()  # Uses OPENAI_API_KEY environment variable
    
#     # Load system prompt
#     system_prompt_path = os.path.join("llm_as_a_judge", "gpt-5-system-prompt.txt")
#     try:
#         with open(system_prompt_path, 'r', encoding='utf-8') as f:
#             system_prompt = f.read().strip()
#     except FileNotFoundError:
#         print(f"System prompt file not found: {system_prompt_path}")
#         return
    
#     # Extract base path and date from responses_folder
#     # responses_folder format: "responses\\2024-03-16\\4_past_days"
#     parts = responses_folder.split(os.sep)
#     if len(parts) >= 2:
#         date = parts[-2]  # Get date from path
#         base_responses_path = os.sep.join(parts[:-1])  # Get base path without past_days folder
#     else:
#         print(f"Invalid responses_folder format: {responses_folder}")
#         return
    
#     print(f"Processing all configurations for date: {date}")
#     print(f"Base responses path: {base_responses_path}")
#     print(f"Target past_days: {n_past_days}")
    
#     # Collect all JSON files from all past_days configurations
#     all_json_files = []
    
#     for current_past_days in range(1, n_past_days + 1):
#         current_folder = os.path.join(base_responses_path, f"{current_past_days}_past_days")
        
#         if os.path.exists(current_folder):
#             json_files = glob(os.path.join(current_folder, "*.json"))
#             json_files = [f for f in json_files if not os.path.basename(f).startswith("test_summary")]
            
#             print(f"Found {len(json_files)} files in {current_past_days}_past_days folder")
#             all_json_files.extend(json_files)
#         else:
#             print(f"Folder not found: {current_folder}")
    
#     if not all_json_files:
#         print(f"No valid JSON files found in any past_days configurations")
#         return
    
#     print(f"Total files to process: {len(all_json_files)}")
    
#     # Create main output directory
#     judge_output_dir = os.path.join("llm_as_a_judge", judge_model, date, f"{n_past_days}_past_days")
#     os.makedirs(judge_output_dir, exist_ok=True)
    
#     # Store all data
#     all_data = []
    
#     def call_judge_api(reference: str, response: str, judge_model: str) -> str:
#         """Call OpenAI API for judgment."""
#         user_prompt = f"REFERINTA\n{reference}\n\nRASPUNS\n{response}"
        
#         try:
#             response = client.responses.create(
#                 model=judge_model,
#                 reasoning={"effort": "minimal"},
#                 instructions=system_prompt,
#                 input=user_prompt,
#                 max_output_tokens=10000
#             )
#             return response.output_text
#         except Exception as e:
#             print(f"API call failed: {e}")
#             return f"Error: {str(e)}"
    
#     def extract_correlation_scores(judge_response: str) -> Tuple[Optional[List[float]], Optional[float]]:
#         """
#         Extract correlation scores from judge response looking for [x, x, x, x, x] or [x, x, x, x] pattern.
#         Returns: (correlation_array, average_score)
#         """
#         # Look for pattern [x.xx, x.xx, x.xx, x.xx, x.xx] or [x.xx, x.xx, x.xx, x.xx]
#         # Pattern supports both integers and decimals
#         pattern = r'\[([0-9., ]+)\]'
#         matches = re.findall(pattern, judge_response)
        
#         if matches:
#             # Take the last match in case there are multiple
#             score_string = matches[-1]
            
#             try:
#                 # Split by comma and convert to floats
#                 scores = [float(x.strip()) for x in score_string.split(',')]
                
#                 # Validate that all scores are in [0, 1] range
#                 if all(0.0 <= score <= 1.0 for score in scores):
#                     # Check if we have 4 or 5 scores (expected according to system prompt)
#                     if len(scores) in [4, 5]:
#                         average_score = sum(scores) / len(scores)
#                         return scores, average_score
                    
#             except (ValueError, TypeError):
#                 pass
        
#         return None, None
    
#     for json_file in all_json_files:
#         try:
#             model_name, file_date, past_days = parse_filename(json_file)
            
#             with open(json_file, 'r', encoding='utf-8') as f:
#                 json_data = json.load(f)
            
#             response_text = extract_response_text(json_data)
            
#             print(f"Processing: {os.path.basename(json_file)} (from {past_days}_past_days)")
            
#             # Call judge API
#             judge_response = call_judge_api(reference_text, response_text, judge_model)
            
#             # Save individual judge response in the target folder
#             judge_filename = f"{model_name}_{file_date}_{past_days}_past_days.json"
#             judge_filepath = os.path.join(judge_output_dir, judge_filename)
            
#             judge_data = {
#                 "model_name": model_name,
#                 "date": file_date,
#                 "original_past_days": past_days,  # Original past_days from file
#                 "target_past_days": n_past_days,  # Target folder past_days
#                 "reference_text": reference_text,
#                 "response_text": response_text,
#                 "judge_model": judge_model,
#                 "judge_response": judge_response,
#                 "timestamp": time.time()
#             }
            
#             with open(judge_filepath, 'w', encoding='utf-8') as f:
#                 json.dump(judge_data, f, ensure_ascii=False, indent=2)
            
#             # Extract correlation scores
#             correlation_scores, average_score = extract_correlation_scores(judge_response)
            
#             # Store data for analysis
#             data_point = {
#                 'model': model_name,
#                 'date': file_date,
#                 'past_days': past_days,
#                 'filename': os.path.basename(json_file),
#                 'judge_response': judge_response,
#                 'correlation_scores': correlation_scores,
#                 'average_score': average_score,
#                 'score_extracted': correlation_scores is not None,
#                 'num_propositions': len(correlation_scores) if correlation_scores else None
#             }
            
#             # Add individual correlation scores as separate columns
#             if correlation_scores:
#                 for i, score in enumerate(correlation_scores):
#                     data_point[f'correlation_{i+1}'] = score
            
#             all_data.append(data_point)
            
#             print(f"  -> Correlation scores: {correlation_scores}")
#             print(f"  -> Average score: {average_score:.3f}" if average_score else "  -> No valid scores extracted")
            
#             # Add small delay to avoid rate limiting
#             time.sleep(0.5)
            
#         except Exception as e:
#             print(f"Error processing {json_file}: {e}")
#             continue
    
#     if not all_data:
#         print("No data was successfully processed")
#         return
    




# #######################################################################
# ####################### judge_analysis_table.py #######################
# #######################################################################





# import os
# import json
# import pandas as pd
# import re
# from glob import glob
# from typing import Optional, List, Tuple
# import numpy as np

# def generate_judge_analysis_tables(judge_output_dir: str):
#     """
#     Generate analysis tables from saved judge JSON files.
    
#     Args:
#         judge_output_dir: Path to directory containing judge JSON files 
#                          (e.g., "llm_as_a_judge/gpt-5-mini/2024-03-16/4_past_days")
#     """
    
#     # Get all JSON files (exclude analysis folder)
#     json_files = glob(os.path.join(judge_output_dir, "*.json"))
    
#     if not json_files:
#         print(f"No JSON files found in {judge_output_dir}")
#         return
    
#     print(f"Found {len(json_files)} judge JSON files to analyze")
    
#     def extract_correlation_scores_from_response(judge_response: str) -> Tuple[Optional[List[float]], Optional[float]]:
#         """Extract correlation scores from judge response."""
#         pattern = r'\[([0-9., ]+)\]'
#         matches = re.findall(pattern, judge_response)
        
#         if matches:
#             score_string = matches[-1]
#             try:
#                 scores = [float(x.strip()) for x in score_string.split(',')]
#                 if all(0.0 <= score <= 1.0 for score in scores) and len(scores) in [4, 5]:
#                     average_score = sum(scores) / len(scores)
#                     return scores, average_score
#             except (ValueError, TypeError):
#                 pass
#         return None, None
    
#     # Store all data
#     all_data = []
    
#     for json_file in json_files:
#         try:
#             with open(json_file, 'r', encoding='utf-8') as f:
#                 judge_data = json.load(f)
            
#             # Extract information from the saved judge data
#             model_name = judge_data.get('model_name', '')
#             date = judge_data.get('date', '')
#             past_days = judge_data.get('original_past_days', 1)
#             judge_response = judge_data.get('judge_response', '')
            
#             # Extract correlation scores
#             correlation_scores, average_score = extract_correlation_scores_from_response(judge_response)
            
#             # Store data for analysis
#             data_point = {
#                 'model': model_name,
#                 'date': date,
#                 'past_days': past_days,
#                 'filename': os.path.basename(json_file),
#                 'judge_response': judge_response,
#                 'correlation_scores': correlation_scores,
#                 'average_score': average_score,
#                 'score_extracted': correlation_scores is not None,
#                 'num_propositions': len(correlation_scores) if correlation_scores else None
#             }
            
#             # Add individual correlation scores as separate columns
#             if correlation_scores:
#                 for i, score in enumerate(correlation_scores):
#                     data_point[f'correlation_{i+1}'] = score
            
#             all_data.append(data_point)
            
#         except Exception as e:
#             print(f"Error processing {json_file}: {e}")
#             continue
    
#     if not all_data:
#         print("No data was successfully processed")
#         return
    
#     # Convert to DataFrame
#     df = pd.DataFrame(all_data)
    
#     # Filter out rows where correlation scores couldn't be extracted
#     df_valid_scores = df[df['score_extracted'] == True].copy()
    
#     if df_valid_scores.empty:
#         print("No valid correlation scores were extracted from judge responses")
#         return
    
#     print(f"Successfully extracted correlation scores from {len(df_valid_scores)}/{len(df)} responses")
    
#     # Create analysis directory
#     analysis_output_dir = os.path.join(judge_output_dir, "analysis")
#     os.makedirs(analysis_output_dir, exist_ok=True)
    
#     # Get correlation columns (individual numeric columns, not the list column)
#     correlation_columns = [col for col in df_valid_scores.columns if col.startswith('correlation_') and col != 'correlation_scores']
    
#     # Create pivot tables for average scores
#     if 'average_score' in df_valid_scores.columns:
#         try:
#             avg_scores_pivot = df_valid_scores.pivot_table(
#                 index='past_days',
#                 columns='model', 
#                 values='average_score',
#                 aggfunc='mean'
#             )
#             avg_scores_pivot.to_csv(os.path.join(analysis_output_dir, "average_scores_models_vs_past_days.csv"))
#             print("Created average_scores_models_vs_past_days.csv")
#         except Exception as e:
#             print(f"Error creating average scores pivot table: {e}")
    
#     # Create pivot tables for individual correlation scores
#     for corr_col in correlation_columns:
#         try:
#             # Ensure the column contains only numeric values
#             numeric_data = pd.to_numeric(df_valid_scores[corr_col], errors='coerce')
#             if not numeric_data.isna().all():
#                 # Create a temporary dataframe with the numeric column
#                 temp_df = df_valid_scores.copy()
#                 temp_df[corr_col] = numeric_data
                
#                 corr_pivot = temp_df.pivot_table(
#                     index='past_days',
#                     columns='model',
#                     values=corr_col,
#                     aggfunc='mean'
#                 )
#                 corr_pivot.to_csv(os.path.join(analysis_output_dir, f"{corr_col}_models_vs_past_days.csv"))
#                 print(f"Created {corr_col}_models_vs_past_days.csv")
#         except Exception as e:
#             print(f"Error creating pivot table for {corr_col}: {e}")
    
#     # Overall summary statistics
#     if 'average_score' in df_valid_scores.columns:
#         try:
#             score_stats = df_valid_scores['average_score'].describe()
#             score_stats.to_csv(os.path.join(analysis_output_dir, "overall_summary_statistics.csv"))
#             print("Created overall_summary_statistics.csv")
#         except Exception as e:
#             print(f"Error creating overall summary statistics: {e}")
    
#     # Summary by past_days - only include numeric columns
#     numeric_summary_columns = ['average_score'] + correlation_columns
#     existing_numeric_columns = []
    
#     for col in numeric_summary_columns:
#         if col in df_valid_scores.columns:
#             # Check if column is numeric or can be converted to numeric
#             try:
#                 numeric_data = pd.to_numeric(df_valid_scores[col], errors='coerce')
#                 if not numeric_data.isna().all():
#                     existing_numeric_columns.append(col)
#             except:
#                 pass
    
#     if existing_numeric_columns:
#         try:
#             # Create a clean dataframe with only numeric columns
#             clean_df = df_valid_scores[['past_days', 'model'] + existing_numeric_columns].copy()
            
#             # Ensure all summary columns are numeric
#             for col in existing_numeric_columns:
#                 clean_df[col] = pd.to_numeric(clean_df[col], errors='coerce')
            
#             past_days_summary = clean_df.groupby('past_days')[existing_numeric_columns].agg([
#                 'count', 'mean', 'std', 'min', 'max'
#             ]).round(4)
#             past_days_summary.to_csv(os.path.join(analysis_output_dir, "summary_by_past_days.csv"))
#             print("Created summary_by_past_days.csv")
#         except Exception as e:
#             print(f"Error creating past_days summary: {e}")
    
#     # Summary by model
#     if existing_numeric_columns:
#         try:
#             model_summary = clean_df.groupby('model')[existing_numeric_columns].agg([
#                 'count', 'mean', 'std', 'min', 'max'
#             ]).round(4)
#             model_summary.to_csv(os.path.join(analysis_output_dir, "summary_by_model.csv"))
#             print("Created summary_by_model.csv")
#         except Exception as e:
#             print(f"Error creating model summary: {e}")
    
#     # Summary by number of propositions
#     if 'num_propositions' in df_valid_scores.columns and existing_numeric_columns:
#         try:
#             clean_df_with_props = clean_df.copy()
#             clean_df_with_props['num_propositions'] = df_valid_scores['num_propositions']
            
#             prop_summary = clean_df_with_props.groupby('num_propositions')[existing_numeric_columns].agg([
#                 'count', 'mean', 'std'
#             ]).round(4)
#             prop_summary.to_csv(os.path.join(analysis_output_dir, "summary_by_propositions.csv"))
#             print("Created summary_by_propositions.csv")
#         except Exception as e:
#             print(f"Error creating propositions summary: {e}")
    
#     # Save raw data for reference
#     try:
#         df.to_csv(os.path.join(analysis_output_dir, "raw_judge_data.csv"), index=False)
#         df_valid_scores.to_csv(os.path.join(analysis_output_dir, "valid_scores_data.csv"), index=False)
#         print("Created raw_judge_data.csv and valid_scores_data.csv")
#     except Exception as e:
#         print(f"Error saving raw data: {e}")
    
#     # Print summary
#     print(f"\n=== JUDGE ANALYSIS SUMMARY ===")
#     print(f"Total responses processed: {len(df)}")
#     print(f"Valid correlation scores extracted: {len(df_valid_scores)}")
    
#     if 'average_score' in df_valid_scores.columns and not df_valid_scores['average_score'].isna().all():
#         print(f"Average score range: {df_valid_scores['average_score'].min():.3f} - {df_valid_scores['average_score'].max():.3f}")
#         print(f"Mean average score: {df_valid_scores['average_score'].mean():.3f}")
    
#     print(f"Models evaluated: {df_valid_scores['model'].nunique()}")
#     print(f"Past days configurations: {sorted(df_valid_scores['past_days'].unique())}")
    
#     if 'num_propositions' in df_valid_scores.columns:
#         unique_props = sorted(df_valid_scores['num_propositions'].dropna().unique())
#         if unique_props:
#             print(f"Proposition counts: {unique_props}")
    
#     print(f"\nResults saved in: {analysis_output_dir}")
    
#     # Show correlation score statistics
#     if correlation_columns:
#         print(f"\n=== CORRELATION SCORES SUMMARY ===")
#         for corr_col in correlation_columns:
#             if corr_col in df_valid_scores.columns:
#                 scores = pd.to_numeric(df_valid_scores[corr_col], errors='coerce').dropna()
#                 if len(scores) > 0:
#                     print(f"{corr_col}: mean={scores.mean():.3f}, std={scores.std():.3f}, min={scores.min():.3f}, max={scores.max():.3f}")
    
#     return df_valid_scores

"""
Judge-based evaluation for the meteorological diagnosis pipeline.

Implements a two-phase pipeline against the gpt-5-mini judge model:

  Phase 1 - SCORING (expensive, hits the OpenAI API):
    create_judge_analysis() walks every response JSON in a folder, calls
    the judge with a Romanian rubric, and saves one judge JSON per response
    to llm_as_a_judge/{judge_model}/{date}/{n_past_days}_past_days/.

  Phase 2 - AGGREGATION (cheap, pure pandas):
    generate_judge_analysis_tables() walks the saved judge JSONs, parses
    correlation scores via regex, and writes pivot tables and summaries
    into an analysis/ subdirectory.

Phase 1 automatically calls Phase 2 at the end, so a single
create_judge_analysis() invocation produces both the per-file JSONs and
the summary CSVs. Phase 2 is also exposed as a public function so existing
judge JSONs can be re-aggregated without re-judging.

Public API (signatures backward-compatible with the previous llm_as_a_judge.py
and judge_analysis_table.py modules; new optional kwargs are added with
None defaults so existing call sites work unchanged):

    create_judge_analysis              run scoring + aggregation
    generate_judge_analysis_tables     re-aggregate saved judge JSONs
"""

import json
import os
import re
import time
from glob import glob
from pathlib import Path, PurePath
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from openai import OpenAI

from prompting.utils.response_evaluation import (
    extract_response_text,
    parse_filename,
    parse_filename_with_seed,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default judge model. Match the report's evaluation setup unless you have
# a research reason to swap; changing this affects the comparability of all
# subsequent score tables.
_DEFAULT_JUDGE_MODEL = "gpt-5-mini"

# Reasoning effort and output cap for judge API calls. The rubric is short
# and the score format is a single bracketed list, so 'minimal' effort and
# a 10K token ceiling are comfortably above what the judge needs.
_JUDGE_REASONING_EFFORT = "minimal"
_JUDGE_MAX_OUTPUT_TOKENS = 10000

# Inter-call delay to avoid trivially tripping rate limits. Not a real
# backoff strategy; if you start hitting 429s in bulk, switch to proper
# exponential backoff with jitter.
_JUDGE_API_DELAY_SECONDS = 0.5

# Where the per-file judge JSONs and the analysis CSVs land. Outputs go to
# llm_as_a_judge/{judge_model}/{date}/{n_past_days}_past_days/.
_JUDGE_OUTPUT_BASE = Path("llm_as_a_judge")
_ANALYSIS_SUBDIR_NAME = "analysis"

# Bracketed-list pattern used to extract correlation scores from judge
# responses. Captures any sequence of digits, dots, commas, and spaces
# inside square brackets.
_BRACKETED_LIST_RE = re.compile(r"\[([0-9., ]+)\]")

# Acceptable lengths for the parsed score list. The rubric requires either
# 4 or 5 sentence scores depending on whether the optional repeated-phenomena
# sentence is present.
_VALID_SCORE_LIST_LENGTHS = (4, 5)

# Per-cell std threshold above which a (model, past_days) combination is
# flagged as high-variance. On the judge's 0-1 scale, a std of 0.05 means
# the judge's scores for that cell jitter by ~5 percentage points across
# replicates, which is large enough to make single-run comparisons unreliable.
_VARIANCE_OUTLIER_THRESHOLD = 0.05


# ---------------------------------------------------------------------------
# Default judge rubric
# ---------------------------------------------------------------------------

# Embedded verbatim from gpt-5-system-prompt.txt so the rubric is
# version-controlled alongside the code that uses it. Callers can still
# override with system_prompt_path= for experiments.
_DEFAULT_JUDGE_SYSTEM_PROMPT = """Tu ești un evaluator expert în meteorologie care acorda procentaje de corelare in intervalul [0, 1]. Trebuie să analizezi și să compari răspunsurile generate cu un text de referință. Rolul tău este să acționezi ca un judecător imparțial care evaluează calitatea și conformitatea răspunsului cu structura și conținutul așteptat.

PROCESUL DE EVALUARE:

PASUL 1 - ANALIZA REFERINTEI:
Analizează mai întâi textul de referință și identifică următoarele elemente structurale:

1. Observații generale despre vremea din ziua curentă comparativ cu zilele precedente, pe baza temperaturilor și prognozelor anterioare.

2. Descrierea stării cerului (pe baza valorii Nop: 1=senin, 8=acoperit) și a vântului (pe baza valorii Rff1: sub 3 m/s=slab, peste 6 m/s=puternic).

3. Această propoziție există DOAR DACĂ sunt menționate fenomene meteorologice repetate în ultimele 24 ore (ploi, ninsori, ceață, etc.). Dacă nu există fenomene repetate, această propoziție lipsește.

4. Informații despre temperatura maximă la cele 3 stații meteo din București: Filaret, Băneasa și Afumați.

5. Predicția pentru temperaturile de la ora 6:00 dimineața la cele 3 stații din București.

PASUL 2 - ANALIZA RĂSPUNSULUI:
Analizează răspunsul generat folosind aceeași structură de 5 puncte și numără propozițiile.

PASUL 3 - EVALUAREA:
Pentru fiecare dintre cele 5 puncte definite la PASUL 1, coreleaza si evaluează propozitiile din referinta cu cele din raspuns in urmatoarele moduri:
- Prezența informației corecte
- Acuratețea datelor numerice
- Respectarea ordinii și logicii expunerii

IMPORTANT:
- Coreleaza propozitiile din referinta cu cele din raspuns pentru a oferi procentaje cat mai corecte, desi in unele cazuri in referinta apar propozitii suplimentare redundante.
- Mentioneaza pentru fiecare parte din structura definita anterior motivul pentru care s-au corelat sau nu propozitiile din referinta si raspuns
- Dupa mentionarea motivului ofera un procentaj de corelare cuprins in intervalul [0, 1] si avand 2 zecimale
- Daca diferenta dintre temperaturile propozitiilor corelate > 2 grade Celsius sau diferenta dintre vitezele vantului > 5 m/s atunci procentajul se va duce spre 0. Cu cat diferenta dintre temperaturi sau vitezele vantului este mai mica cu atat procentajul se va duce spre 1

FORMATUL FINAL AL RĂSPUNSULUI:
După analiza completă, oferă procentajele finale în formatul: [x, x, x, x, x] daca au fost 5 propozitii corelate, sau [x, x, x, x] daca au fost doar 4 propozitii corelate intre referinta si raspuns"""


# ---------------------------------------------------------------------------
# Helpers: API key, system prompt, judge call
# ---------------------------------------------------------------------------

def _resolve_api_key(provided: Optional[str]) -> str:
    """
    Return an OpenAI API key. Prefers an explicit argument, then the
    OPENAI_API_KEY environment variable. Raises if neither is set.
    """
    if provided:
        return provided
    env = os.environ.get("OPENAI_API_KEY")
    if env:
        return env
    raise RuntimeError(
        "OpenAI API key not provided. Pass api_key explicitly "
        "or set the OPENAI_API_KEY environment variable."
    )


def _load_judge_system_prompt(system_prompt_path: Optional[str]) -> str:
    """
    Load the judge system prompt from a file if a path is provided,
    otherwise return the embedded default.
    """
    if system_prompt_path is None:
        return _DEFAULT_JUDGE_SYSTEM_PROMPT
    try:
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(
            f"WARNING: judge system prompt not found at {system_prompt_path}; "
            "using embedded default"
        )
        return _DEFAULT_JUDGE_SYSTEM_PROMPT
    except Exception as e:
        print(
            f"WARNING: failed to load judge system prompt from {system_prompt_path} "
            f"({e}); using embedded default"
        )
        return _DEFAULT_JUDGE_SYSTEM_PROMPT


def _call_judge_api(
    client: OpenAI,
    judge_model: str,
    system_prompt: str,
    reference_text: str,
    response_text: str,
) -> str:
    """
    Issue one judge API call. Returns the raw response text on success or
    a string starting with 'Error:' on failure so callers can detect the
    failure without exception handling at the call site.
    """
    user_prompt = f"REFERINTA\n{reference_text}\n\nRASPUNS\n{response_text}"
    try:
        response = client.responses.create(
            model=judge_model,
            reasoning={"effort": _JUDGE_REASONING_EFFORT},
            instructions=system_prompt,
            input=user_prompt,
            max_output_tokens=_JUDGE_MAX_OUTPUT_TOKENS,
        )
        return response.output_text
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Score extraction
# ---------------------------------------------------------------------------

def _extract_correlation_scores(
    judge_response: str,
) -> Tuple[Optional[List[float]], Optional[float]]:
    """
    Extract the correlation score list from a judge response.

    Iterates through every bracketed expression in the response in REVERSE
    order and returns the first one that passes validation: 4 or 5 floats,
    each in [0, 1]. This handles judge responses where the chain-of-thought
    contains intermediate bracketed lists (e.g., 'cele 5 propoziții sunt
    [1, 2, 3, 4, 5]'); the previous implementation took matches[-1]
    unconditionally and silently dropped these rows.

    Returns (score_list, average) on success or (None, None) on failure.
    """
    matches = _BRACKETED_LIST_RE.findall(judge_response)
    if not matches:
        return None, None

    for match in reversed(matches):
        try:
            scores = [float(x.strip()) for x in match.split(",")]
        except ValueError:
            continue
        if len(scores) not in _VALID_SCORE_LIST_LENGTHS:
            continue
        if not all(0.0 <= s <= 1.0 for s in scores):
            continue
        return scores, sum(scores) / len(scores)

    return None, None


# ---------------------------------------------------------------------------
# Judge JSON I/O
# ---------------------------------------------------------------------------

def _save_judge_json(
    judge_output_dir: Path,
    model_name: str,
    file_date: str,
    original_past_days: int,
    target_past_days: int,
    reference_text: str,
    response_text: str,
    judge_model: str,
    judge_response: str,
    seed: Optional[int] = None,
    judge_run_index: Optional[int] = None,
) -> None:
    """
    Serialize one scored judge result to a JSON file in judge_output_dir.

    Filename shape depends on whether the response came from a multi-seed
    inference run and whether this call is one of K judge runs:

      Single-seed, single judge run:
        {model}_{date}_{N}_past_days.json
      Multi-seed, single judge run:
        {model}_{date}_{N}_past_days_seed{seed}.json
      Single-seed, multi judge run:
        {model}_{date}_{N}_past_days_judge{judge_run_index}.json
      Multi-seed, multi judge run:
        {model}_{date}_{N}_past_days_seed{seed}_judge{judge_run_index}.json

    The seed and judge_run_index are also recorded inside the JSON payload
    so aggregation code can identify replicates without parsing filenames.
    """
    parts = [f"{model_name}_{file_date}_{original_past_days}_past_days"]
    if seed is not None:
        parts.append(f"_seed{seed}")
    if judge_run_index is not None:
        parts.append(f"_judge{judge_run_index}")
    filename = "".join(parts) + ".json"

    payload = {
        "model_name": model_name,
        "date": file_date,
        "original_past_days": original_past_days,
        "target_past_days": target_past_days,
        "reference_text": reference_text,
        "response_text": response_text,
        "judge_model": judge_model,
        "judge_response": judge_response,
        "inference_seed": seed,
        "judge_run_index": judge_run_index,
        "timestamp": time.time(),
    }
    with open(judge_output_dir / filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _resolve_date_from_folder(responses_folder: str) -> Optional[str]:
    """
    Reverse-engineer the date from a responses folder path. Expected layout:
        responses/{date}/{N}_past_days
    Works on both Windows and POSIX paths via PurePath.parts. Returns None
    if the path doesn't match the expected layout.
    """
    parts = PurePath(responses_folder).parts
    if len(parts) < 2:
        return None
    candidate = parts[-2]
    if re.match(r"^\d{4}-\d{2}-\d{2}$", candidate):
        return candidate
    return None


# ---------------------------------------------------------------------------
# Phase 1: scoring
# ---------------------------------------------------------------------------

def create_judge_analysis(
    responses_folder: str,
    reference_text: str,
    n_past_days: int,
    judge_model: str = _DEFAULT_JUDGE_MODEL,
    api_key: Optional[str] = None,
    date: Optional[str] = None,
    system_prompt_path: Optional[str] = None,
    n_judge_runs_per_response: int = 1,
    output_dir: Optional[str] = None,
) -> None:
    """
    Score every response JSON for past_days configurations 1..n_past_days
    against the reference text using the judge model, save per-file judge
    JSONs, and automatically aggregate the results into pivot tables.

    Args:
        responses_folder: Path to a responses/{date}/{N}_past_days folder.
            Used both to discover the responses to score and (when date=None)
            to reverse-engineer the date for the output directory.
        reference_text: Ground-truth text the judge should compare against.
        n_past_days: Highest past_days configuration to include. Folders
            for 1..n_past_days are all collected and scored together.
        judge_model: OpenAI model identifier for the judge. Default gpt-5-mini.
        api_key: Optional OpenAI API key. Falls back to OPENAI_API_KEY env var.
        date: Optional explicit date string. If None, parsed from
            responses_folder. Pass explicitly when running from a non-standard
            folder layout.
        system_prompt_path: Optional path to a custom judge rubric file. If
            None, uses the embedded _DEFAULT_JUDGE_SYSTEM_PROMPT.
        n_judge_runs_per_response: Number of independent judge calls per
            response file. Default 1 preserves the single-run schema and
            filename exactly. Set >1 for judge-noise variance estimation;
            each extra run multiplies OpenAI API cost linearly.

    When the input responses folder contains multi-seed response files
    (with `_seed{N}` suffix), each seed is judged independently and the
    seed is propagated into the judge JSON filename and payload. When
    n_judge_runs_per_response > 1, each (response, judge_run) pair gets
    its own judge JSON with `_judge{K}` suffix in the filename.

    On completion, calls generate_judge_analysis_tables() so the summary
    CSVs are always present after a successful scoring run.
    """
    if date is None:
        date = _resolve_date_from_folder(responses_folder)
    if date is None:
        print(
            f"ERROR: could not determine date from responses_folder "
            f"'{responses_folder}'. Pass date= explicitly."
        )
        return

    if n_judge_runs_per_response < 1:
        print(
            f"ERROR: n_judge_runs_per_response must be >= 1, "
            f"got {n_judge_runs_per_response}"
        )
        return

    base_responses_path = str(PurePath(responses_folder).parent)

    # Collect every response JSON across all past_days configurations
    all_json_files: List[str] = []
    for current_past_days in range(1, n_past_days + 1):
        current_folder = os.path.join(base_responses_path, f"{current_past_days}_past_days")
        if not os.path.exists(current_folder):
            print(f"WARNING: responses folder not found: {current_folder}")
            continue
        files = [
            f for f in glob(os.path.join(current_folder, "*.json"))
            if not os.path.basename(f).startswith("test_summary")
        ]
        all_json_files.extend(files)

    if not all_json_files:
        print(f"ERROR: no response JSON files found under {base_responses_path}")
        return

    total_judge_calls = len(all_json_files) * n_judge_runs_per_response
    judge_run_desc = (
        f", {n_judge_runs_per_response} judge runs per response"
        if n_judge_runs_per_response > 1 else ""
    )
    print(
        f"Judging {len(all_json_files)} response files for {date} "
        f"(past_days 1..{n_past_days}{judge_run_desc}, "
        f"{total_judge_calls} total judge calls)"
    )

    if output_dir is not None:
        judge_output_dir = Path(output_dir)
    else:
        judge_output_dir = _JUDGE_OUTPUT_BASE / judge_model / date / f"{n_past_days}_past_days"
    judge_output_dir.mkdir(parents=True, exist_ok=True)

    client = OpenAI(api_key=_resolve_api_key(api_key))
    system_prompt = _load_judge_system_prompt(system_prompt_path)

    successes = 0
    api_failures = 0
    parse_failures = 0
    multi_judge_runs = n_judge_runs_per_response > 1

    for json_file in all_json_files:
        try:
            # Use the seed-aware parser so multi-seed response filenames
            # correctly propagate the seed into each judge JSON. Files
            # without a seed suffix return seed=None and are handled the
            # same way as before.
            model_name, file_date, original_past_days, seed_val = (
                parse_filename_with_seed(json_file)
            )
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            response_text = extract_response_text(json_data)
        except Exception as e:
            print(f"ERROR loading {os.path.basename(json_file)}: {e}")
            continue

        for judge_run_index in range(n_judge_runs_per_response):
            judge_response = _call_judge_api(
                client=client,
                judge_model=judge_model,
                system_prompt=system_prompt,
                reference_text=reference_text,
                response_text=response_text,
            )

            if judge_response.startswith("Error:"):
                api_failures += 1
            else:
                scores, _ = _extract_correlation_scores(judge_response)
                if scores is None:
                    parse_failures += 1
                else:
                    successes += 1

            _save_judge_json(
                judge_output_dir=judge_output_dir,
                model_name=model_name,
                file_date=file_date,
                original_past_days=original_past_days,
                target_past_days=n_past_days,
                reference_text=reference_text,
                response_text=response_text,
                judge_model=judge_model,
                judge_response=judge_response,
                seed=seed_val,
                judge_run_index=judge_run_index if multi_judge_runs else None,
            )

            time.sleep(_JUDGE_API_DELAY_SECONDS)

    print(
        f"Judging complete: {successes}/{total_judge_calls} parsed, "
        f"{api_failures} API failures, {parse_failures} unparseable responses"
    )

    # Auto-aggregate so a single create_judge_analysis call always produces
    # the summary tables alongside the per-file judge JSONs.
    generate_judge_analysis_tables(str(judge_output_dir))


# ---------------------------------------------------------------------------
# Phase 2: aggregation
# ---------------------------------------------------------------------------

def generate_judge_analysis_tables(judge_output_dir: str) -> None:
    """
    Read every judge JSON in judge_output_dir, parse correlation scores, and
    write pivot tables and summary CSVs to judge_output_dir/analysis/.

    Detects multi-seed and/or multi-judge-run replicate data automatically:
    if any (model, past_days) cell has count > 1 after grouping, also emits
    std companion pivot tables and a variance_summary.csv for error-bar
    plotting. High-variance cells (std > _VARIANCE_OUTLIER_THRESHOLD) are
    flagged in a single WARNING line at the end of the run.

    Safe to call on its own to re-aggregate without re-judging.
    """
    judge_output_path = Path(judge_output_dir)
    json_files = [
        f for f in glob(str(judge_output_path / "*.json"))
        if not os.path.basename(f).startswith("test_summary")
    ]
    if not json_files:
        print(f"ERROR: no judge JSON files found in {judge_output_dir}")
        return

    rows = _build_judge_dataframe_rows(json_files)
    if not rows:
        print(f"ERROR: no judge JSONs were successfully parsed in {judge_output_dir}")
        return

    df = pd.DataFrame(rows)
    df_valid = df[df["score_extracted"]].copy()

    n_total = len(df)
    n_valid = len(df_valid)
    print(f"Aggregating judge results: {n_valid}/{n_total} responses with valid scores")

    if n_valid == 0:
        print("ERROR: no valid scores extracted; nothing to aggregate")
        return

    _report_unparseable_groups(df)

    # Detect replicates: multiple rows per (model, past_days) cell across
    # seeds or judge runs. Triggers the std companion files and the
    # variance_summary.csv.
    cell_counts = df_valid.groupby(["model", "past_days"]).size()
    has_replicates = (cell_counts > 1).any()

    analysis_dir = judge_output_path / _ANALYSIS_SUBDIR_NAME
    analysis_dir.mkdir(parents=True, exist_ok=True)

    correlation_columns = sorted(c for c in df_valid.columns if re.match(r"^correlation_\d+$", c))
    numeric_columns = ["average_score"] + correlation_columns
    numeric_columns = [c for c in numeric_columns if c in df_valid.columns]

    _write_judge_pivots(df_valid, analysis_dir, correlation_columns, numeric_columns, has_replicates)
    _write_judge_summaries(df_valid, df, analysis_dir, numeric_columns, has_replicates)

    if has_replicates:
        _report_variance_outliers(df_valid)

    n_models = df_valid["model"].nunique()
    pd_min = int(df_valid["past_days"].min())
    pd_max = int(df_valid["past_days"].max())
    replicate_desc = ""
    if has_replicates:
        max_replicates = int(cell_counts.max())
        replicate_desc = f", up to {max_replicates} replicates per cell"
    print(
        f"Judge analysis tables written to {analysis_dir}: "
        f"{n_valid} responses, {n_models} models, "
        f"past_days {pd_min}..{pd_max}{replicate_desc}"
    )


def _build_judge_dataframe_rows(json_files: List[str]) -> List[Dict[str, Any]]:
    """
    Parse every judge JSON into one row dict. Each row carries the model
    name, date, past_days, seed and judge_run_index (for variance
    aggregation), parsed correlation scores (if any), and a score_extracted
    boolean.

    Seed and judge_run_index are read from the JSON payload first
    (authoritative when present) and fall back to the filename for
    legacy judge JSONs that don't have those fields in the payload.
    """
    rows: List[Dict[str, Any]] = []
    parse_errors = 0
    first_error_message: Optional[str] = None

    # Filename regex to extract optional _seed{N} and _judge{K} suffixes
    # for judge JSONs that predate the enriched payload schema.
    judge_filename_re = re.compile(
        r"(?P<stem>.+?_\d{4}-\d{2}-\d{2}_\d+_past_days)"
        r"(?:_seed(?P<seed>\d+))?"
        r"(?:_judge(?P<judge_run>\d+))?$"
    )

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                judge_data = json.load(f)
        except Exception as e:
            if parse_errors == 0:
                first_error_message = str(e)
            parse_errors += 1
            continue

        model_name = judge_data.get("model_name", "")
        file_date = judge_data.get("date", "")
        past_days = judge_data.get("original_past_days", 1)
        judge_response = judge_data.get("judge_response", "")
        seed_val = judge_data.get("inference_seed")
        judge_run = judge_data.get("judge_run_index")

        # Fallback: parse from filename for judge JSONs produced before
        # inference_seed / judge_run_index were added to the payload.
        if seed_val is None or judge_run is None:
            basename = os.path.basename(json_file).replace(".json", "")
            fm = judge_filename_re.match(basename)
            if fm is not None:
                if seed_val is None and fm.group("seed") is not None:
                    seed_val = int(fm.group("seed"))
                if judge_run is None and fm.group("judge_run") is not None:
                    judge_run = int(fm.group("judge_run"))

        scores, average = _extract_correlation_scores(judge_response)

        row: Dict[str, Any] = {
            "model": model_name,
            "date": file_date,
            "past_days": past_days,
            "seed": seed_val,
            "judge_run": judge_run,
            "filename": os.path.basename(json_file),
            "judge_response": judge_response,
            "correlation_scores": scores,
            "average_score": average,
            "score_extracted": scores is not None,
            "num_propositions": len(scores) if scores else None,
        }
        if scores:
            for i, s in enumerate(scores, start=1):
                row[f"correlation_{i}"] = s
        rows.append(row)

    if parse_errors > 0:
        print(
            f"WARNING: failed to load {parse_errors} judge JSONs "
            f"(first error: {first_error_message})"
        )

    return rows


def _report_unparseable_groups(df: pd.DataFrame) -> None:
    """
    Print a per-(model, past_days) summary of how many responses failed
    score extraction. Helps spot judge-CoT format outliers concentrated in
    a single model or configuration, instead of just seeing the aggregate
    success rate.
    """
    failed = df[~df["score_extracted"]]
    if len(failed) == 0:
        return

    grouped = failed.groupby(["model", "past_days"]).size().reset_index(name="count")
    parts = [
        f"{row['model']} [pd={row['past_days']}] x{row['count']}"
        for _, row in grouped.iterrows()
    ]
    print(f"Rows with unparseable judge responses: {', '.join(parts)}")


def _write_judge_pivots(
    df_valid: pd.DataFrame,
    analysis_dir: Path,
    correlation_columns: List[str],
    numeric_columns: List[str],
    has_replicates: bool,
) -> None:
    """
    Write the per-metric pivot tables (past_days x model) for the average
    score and each individual sentence correlation column. When replicates
    are present (n>1 rows per cell across seeds and/or judge runs), also
    emits companion std tables alongside each mean table.
    """
    if "average_score" in df_valid.columns:
        avg_mean = df_valid.pivot_table(
            index="past_days", columns="model", values="average_score", aggfunc="mean",
        )
        avg_mean.to_csv(analysis_dir / "average_scores_models_vs_past_days.csv")

        if has_replicates:
            avg_std = df_valid.pivot_table(
                index="past_days", columns="model", values="average_score", aggfunc="std",
            )
            avg_std.to_csv(analysis_dir / "average_scores_std_models_vs_past_days.csv")

    for corr_col in correlation_columns:
        numeric = pd.to_numeric(df_valid[corr_col], errors="coerce")
        if numeric.isna().all():
            continue
        temp = df_valid.copy()
        temp[corr_col] = numeric

        mean_pivot = temp.pivot_table(
            index="past_days", columns="model", values=corr_col, aggfunc="mean",
        )
        mean_pivot.to_csv(analysis_dir / f"{corr_col}_models_vs_past_days.csv")

        if has_replicates:
            std_pivot = temp.pivot_table(
                index="past_days", columns="model", values=corr_col, aggfunc="std",
            )
            std_pivot.to_csv(analysis_dir / f"{corr_col}_std_models_vs_past_days.csv")


def _write_judge_summaries(
    df_valid: pd.DataFrame,
    df_all: pd.DataFrame,
    analysis_dir: Path,
    numeric_columns: List[str],
    has_replicates: bool,
) -> None:
    """
    Write the cross-cutting summary files: overall stats, per-past_days
    summary, per-model summary, per-proposition-count summary, and the raw
    data dumps for both valid and all rows. When replicates are present,
    also emits a variance_summary.csv with per-cell mean/std/count designed
    for plotting error bars.
    """
    if "average_score" in df_valid.columns:
        df_valid["average_score"].describe().to_csv(
            analysis_dir / "overall_summary_statistics.csv"
        )

    if numeric_columns:
        clean = df_valid[["past_days", "model"] + numeric_columns].copy()
        for col in numeric_columns:
            clean[col] = pd.to_numeric(clean[col], errors="coerce")

        clean.groupby("past_days")[numeric_columns].agg(
            ["count", "mean", "std", "min", "max"]
        ).round(4).to_csv(analysis_dir / "summary_by_past_days.csv")

        clean.groupby("model")[numeric_columns].agg(
            ["count", "mean", "std", "min", "max"]
        ).round(4).to_csv(analysis_dir / "summary_by_model.csv")

        if has_replicates:
            # Per-cell (model, past_days) variance summary across all
            # replicates (seed x judge_run). One row per cell.
            variance_summary = clean.groupby(
                ["model", "past_days"]
            )[numeric_columns].agg(["mean", "std", "count"]).round(4)
            variance_summary.to_csv(analysis_dir / "variance_summary.csv")

        if "num_propositions" in df_valid.columns:
            clean_with_props = clean.copy()
            clean_with_props["num_propositions"] = df_valid["num_propositions"].values
            clean_with_props.groupby("num_propositions")[numeric_columns].agg(
                ["count", "mean", "std"]
            ).round(4).to_csv(analysis_dir / "summary_by_propositions.csv")

    df_all.to_csv(analysis_dir / "raw_judge_data.csv", index=False)
    df_valid.to_csv(analysis_dir / "valid_scores_data.csv", index=False)


def _report_variance_outliers(df_valid: pd.DataFrame) -> None:
    """
    Print a summary of (model, past_days) cells whose judge score std
    across replicates exceeds _VARIANCE_OUTLIER_THRESHOLD on the 0-1 scale.
    Useful for spotting configurations where the decoder (or judge) is
    noisy enough that single-run comparisons are unreliable.

    No-op if no replicates are present or no cell exceeds the threshold.
    """
    if "average_score" not in df_valid.columns:
        return

    cell_stats = df_valid.groupby(["model", "past_days"])["average_score"].agg(
        ["mean", "std", "count"]
    )
    outliers = cell_stats[
        (cell_stats["count"] > 1) & (cell_stats["std"] > _VARIANCE_OUTLIER_THRESHOLD)
    ]
    if len(outliers) == 0:
        return

    parts = [
        f"{model} [pd={past_days}] std={row['std']:.3f} (n={int(row['count'])})"
        for (model, past_days), row in outliers.iterrows()
    ]
    print(
        f"WARNING: {len(outliers)} (model, past_days) cells have "
        f"std > {_VARIANCE_OUTLIER_THRESHOLD}: {', '.join(parts)}"
    )
    
# import os
# import json
# import time
# import re
# from datetime import datetime, timedelta
# from pathlib import Path
# from typing import Dict, List, Optional
# from openai import OpenAI
# import pdfplumber

# def extract_yearly_diagnoses_and_format(
#     year: int,
#     judge_model: str,
#     output_folder: str,
#     base_folder: str = "date/all_diagnosis_forecast_text",
#     api_key: str = None,
#     delay_between_calls: float = 1.0
# ) -> Dict[str, Dict[str, str]]:
#     """
#     Extract all diagnoses for a given year and format them using GPT-5-mini.
    
#     Args:
#         year (int): Year to process (e.g., 2024)
#         base_folder (str): Base folder containing PDF files organized by date
#         api_key (str): OpenAI API key (optional, uses environment variable if None)
#         output_folder (str): Folder to save formatted diagnoses
#         delay_between_calls (float): Delay between API calls in seconds
    
#     Returns:
#         Dict containing all formatted diagnoses with dates as keys
#     """
    
#     print(f"Starting yearly diagnosis extraction and formatting for {year}")
#     print(f"=" * 60)
    
#     # Initialize OpenAI client
#     if api_key:
#         client = OpenAI(api_key=api_key)
#     else:
#         client = OpenAI()  # Uses OPENAI_API_KEY environment variable
    
#     # Create system prompt for GPT-5-mini
#     system_prompt = create_diagnosis_formatting_system_prompt()
    
#     # Find all PDF files for the year
#     pdf_files = find_all_pdf_files_for_year(year, base_folder)
    
#     if not pdf_files:
#         print(f"No PDF files found for year {year}")
#         return {}
    
#     print(f"Found {len(pdf_files)} PDF files for year {year}")
#     print(f"Date range: {min(pdf_files.keys())} to {max(pdf_files.keys())}")
    
#     # Create output directory
#     output_path = Path(output_folder)
#     output_path.mkdir(exist_ok=True)
    
#     # Process each diagnosis
#     formatted_diagnoses = {}
#     successful_extractions = 0
#     failed_extractions = 0
    
#     for date_str in sorted(pdf_files.keys()):
#         pdf_path = pdf_files[date_str]
        
#         print(f"\nProcessing {date_str}: {Path(pdf_path).name}")
        
#         try:
#             # Extract diagnosis from PDF
#             extracted_data = extract_forecast_from_single_pdf(pdf_path, date_str)
            
#             if not extracted_data:
#                 print(f"  Failed to extract diagnosis from PDF")
#                 failed_extractions += 1
#                 continue
            
#             original_diagnosis = extracted_data['forecast_text']
            
#             # Format diagnosis using GPT-5-mini
#             formatted_result = format_diagnosis_with_gpt(
#                 client, system_prompt, original_diagnosis, date_str, judge_model
#             )
            
#             if formatted_result:
#                 formatted_diagnoses[date_str] = {
#                     'original_diagnosis': original_diagnosis,
#                     'formatted_diagnosis': formatted_result,
#                     'interval': extracted_data.get('interval', ''),
#                     'pdf_path': pdf_path,
#                     'processing_timestamp': datetime.now().isoformat()
#                 }
#                 successful_extractions += 1
#                 print(f"  ✅ Successfully formatted diagnosis")
#             else:
#                 print(f"  ❌ Failed to format diagnosis")
#                 failed_extractions += 1
            
#             # Delay between API calls
#             if delay_between_calls > 0:
#                 time.sleep(delay_between_calls)
                
#         except Exception as e:
#             print(f"  ❌ Error processing {date_str}: {str(e)}")
#             failed_extractions += 1
#             continue
    
#     # Save results to JSON file
#     output_file = output_path / f"formatted_diagnoses_{year}.json"
    
#     try:
#         with open(output_file, 'w', encoding='utf-8') as f:
#             json.dump(formatted_diagnoses, f, ensure_ascii=False, indent=2)
        
#         print(f"\n" + "=" * 60)
#         print(f"YEARLY PROCESSING COMPLETE")
#         print(f"=" * 60)
#         print(f"Year: {year}")
#         print(f"Total PDFs found: {len(pdf_files)}")
#         print(f"Successfully processed: {successful_extractions}")
#         print(f"Failed: {failed_extractions}")
#         print(f"Success rate: {successful_extractions/len(pdf_files)*100:.1f}%")
#         print(f"Results saved to: {output_file}")
        
#     except Exception as e:
#         print(f"❌ Error saving results: {e}")
    
#     return formatted_diagnoses

# def create_diagnosis_formatting_system_prompt() -> str:
#     """
#     Create the system prompt for GPT-5-mini to format diagnoses.
    
#     Returns:
#         str: System prompt in Romanian
#     """
    
#     system_prompt = """Tu ești un expert adnotator pentru diagnozele meteorologice românești. Sarcina ta este să reformatezi diagnozele meteorologice pentru a urma strict o structură de 5 propoziții.

# STRUCTURA OBLIGATORIE A RĂSPUNSULUI:

# 1. PRIMA PROPOZIȚIE: Observații generale despre vremea din ziua curentă comparativ cu zilele precedente.

# 2. A DOUA PROPOZIȚIE: Descrierea stării cerului (senin sau acoperit de nori) și a vântului (slab sau puternic).

# 3. A TREIA PROPOZIȚIE (OPȚIONALĂ): Această propoziție se include DOAR DACĂ un fenomen meteorologic din textul original al diagnozei a avut o influență semnificativă asupra vremii în ultimele 24 de ore (de exemplu: ploi, ninsori, ceață, etc.). Dacă nu este menționat niciun fenomen specific, se omite această propoziție.

# 4. A PATRA PROPOZIȚIE (sau a treia dacă nu există fenomene semnificative): Informații despre temperatura maximă înregistrată la cele 3 stații meteo din București: Filaret, Băneasa și Afumați din decursul ultimelor 24h.

# 5. PROPOZIȚIA FINALĂ: Menționează temperaturile înregistrate la ora 6:00 dimineața la cele 3 stații din București (Filaret, Băneasa, Afumați).

# INSTRUCȚIUNI IMPORTANTE:

# - Păstrează EXACT eticheletele de propoziții (PRIMA PROPOZIȚIE, A DOUA PROPOZIȚIE, etc.)
# - Dacă diagnoza originală are mai mult de 5 propoziții, combină sau comprimă informațiile similare
# - Dacă nu există suficiente informații pentru o propoziție specifică, folosește eticheta urmată de "-" (exemplu: "PRIMA PROPOZIȚIE: -")
# - Menține terminologia meteorologică profesională
# - Păstrează valorile numerice exacte din textul original
# - Nu adăuga informații care nu există în textul original

# Răspunde DOAR cu propozițiile formatate, fără explicații suplimentare."""

#     return system_prompt

# def find_all_pdf_files_for_year(year: int, base_folder: str) -> Dict[str, str]:
#     """
#     Find all PDF files for a specific year.
    
#     Args:
#         year (int): Year to search for
#         base_folder (str): Base folder containing PDFs organized by date
    
#     Returns:
#         Dict[date_str, pdf_path]: Dictionary mapping dates to PDF file paths
#     """
    
#     base_path = Path(base_folder)
#     pdf_files = {}
    
#     # Start from January 1st
#     start_date = datetime(year, 1, 1).date()
    
#     # End on December 31st
#     end_date = datetime(year, 12, 31).date()
    
#     current_date = start_date
    
#     while current_date <= end_date:
#         date_str = current_date.strftime("%Y-%m-%d")
        
#         # Construct path: base_folder/YYYY/MM/DD
#         year_str = current_date.strftime("%Y")
#         month_str = current_date.strftime("%m")
#         day_str = current_date.strftime("%d")
        
#         date_folder = base_path / year_str / month_str / day_str
        
#         if date_folder.exists():
#             # Find PDF files in this folder
#             pdf_files_in_folder = list(date_folder.glob("*.pdf"))
            
#             if pdf_files_in_folder:
#                 # Take the first PDF file found (assuming one per day)
#                 pdf_path = str(pdf_files_in_folder[0])
#                 pdf_files[date_str] = pdf_path
            
#         # Move to next day
#         current_date += timedelta(days=1)
    
#     return pdf_files

# def extract_forecast_from_single_pdf(pdf_path: str, target_date: str) -> Optional[Dict[str, str]]:
#     """
#     Extract meteorological forecast text from a single PDF file.
#     (Reused from the provided extract_pdf_data.py)
#     """
    
#     try:
#         with pdfplumber.open(pdf_path) as pdf:
#             full_text = ""
            
#             # Extract text from all pages
#             for page in pdf.pages:
#                 page_text = page.extract_text()
#                 if page_text:
#                     full_text += page_text + "\n"
            
#             if not full_text.strip():
#                 return None
            
#             # Split into lines for processing
#             lines = full_text.split('\n')
            
#             # Find the interval line
#             interval_line = None
#             interval_line_idx = -1
            
#             for i, line in enumerate(lines):
#                 # Look for the interval pattern
#                 if re.search(r'SITUAȚIA METEOROLOGICĂ PENTRU INTERVALUL.*ORA.*-.*ORA', line, re.IGNORECASE):
#                     interval_line = line.strip()
#                     interval_line_idx = i
#                     break
            
#             if not interval_line:
#                 return None
            
#             # Find BUCUREȘTI section
#             bucuresti_start_idx = -1
#             for i in range(interval_line_idx + 1, len(lines)):
#                 if 'BUCUREȘTI' in lines[i].upper():
#                     bucuresti_start_idx = i
#                     break
            
#             if bucuresti_start_idx == -1:
#                 return None
            
#             # Find PROGNOZĂ section (end marker)
#             prognoza_idx = -1
#             for i in range(bucuresti_start_idx + 1, len(lines)):
#                 if 'PROGNOZĂ' in lines[i].upper():
#                     prognoza_idx = i
#                     break
            
#             if prognoza_idx == -1:
#                 # If no PROGNOZĂ found, take until end of meaningful content
#                 prognoza_idx = len(lines)
#                 # Look for other section markers that might indicate end
#                 for i in range(bucuresti_start_idx + 1, len(lines)):
#                     if any(marker in lines[i].upper() for marker in ['OBSERVAȚII', 'AVERTIZARE', 'ATENȚIE']):
#                         prognoza_idx = i
#                         break
            
#             # Extract the forecast text
#             forecast_lines = []
#             for i in range(bucuresti_start_idx, prognoza_idx):
#                 line = lines[i].strip()
#                 if line:  # Skip empty lines
#                     forecast_lines.append(line)
            
#             forecast_text = '\n'.join(forecast_lines)
            
#             if not forecast_text.strip():
#                 return None
            
#             return {
#                 'interval': interval_line,
#                 'forecast_text': forecast_text,
#                 'file_path': pdf_path
#             }
            
#     except Exception as e:
#         print(f"Error processing {pdf_path}: {e}")
#         return None

# def format_diagnosis_with_gpt(
#     client: OpenAI, 
#     system_prompt: str, 
#     original_diagnosis: str, 
#     date_str: str,
#     judge_model: str
# ) -> Optional[Dict[str, str]]:
#     """
#     Format a diagnosis using GPT-5-mini API.
    
#     Args:
#         client: OpenAI client
#         system_prompt: System prompt for formatting
#         original_diagnosis: Original diagnosis text
#         date_str: Date string for logging
    
#     Returns:
#         Dict with formatted sentences or None if failed
#     """
    
#     user_prompt = f"Reformatează următoarea diagnoză meteorologică pentru data {date_str}:\n\n{original_diagnosis}"
    
#     try:
#         response = client.responses.create(
#             model=judge_model,
#             reasoning={"effort": "minimal"},
#             instructions=system_prompt,
#             input=user_prompt,
#             # Temperature only works for GPT models (e.g., gpt-4), not reasoning models (e.g., gpt-5, o3)
#             # temperature=0.1, 
#             max_output_tokens=10000
#         )
        
#         formatted_text = response.output_text
        
#         # Parse the formatted response into structured sentences
#         parsed_sentences = parse_formatted_diagnosis(formatted_text)
        
#         return parsed_sentences
        
#     except Exception as e:
#         print(f"  API call failed for {date_str}: {e}")
#         return None

# def parse_formatted_diagnosis(formatted_text: str) -> Dict[str, str]:
#     """
#     Parse the formatted diagnosis response into individual sentences.
    
#     Args:
#         formatted_text: The GPT-formatted diagnosis text
    
#     Returns:
#         Dict mapping sentence labels to their content
#     """
    
#     sentences = {}
    
#     # Define the sentence patterns to look for
#     patterns = [
#         r'PRIMA PROPOZIȚIE:\s*(.+?)(?=\n\n|\nA DOUA PROPOZIȚIE|\nA TREIA PROPOZIȚIE|\nA PATRA PROPOZIȚIE|\nPROPOZIȚIA FINALĂ|$)',
#         r'A DOUA PROPOZIȚIE:\s*(.+?)(?=\n\n|\nA TREIA PROPOZIȚIE|\nA PATRA PROPOZIȚIE|\nPROPOZIȚIA FINALĂ|$)',
#         r'A TREIA PROPOZIȚIE[^:]*:\s*(.+?)(?=\n\n|\nA PATRA PROPOZIȚIE|\nPROPOZIȚIA FINALĂ|$)',
#         r'A PATRA PROPOZIȚIE[^:]*:\s*(.+?)(?=\n\n|\nPROPOZIȚIA FINALĂ|$)',
#         r'PROPOZIȚIA FINALĂ:\s*(.+?)(?=\n\n|$)'
#     ]
    
#     labels = [
#         'PRIMA_PROPOZITIE',
#         'A_DOUA_PROPOZITIE', 
#         'A_TREIA_PROPOZITIE',
#         'A_PATRA_PROPOZITIE',
#         'PROPOZITIA_FINALA'
#     ]
    
#     # Clean the text for better parsing
#     text = formatted_text.replace('\n', ' ').strip()
    
#     for i, pattern in enumerate(patterns):
#         match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
#         if match:
#             content = match.group(1).strip()
#             # Remove any trailing punctuation or extra whitespace
#             content = re.sub(r'\s+', ' ', content)
#             sentences[labels[i]] = content
    
#     return sentences

# def validate_yearly_extraction(year: int, sample_dates: List[str] = None):
#     """
#     Validate the yearly extraction by showing samples.
    
#     Args:
#         year: Year to validate
#         sample_dates: Specific dates to check (optional)
#     """
    
#     results_file = Path("formatted_diagnoses_year") / f"formatted_diagnoses_{year}.json"
    
#     if not results_file.exists():
#         print(f"Results file not found: {results_file}")
#         return
    
#     with open(results_file, 'r', encoding='utf-8') as f:
#         data = json.load(f)
    
#     print(f"Validation for year {year}")
#     print(f"=" * 40)
#     print(f"Total diagnoses: {len(data)}")
    
#     if sample_dates:
#         dates_to_check = sample_dates
#     else:
#         # Take first 3 dates as samples
#         dates_to_check = sorted(data.keys())[:3]
    
#     for date_str in dates_to_check:
#         if date_str in data:
#             print(f"\nSample: {date_str}")
#             print(f"-" * 20)
#             print(f"Original length: {len(data[date_str]['original_diagnosis'])} chars")
#             print(f"Formatted length: {len(data[date_str]['formatted_diagnosis'])} chars")
#             print(f"\nFormatted diagnosis:")
#             print(f"{data[date_str]['formatted_diagnosis']}")
#         else:
#             print(f"Date {date_str} not found in results")
    
"""
Yearly diagnosis extraction and formatting pipeline.

Walks every PDF forecast for a given year, extracts the Bucharest-section
text, and calls a reasoning model (typically gpt-5-mini) to reformat the
raw diagnosis into a structured 5-sentence format. Writes the result to
formatted_diagnoses_{year}.json, which is the foundational input to the
rest of the project:

    - dataset_creation.py reads it to build train/test data
    - response_evaluation.load_reference_text reads it for eval metrics

Public API (same shape as the pre-cleanup create_dataset.py):

    extract_yearly_diagnoses_and_format(year, judge_model, output_folder, ...)
    validate_yearly_extraction(year, output_folder, sample_dates=None)

KEY DESIGN POINTS for downstream readers:

1. Checkpointing. If formatted_diagnoses_{year}.json already exists at the
   output folder, its contents are loaded and already-formatted dates are
   skipped. This makes the pipeline resumable - a failure 10 hours into
   a 12-hour run can be recovered by rerunning without losing progress.
   The incremental save happens after every successful date, not just at
   the end.

2. API key resolution. Prefers explicit api_key parameter, then
   OPENAI_API_KEY env var, then raises with a clear message. The previous
   module accepted api_key=None and silently fell through to OpenAI()'s
   default env-var behavior, which obscured errors when the env var was
   also unset. The previous main.py call site passed a hardcoded key;
   that key has been rotated and removed from the codebase.

3. PDF extraction reuses input_extraction.py. The previous module
   duplicated the BUCUREȘTI-section extraction logic from extract_pdf_data.py
   (now input_extraction.py). The cleaned version calls into the shared
   extractor so bug fixes propagate.

4. Structured-sentence parsing is line-based. The previous parser replaced
   all newlines with spaces and then used regex lookaheads that required
   newlines to function - a bug that happened to work only because the
   sentence labels acted as implicit delimiters. The cleaned parser reads
   the model output line by line, splits at known label prefixes, and is
   robust to responses where one section's content mentions another
   section's label name.

5. Structured-sentence schema is uniform. All formatted diagnoses have
   the same five keys (PRIMA_PROPOZITIE through PROPOZITIA_FINALA);
   missing sentences are set to empty string rather than omitted from
   the dict. Downstream consumers can assume a consistent shape.

6. Retry on transient API errors. Rate-limit and transient 5xx errors
   trigger 3 attempts with 5s, 15s backoffs. Non-retriable errors
   (invalid request, auth) fail immediately.

7. METHODOLOGICAL NOTE: the system prompt instructs gpt-5-mini to
   "combină sau comprimă informațiile similare" (combine or compress
   similar information) when the original has more than 5 sentences.
   This means the formatted diagnoses contain gpt-5-mini's synthesis,
   not only the meteorologist's verbatim wording. Since these formatted
   diagnoses are used as reference text for ROUGE/BLEU/BERTScore
   evaluation downstream, the evaluation is partly circular - models
   are scored on how well they match gpt-5-mini's reformatting style.
   This is a known limitation discussed in the project report and is
   preserved here for continuity; do not change the system prompt
   without coordinating with the evaluation methodology.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI

from prompting.utils.input_extraction import extract_forecasts_sequential


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_BASE_FOLDER = "date/all_diagnosis_forecast_text"
_DEFAULT_DELAY_BETWEEN_CALLS = 1.0
_MAX_OUTPUT_TOKENS = 1500
_REASONING_EFFORT = "minimal"

_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = (5, 15)

# The five structured-sentence keys produced by the formatting pass.
# The order here is the order they appear in the system prompt.
_SENTENCE_KEYS = [
    "PRIMA_PROPOZITIE",
    "A_DOUA_PROPOZITIE",
    "A_TREIA_PROPOZITIE",
    "A_PATRA_PROPOZITIE",
    "PROPOZITIA_FINALA",
]

# Maps the Romanian label (as it appears in the gpt-5-mini output) to
# the corresponding ASCII-safe dictionary key used downstream.
_LABEL_TO_KEY = {
    "PRIMA PROPOZIȚIE": "PRIMA_PROPOZITIE",
    "A DOUA PROPOZIȚIE": "A_DOUA_PROPOZITIE",
    "A TREIA PROPOZIȚIE": "A_TREIA_PROPOZITIE",
    "A PATRA PROPOZIȚIE": "A_PATRA_PROPOZITIE",
    "PROPOZIȚIA FINALĂ": "PROPOZITIA_FINALA",
}

_SYSTEM_PROMPT = """Tu ești un expert adnotator pentru diagnozele meteorologice românești. Sarcina ta este să reformatezi diagnozele meteorologice pentru a urma strict o structură de 5 propoziții.

STRUCTURA OBLIGATORIE A RĂSPUNSULUI:

1. PRIMA PROPOZIȚIE: Observații generale despre vremea din ziua curentă comparativ cu zilele precedente.

2. A DOUA PROPOZIȚIE: Descrierea stării cerului (senin sau acoperit de nori) și a vântului (slab sau puternic).

3. A TREIA PROPOZIȚIE (OPȚIONALĂ): Această propoziție se include DOAR DACĂ un fenomen meteorologic din textul original al diagnozei a avut o influență semnificativă asupra vremii în ultimele 24 de ore (de exemplu: ploi, ninsori, ceață, etc.). Dacă nu este menționat niciun fenomen specific, se omite această propoziție.

4. A PATRA PROPOZIȚIE (sau a treia dacă nu există fenomene semnificative): Informații despre temperatura maximă înregistrată la cele 3 stații meteo din București: Filaret, Băneasa și Afumați din decursul ultimelor 24h.

5. PROPOZIȚIA FINALĂ: Menționează temperaturile înregistrate la ora 6:00 dimineața la cele 3 stații din București (Filaret, Băneasa, Afumați).

INSTRUCȚIUNI IMPORTANTE:

- Păstrează EXACT eticheletele de propoziții (PRIMA PROPOZIȚIE, A DOUA PROPOZIȚIE, etc.)
- Dacă diagnoza originală are mai mult de 5 propoziții, combină sau comprimă informațiile similare
- Dacă nu există suficiente informații pentru o propoziție specifică, folosește eticheta urmată de "-" (exemplu: "PRIMA PROPOZIȚIE: -")
- Menține terminologia meteorologică profesională
- Păstrează valorile numerice exacte din textul original
- Nu adăuga informații care nu există în textul original

Răspunde DOAR cu propozițiile formatate, fără explicații suplimentare."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_api_key(provided: Optional[str]) -> str:
    """
    Return an OpenAI API key. Prefers explicit argument, then OPENAI_API_KEY
    env var. Raises with a clear message if neither is set.
    """
    if provided:
        return provided
    env = os.environ.get("OPENAI_API_KEY")
    if env:
        return env
    raise RuntimeError(
        "OpenAI API key not provided. Pass api_key explicitly or set the "
        "OPENAI_API_KEY environment variable."
    )


def _find_all_pdf_files_for_year(year: int, base_folder: str) -> Dict[str, str]:
    """
    Walk base_folder/{year}/{month}/{day}/ for every day of the given year
    and return a mapping of date_str -> first PDF found in that folder.
    Dates without a matching folder or without any PDF in the folder are
    simply omitted.
    """
    base_path = Path(base_folder)
    pdf_files: Dict[str, str] = {}

    start_date = datetime(year, 1, 1).date()
    end_date = datetime(year, 12, 31).date()
    current_date = start_date

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        date_folder = (
            base_path
            / current_date.strftime("%Y")
            / current_date.strftime("%m")
            / current_date.strftime("%d")
        )
        if date_folder.exists():
            pdfs = list(date_folder.glob("*.pdf"))
            if pdfs:
                # Multiple PDFs in one date folder is unexpected but not
                # a hard error; take the first deterministically.
                pdf_files[date_str] = str(sorted(pdfs)[0])
        current_date += timedelta(days=1)

    return pdf_files


def _extract_forecast_from_single_pdf(pdf_path: str) -> Optional[Dict[str, str]]:
    """
    Wrapper around input_extraction.extract_forecasts_sequential that
    fetches the first forecast block from a single PDF. Returns None
    if no BUCUREȘTI section is found or the PDF is malformed.

    The previous module had this logic inlined with its own regex
    matching; this version delegates to the shared extractor so fixes
    in input_extraction.py propagate here automatically.
    """
    try:
        forecasts = extract_forecasts_sequential(pdf_path)
    except Exception as e:
        print(f"ERROR extracting PDF {pdf_path}: {e}")
        return None

    if not forecasts:
        return None

    # extract_forecasts_sequential returns a list (one entry per interval
    # found in the PDF); the first one is the current-day forecast,
    # which is what we want.
    first = forecasts[0]
    return {
        "interval": first.get("interval", ""),
        "forecast_text": first.get("forecast_text", ""),
        "file_path": pdf_path,
    }


def _format_diagnosis_with_gpt(
    client: OpenAI,
    original_diagnosis: str,
    date_str: str,
    judge_model: str,
) -> Optional[Dict[str, str]]:
    """
    Call the judge model to reformat one diagnosis. Retries up to 3 times
    on transient errors with 5s, 15s backoffs. Returns the parsed
    structured-sentence dict, or None on permanent failure.
    """
    user_prompt = (
        f"Reformatează următoarea diagnoză meteorologică pentru data "
        f"{date_str}:\n\n{original_diagnosis}"
    )

    last_error: Optional[str] = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            response = client.responses.create(
                model=judge_model,
                reasoning={"effort": _REASONING_EFFORT},
                instructions=_SYSTEM_PROMPT,
                input=user_prompt,
                # NOTE: temperature is a parameter only for legacy GPT
                # models; reasoning models (gpt-5, o3, o4) ignore it.
                max_output_tokens=_MAX_OUTPUT_TOKENS,
            )
            formatted_text = response.output_text
            return _parse_formatted_diagnosis(formatted_text)

        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            if attempt < _RETRY_ATTEMPTS - 1:
                backoff = _RETRY_BACKOFF_SECONDS[attempt]
                print(
                    f"  WARNING: format attempt {attempt + 1}/{_RETRY_ATTEMPTS} "
                    f"failed for {date_str} ({last_error}); retrying in {backoff}s"
                )
                time.sleep(backoff)

    print(f"  ERROR: formatting {date_str} failed after {_RETRY_ATTEMPTS} attempts: {last_error}")
    return None


def _parse_formatted_diagnosis(formatted_text: str) -> Dict[str, str]:
    """
    Parse the gpt-5-mini response into a structured-sentence dict.

    Algorithm:
        1. Walk the text line by line.
        2. When a line starts with (or contains early) one of the known
           Romanian sentence labels, start a new section under that label.
        3. Accumulate subsequent non-label lines into the current section.
        4. Initialize all five expected keys to empty string at the end;
           sections the model omitted simply stay empty.

    This is robust to:
        - Extra blank lines between sections
        - Content that mentions a label name (because we only match labels
          that appear at the START of a line, not anywhere in the text)
        - Out-of-order sections (each label opens its own bucket)
        - Missing optional sections (A_TREIA_PROPOZITIE)
    """
    sections: Dict[str, List[str]] = {key: [] for key in _SENTENCE_KEYS}
    current_key: Optional[str] = None

    for raw_line in formatted_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Check if the line begins with one of the known labels
        matched_key: Optional[str] = None
        matched_content: str = ""
        for label, key in _LABEL_TO_KEY.items():
            # Match the label optionally followed by parenthetical notes
            # like "(OPȚIONALĂ)" and the colon separator
            pattern = rf"^{re.escape(label)}[^:]*:\s*(.*)$"
            m = re.match(pattern, line, re.IGNORECASE)
            if m:
                matched_key = key
                matched_content = m.group(1).strip()
                break

        if matched_key is not None:
            current_key = matched_key
            if matched_content:
                sections[current_key].append(matched_content)
        elif current_key is not None:
            # Continuation of the current section
            sections[current_key].append(line)

    # Collapse accumulated lines into single strings. A missing section
    # becomes an empty string - consistent shape across all diagnoses.
    # The "-" convention from the system prompt ("PRIMA PROPOZIȚIE: -")
    # is preserved as literal "-" rather than normalized, so downstream
    # consumers can distinguish "intentionally absent" from "section not
    # generated at all" by checking for "-" vs "".
    result: Dict[str, str] = {}
    for key in _SENTENCE_KEYS:
        content = " ".join(sections[key]).strip()
        content = re.sub(r"\s+", " ", content)
        result[key] = content

    return result


def _load_existing_checkpoint(output_file: Path) -> Dict[str, Dict]:
    """
    Load any existing formatted_diagnoses_{year}.json file to resume from
    a previous partial run. Returns empty dict if the file does not exist
    or cannot be parsed; the pipeline then starts from scratch.
    """
    if not output_file.exists():
        return {}
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            print(f"WARNING: {output_file} is not a dict; ignoring checkpoint")
            return {}
        print(f"Resuming from checkpoint: {len(data)} dates already formatted in {output_file}")
        return data
    except Exception as e:
        print(f"WARNING: cannot read checkpoint {output_file} ({e}); starting fresh")
        return {}


def _save_checkpoint(output_file: Path, formatted_diagnoses: Dict[str, Dict]) -> None:
    """Write the current formatted_diagnoses dict to disk atomically."""
    tmp_file = output_file.with_suffix(output_file.suffix + ".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(formatted_diagnoses, f, ensure_ascii=False, indent=2)
    # Atomic rename on POSIX; on Windows tmp_file is replaced atomically
    # via os.replace semantics.
    os.replace(tmp_file, output_file)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_yearly_diagnoses_and_format(
    year: int,
    judge_model: str,
    output_folder: str,
    base_folder: str = _DEFAULT_BASE_FOLDER,
    api_key: Optional[str] = None,
    delay_between_calls: float = _DEFAULT_DELAY_BETWEEN_CALLS,
) -> Dict[str, Dict[str, str]]:
    """
    Extract and format every forecast PDF for a given year.

    Args:
        year: Calendar year to process (e.g., 2024).
        judge_model: OpenAI model name for the formatting pass. Typically
            gpt-5-mini or another reasoning model; gpt-4o and similar
            chat models will also work but ignore the reasoning effort.
        output_folder: Directory to write formatted_diagnoses_{year}.json
            into. Also checked for an existing checkpoint at startup.
        base_folder: Root directory containing the year/month/day PDF tree.
        api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
        delay_between_calls: Seconds to pause between successive API calls,
            to stay under rate limits. Set to 0 to disable.

    Returns:
        Dict keyed by date string (YYYY-MM-DD) with values:
            {
                "original_diagnosis": str,       # raw PDF text
                "formatted_diagnosis": dict,     # structured-sentence dict
                "interval": str,                 # PDF interval line
                "pdf_path": str,
                "processing_timestamp": str,
            }
    """
    resolved_key = _resolve_api_key(api_key)
    client = OpenAI(api_key=resolved_key)

    print(f"Starting yearly diagnosis extraction for {year} using {judge_model}")

    pdf_files = _find_all_pdf_files_for_year(year, base_folder)
    if not pdf_files:
        print(f"ERROR: no PDF files found for year {year} under {base_folder}")
        return {}

    print(
        f"Found {len(pdf_files)} PDF files for {year} "
        f"(date range: {min(pdf_files.keys())} to {max(pdf_files.keys())})"
    )

    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / f"formatted_diagnoses_{year}.json"

    # Checkpoint: load any previously-formatted dates so we can skip them
    formatted_diagnoses = _load_existing_checkpoint(output_file)

    successful_extractions = 0
    failed_extractions = 0
    skipped_extractions = 0

    for date_str in sorted(pdf_files.keys()):
        if date_str in formatted_diagnoses:
            skipped_extractions += 1
            continue

        pdf_path = pdf_files[date_str]
        print(f"Processing {date_str}: {Path(pdf_path).name}")

        extracted_data = _extract_forecast_from_single_pdf(pdf_path)
        if not extracted_data or not extracted_data.get("forecast_text", "").strip():
            print(f"  WARNING: could not extract forecast text from {pdf_path}")
            failed_extractions += 1
            continue

        original_diagnosis = extracted_data["forecast_text"]

        formatted_result = _format_diagnosis_with_gpt(
            client=client,
            original_diagnosis=original_diagnosis,
            date_str=date_str,
            judge_model=judge_model,
        )
        if formatted_result is None:
            failed_extractions += 1
            continue

        formatted_diagnoses[date_str] = {
            "original_diagnosis": original_diagnosis,
            "formatted_diagnosis": formatted_result,
            "interval": extracted_data.get("interval", ""),
            "pdf_path": pdf_path,
            "processing_timestamp": datetime.now().isoformat(),
        }
        successful_extractions += 1

        # Checkpoint after every successful format - resumable from any
        # point of failure, at the cost of one file rewrite per date.
        _save_checkpoint(output_file, formatted_diagnoses)

        if delay_between_calls > 0:
            time.sleep(delay_between_calls)

    total = len(pdf_files)
    attempted = total - skipped_extractions
    success_rate = (successful_extractions / attempted * 100) if attempted else 0.0
    print(
        f"Yearly processing complete: {total} PDFs found, "
        f"{skipped_extractions} skipped (already formatted), "
        f"{successful_extractions} newly formatted, "
        f"{failed_extractions} failed "
        f"(success rate on attempted: {success_rate:.1f}%)"
    )
    print(f"Results saved to: {output_file}")

    return formatted_diagnoses


def validate_yearly_extraction(
    year: int,
    output_folder: Optional[str] = None,
    sample_dates: Optional[List[str]] = None,
) -> None:
    """
    Print a summary of the formatted diagnoses for a given year, including
    a preview of a few sample entries.

    Args:
        year: Year whose extraction should be validated.
        output_folder: Directory containing formatted_diagnoses_{year}.json.
            Defaults to f"formatted_diagnoses_{year}" (matching the
            extractor's default output path). The previous module had a
            hardcoded "formatted_diagnoses_year" path that never matched
            the real output folder; this function has been broken for
            the lifetime of the project until the cleanup.
        sample_dates: Specific dates to print previews for. If None,
            prints the first three dates found in the file.
    """
    if output_folder is None:
        output_folder = f"formatted_diagnoses_{year}"
    results_file = Path(output_folder) / f"formatted_diagnoses_{year}.json"

    if not results_file.exists():
        print(f"ERROR: results file not found: {results_file}")
        return

    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Validation for year {year}: {len(data)} formatted diagnoses")

    if sample_dates:
        dates_to_check = sample_dates
    else:
        dates_to_check = sorted(data.keys())[:3]

    for date_str in dates_to_check:
        if date_str not in data:
            print(f"  {date_str}: not found in results")
            continue
        entry = data[date_str]
        original = entry.get("original_diagnosis", "")
        formatted = entry.get("formatted_diagnosis", {})
        print(f"  Sample {date_str}:")
        print(f"    original length: {len(original)} chars")
        if isinstance(formatted, dict):
            print(f"    formatted sentences present:")
            for key in _SENTENCE_KEYS:
                value = formatted.get(key, "")
                status = "empty" if not value else f"{len(value)} chars"
                print(f"      {key}: {status}")
        else:
            print(f"    formatted diagnosis: {len(str(formatted))} chars (legacy string format)")
            
# ######################################################################
# ##################### postprocessing_romanian.py #####################
# ######################################################################





# import os
# import json
# import pandas as pd
# import re
# from glob import glob
# import re
# import emoji
# from typing import Dict, Tuple, Any

# # Import metric libraries
# try:
#     from rouge_score import rouge_scorer
#     from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
#     from bert_score import score as bert_score
#     from nltk.translate.meteor_score import meteor_score
#     import nltk
#     # Download required NLTK data if not present
#     try:
#         nltk.data.find('tokenizers/punkt')
#     except LookupError:
#         nltk.download('punkt')
#     try:
#         nltk.data.find('corpora/wordnet')
#     except LookupError:
#         nltk.download('wordnet')
# except ImportError as e:
#     print(f"Warning: Some metric libraries not available: {e}")
#     print("Please install: pip install rouge-score bert-score nltk")

# # time related adverbs (in some contexts, these might be relevant)
# time_related_adv = ["azi", "ieri", "mâine", "astăzi"]

# def postprocess_text(text: str, 
#                     lowercase: bool = True,
#                     remove_emojis: bool = False,
#                     remove_punctuation: bool = False,
#                     normalize_whitespace: bool = False,
#                     remove_stopwords: bool = False) -> str:
#     """
#     Preprocess text for more robust comparison
#     """
#     # Remove emojis
#     if remove_emojis:
#         # Replace emojis with empty string
#         text = emoji.replace_emoji(text, replace='')

#     # Normalize whitespace
#     if normalize_whitespace:
#         text = ' '.join(text.split())
    
#     # Lowercase
#     if lowercase:
#         text = text.lower()
    
#     # Remove punctuation (be careful with meteorological data - keep decimal points)
#     if remove_punctuation:
#         # Keep periods that are part of numbers
#         text = re.sub(r'(?<!\d)[^\w\s]|[^\w\s](?!\d)', '', text)

#     # Remove stopwords (spacy version)
#     if remove_stopwords:
#         import spacy

#         # Load Romanian model
#         nlp = spacy.load('ro_core_news_sm')
#         doc = nlp(text)
#         # Filter out stop words and punctuation
#         tokens = [token.text for token in doc if not token.is_stop and token.text in time_related_adv]
#         text = ' '.join(tokens)
    
#     return text.strip()


# def parse_filename(filename: str) -> Tuple[str, str, int]:
#     """Extract model name, date, and past days from filename."""
#     basename = os.path.basename(filename).replace('.json', '')
#     parts = basename.split('_')
    
#     # Find the date part (YYYY-MM-DD format)
#     date_pattern = r'\d{4}-\d{2}-\d{2}'
#     date_idx = None
#     date_str = None
    
#     for i, part in enumerate(parts):
#         if re.match(date_pattern, part):
#             date_idx = i
#             date_str = part
#             break
    
#     if date_idx is None:
#         raise ValueError(f"Could not find date in filename: {filename}")
    
#     # Model name is everything before the date
#     model_name = '_'.join(parts[:date_idx])
    
#     # Past days should be after date, look for pattern ending with "past_days"
#     past_days = None
#     for i in range(date_idx + 1, len(parts)):
#         if parts[i].isdigit() and i + 2 < len(parts) and parts[i + 1] == "past" and parts[i + 2] == "days":
#             past_days = int(parts[i])
#             break
    
#     if past_days is None:
#         # Fallback: look for any number after date
#         for i in range(date_idx + 1, len(parts)):
#             if parts[i].isdigit():
#                 past_days = int(parts[i])
#                 break
    
#     if past_days is None:
#         past_days = 1  # Default value
        
#     return model_name, date_str, past_days

# def extract_response_text(json_data: Dict[str, Any]) -> str:
#     """Extract response text, removing <think> sections."""
#     if 'response' not in json_data:
#         return ""
    
#     response = json_data['response']
#     if isinstance(response, dict):
#         response = response.get('text', '') or response.get('content', '') or str(response)
#     elif not isinstance(response, str):
#         response = str(response)
    
#     # Remove everything between <think> and </think>
#     response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
    
#     # Clean up extra whitespace
#     response = ' '.join(response.split())
    
#     return response

# def calculate_metrics(response_text: str, reference_text: str = None) -> Dict[str, float]:
#     """Calculate various metrics for the response text."""
#     metrics = {}
    
#     # Basic text statistics
#     metrics['length'] = len(response_text)
#     metrics['word_count'] = len(response_text.split())
#     metrics['sentence_count'] = len(re.split(r'[.!?]+', response_text)) - 1
    
#     # If no reference text, return basic metrics
#     if not reference_text:
#         return metrics
    
#     try:
#         # ROUGE scores
#         rouge_scorer_obj = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
#         rouge_scores = rouge_scorer_obj.score(reference_text, response_text)
#         metrics['rouge1_f'] = rouge_scores['rouge1'].fmeasure
#         metrics['rouge1_p'] = rouge_scores['rouge1'].precision
#         metrics['rouge1_r'] = rouge_scores['rouge1'].recall
#         metrics['rouge2_f'] = rouge_scores['rouge2'].fmeasure
#         metrics['rouge2_p'] = rouge_scores['rouge2'].precision  
#         metrics['rouge2_r'] = rouge_scores['rouge2'].recall
#         metrics['rougeL_f'] = rouge_scores['rougeL'].fmeasure
#         metrics['rougeL_p'] = rouge_scores['rougeL'].precision
#         metrics['rougeL_r'] = rouge_scores['rougeL'].recall
#     except Exception as e:
#         print(f"Error calculating ROUGE: {e}")
    
#     try:
#         # BLEU score
#         reference_tokens = reference_text.split()
#         response_tokens = response_text.split()
#         smoothing = SmoothingFunction().method1
#         metrics['bleu'] = sentence_bleu([reference_tokens], response_tokens, smoothing_function=smoothing)
#     except Exception as e:
#         print(f"Error calculating BLEU: {e}")
    
#     try:
#         # BERTScore
#         P, R, F1 = bert_score([response_text], [reference_text], lang='en', verbose=False)
#         metrics['bert_precision'] = P.item()
#         metrics['bert_recall'] = R.item()
#         metrics['bert_f1'] = F1.item()
#     except Exception as e:
#         print(f"Error calculating BERTScore: {e}")
    
#     try:
#         # METEOR score
#         reference_tokens = reference_text.split()
#         response_tokens = response_text.split()
#         metrics['meteor'] = meteor_score([reference_tokens], response_tokens)
#     except Exception as e:
#         print(f"Error calculating METEOR: {e}")
    
#     # Additional semantic metrics
#     try:
#         # Cosine similarity (simple word overlap)
#         ref_words = set(reference_text.lower().split())
#         resp_words = set(response_text.lower().split())
#         intersection = len(ref_words.intersection(resp_words))
#         union = len(ref_words.union(resp_words))
#         metrics['jaccard_similarity'] = intersection / union if union > 0 else 0
        
#         # Coverage metrics
#         metrics['reference_coverage'] = intersection / len(ref_words) if ref_words else 0
#         metrics['response_coverage'] = intersection / len(resp_words) if resp_words else 0
#     except Exception as e:
#         print(f"Error calculating additional metrics: {e}")
    
#     return metrics


# def create_analysis_tables(responses_folder: str, output_date: str, output_past_days: int, 
#                           reference_text: str = None):
#     """
#     Creates 3 tables analyzing LLM responses with various metrics.
    
#     Args:
#         responses_folder: Path to folder containing JSON response files
#         output_date: Date string for output folder structure
#         output_past_days: Number of past days for output folder structure  
#         reference_text: Reference text (ground truth)
#     """
    
#     # Get all JSON files except test_summary
#     json_files = glob(os.path.join(responses_folder, "*.json"))
#     json_files = [f for f in json_files if not os.path.basename(f).startswith("test_summary")]
    
#     if not json_files:
#         print(f"No valid JSON files found in {responses_folder}")
#         return
    
#     print(f"Found {len(json_files)} JSON files to process")
    
#     # Store all data
#     all_data = []
    
#     for json_file in json_files:
#         try:
#             model_name, date, past_days = parse_filename(json_file)
            
#             with open(json_file, 'r', encoding='utf-8') as f:
#                 json_data = json.load(f)
            
#             response_text = extract_response_text(json_data)
            
#             # Postprocess response and reference text
#             response_text = postprocess_text(response_text)
#             reference_text = postprocess_text(reference_text)

#             metrics = calculate_metrics(response_text, reference_text)
            
#             # Store data
#             data_point = {
#                 'model': model_name,
#                 'date': date,
#                 'past_days': past_days,
#                 'filename': os.path.basename(json_file),
#                 'response_text': response_text,
#                 **metrics
#             }
#             all_data.append(data_point)
            
#         except Exception as e:
#             print(f"Error processing {json_file}: {e}")
#             continue
    
#     if not all_data:
#         print("No data was successfully processed")
#         return
    
#     # Convert to DataFrame
#     df = pd.DataFrame(all_data)
    
#     # Get all metric columns (exclude metadata columns)
#     metric_columns = [col for col in df.columns if col not in ['model', 'date', 'past_days', 'filename', 'response_text']]
    
#     print(f"Calculated metrics: {metric_columns}")
    
#     # Create output directory
#     output_dir = os.path.join("results", output_date, f"{output_past_days}_past_days")
#     os.makedirs(output_dir, exist_ok=True)
    
#     # Create tables for each metric
#     for metric in metric_columns:
#         print(f"Creating tables for metric: {metric}")
        
#         # Table 1: Models as columns, past_days as rows
#         pivot_table = df.pivot_table(
#             index='past_days', 
#             columns='model', 
#             values=metric, 
#             aggfunc='mean'
#         )
#         pivot_table.to_csv(os.path.join(output_dir, f"table1_{metric}_models_vs_past_days.csv"))
        
#         # Table 2: Mean per model
#         model_means = df.groupby('model')[metric].agg(['mean', 'std', 'count']).round(4)
#         model_means.to_csv(os.path.join(output_dir, f"table2_{metric}_mean_per_model.csv"))
        
#         # Table 3: Mean per past_days
#         past_days_means = df.groupby('past_days')[metric].agg(['mean', 'std', 'count']).round(4)
#         past_days_means.to_csv(os.path.join(output_dir, f"table3_{metric}_mean_per_past_days.csv"))
    
#     # Create summary tables with all metrics
#     print("Creating summary tables...")
    
#     # Summary by model
#     model_summary = df.groupby('model')[metric_columns].mean().round(4)
#     model_summary.to_csv(os.path.join(output_dir, "summary_by_model.csv"))
    
#     # Summary by past_days  
#     past_days_summary = df.groupby('past_days')[metric_columns].mean().round(4)
#     past_days_summary.to_csv(os.path.join(output_dir, "summary_by_past_days.csv"))
    
#     # Overall summary statistics
#     overall_summary = df[metric_columns].describe().round(4)
#     overall_summary.to_csv(os.path.join(output_dir, "overall_summary_statistics.csv"))
    
#     # Save raw data for reference
#     df.drop('response_text', axis=1).to_csv(os.path.join(output_dir, "raw_data_summary.csv"), index=False)
    
#     print(f"Analysis complete! Results saved in {output_dir}")
#     print(f"Processed {len(df)} responses from {df['model'].nunique()} models")
#     print(f"Past days range: {df['past_days'].min()} to {df['past_days'].max()}")
    
    



# ##########################################################################
# ##################### postprocessing_romanian_gpt.py #####################
# ##########################################################################





# import os
# import json
# import pandas as pd
# import re
# from glob import glob
# import re
# import emoji
# from typing import Dict, Tuple, Any

# # Import metric libraries
# try:
#     from rouge_score import rouge_scorer
#     from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
#     from bert_score import score as bert_score
#     from nltk.translate.meteor_score import meteor_score
#     import nltk
#     # Download required NLTK data if not present
#     try:
#         nltk.data.find('tokenizers/punkt')
#     except LookupError:
#         nltk.download('punkt')
#     try:
#         nltk.data.find('corpora/wordnet')
#     except LookupError:
#         nltk.download('wordnet')
# except ImportError as e:
#     print(f"Warning: Some metric libraries not available: {e}")
#     print("Please install: pip install rouge-score bert-score nltk")

# # time related adverbs (in some contexts, these might be relevant)
# time_related_adv = ["azi", "ieri", "mâine", "astăzi"]

# def postprocess_text(text: str, 
#                     lowercase: bool = True,
#                     remove_emojis: bool = False,
#                     remove_punctuation: bool = False,
#                     normalize_whitespace: bool = False,
#                     remove_stopwords: bool = False) -> str:
#     """
#     Preprocess text for more robust comparison
#     """
#     # Remove emojis
#     if remove_emojis:
#         # Replace emojis with empty string
#         text = emoji.replace_emoji(text, replace='')

#     # Normalize whitespace
#     if normalize_whitespace:
#         text = ' '.join(text.split())
    
#     # Lowercase
#     if lowercase:
#         text = text.lower()
    
#     # Remove punctuation (be careful with meteorological data - keep decimal points)
#     if remove_punctuation:
#         # Keep periods that are part of numbers
#         text = re.sub(r'(?<!\d)[^\w\s]|[^\w\s](?!\d)', '', text)

#     # Remove stopwords (spacy version)
#     if remove_stopwords:
#         import spacy

#         # Load Romanian model
#         nlp = spacy.load('ro_core_news_sm')
#         doc = nlp(text)
#         # Filter out stop words and punctuation
#         tokens = [token.text for token in doc if not token.is_stop and token.text in time_related_adv]
#         text = ' '.join(tokens)
    
#     return text.strip()


# def parse_filename(filename: str) -> Tuple[str, str, int]:
#     """Extract model name, date, and past days from filename."""
#     basename = os.path.basename(filename).replace('.json', '')
#     parts = basename.split('_')
    
#     # Find the date part (YYYY-MM-DD format)
#     date_pattern = r'\d{4}-\d{2}-\d{2}'
#     date_idx = None
#     date_str = None
    
#     for i, part in enumerate(parts):
#         if re.match(date_pattern, part):
#             date_idx = i
#             date_str = part
#             break
    
#     if date_idx is None:
#         raise ValueError(f"Could not find date in filename: {filename}")
    
#     # Model name is everything before the date
#     model_name = '_'.join(parts[:date_idx])
    
#     # Past days should be after date, look for pattern ending with "past_days"
#     past_days = None
#     for i in range(date_idx + 1, len(parts)):
#         if parts[i].isdigit() and i + 2 < len(parts) and parts[i + 1] == "past" and parts[i + 2] == "days":
#             past_days = int(parts[i])
#             break
    
#     if past_days is None:
#         # Fallback: look for any number after date
#         for i in range(date_idx + 1, len(parts)):
#             if parts[i].isdigit():
#                 past_days = int(parts[i])
#                 break
    
#     if past_days is None:
#         past_days = 1  # Default value
        
#     return model_name, date_str, past_days

# def extract_response_text(json_data: Dict[str, Any]) -> str:
#     """Extract response text, removing <think> sections and extracting only structured sentences."""
#     if 'response' not in json_data:
#         return ""
    
#     response = json_data['response']
#     if isinstance(response, dict):
#         response = response.get('text', '') or response.get('content', '') or str(response)
#     elif not isinstance(response, str):
#         response = str(response)
    
#     # Remove everything between <think> and </think>
#     response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
    
#     # Extract structured sentences (PRIMA PROPOZIȚIE, A DOUA PROPOZIȚIE, etc.)
#     sentence_patterns = [
#         r'PRIMA PROPOZIȚ?I[AE]:\s*([^.]*\.?)',
#         r'A DOUA PROPOZIȚ?I[AE]:\s*([^.]*\.?)',
#         r'A TREIA PROPOZIȚ?I[AE]:\s*([^.]*\.?)',
#         r'A PATRA PROPOZIȚ?I[AE]:\s*([^.]*\.?)',
#         r'PROPOZIȚ?IA FINAL[AĂ]:\s*([^.]*\.?)'
#     ]
    
#     extracted_sentences = []
    
#     for pattern in sentence_patterns:
#         matches = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)
#         if matches:
#             # Get the longest match (in case of multiple matches)
#             sentence = max(matches, key=len).strip()
#             if sentence and sentence != '-':  # Skip empty or dash-only sentences
#                 # Add the prefix back to maintain structure
#                 if 'PRIMA' in pattern:
#                     extracted_sentences.append(f"PRIMA PROPOZIȚIE: {sentence}")
#                 elif 'A DOUA' in pattern:
#                     extracted_sentences.append(f"A DOUA PROPOZIȚIE: {sentence}")
#                 elif 'A TREIA' in pattern:
#                     extracted_sentences.append(f"A TREIA PROPOZIȚIE: {sentence}")
#                 elif 'A PATRA' in pattern:
#                     extracted_sentences.append(f"A PATRA PROPOZIȚIE: {sentence}")
#                 elif 'FINAL' in pattern:
#                     extracted_sentences.append(f"PROPOZIȚIA FINALĂ: {sentence}")
    
#     # Join extracted sentences
#     if extracted_sentences:
#         result = ' '.join(extracted_sentences)
#     else:
#         # Fallback: if no structured sentences found, clean up the response
#         result = ' '.join(response.split())
    
#     return result

# def load_reference_text(date: str) -> str:
#     """Load reference text from formatted diagnoses JSON file for the given date."""
#     # Extract year from date
#     year = date.split('-')[0]
    
#     # Construct path to formatted diagnoses file
#     file_path = f"formatted_diagnoses_{year}/formatted_diagnoses_{year}.json"
    
#     try:
#         with open(file_path, 'r', encoding='utf-8') as f:
#             data = json.load(f)
        
#         # Get the reference text for the specific date
#         if date in data:
#             formatted_diagnosis = data[date].get('formatted_diagnosis', {})
#             reference_text = formatted_diagnosis.get('PRIMA_PROPOZITIE', '')
            
#             if reference_text:
#                 print(f"✅ Loaded reference text for {date}")
#                 return reference_text
#             else:
#                 print(f"⚠️ No PRIMA_PROPOZITIE found for {date}")
#                 # Fallback to original diagnosis
#                 return data[date].get('original_diagnosis', '')
#         else:
#             print(f"⚠️ Date {date} not found in formatted diagnoses")
#             return ""
            
#     except FileNotFoundError:
#         print(f"❌ Could not find formatted diagnoses file: {file_path}")
#         return ""
#     except Exception as e:
#         print(f"❌ Error loading reference text: {str(e)}")
#         return ""

# def calculate_metrics(response_text: str, reference_text: str = None) -> Dict[str, float]:
#     """Calculate various metrics for the response text."""
#     metrics = {}
    
#     # Basic text statistics
#     metrics['length'] = len(response_text)
#     metrics['word_count'] = len(response_text.split())
#     metrics['sentence_count'] = len(re.split(r'[.!?]+', response_text)) - 1
    
#     # If no reference text, return basic metrics
#     if not reference_text:
#         return metrics
    
#     try:
#         # ROUGE scores
#         rouge_scorer_obj = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
#         rouge_scores = rouge_scorer_obj.score(reference_text, response_text)
#         metrics['rouge1_f'] = rouge_scores['rouge1'].fmeasure
#         metrics['rouge1_p'] = rouge_scores['rouge1'].precision
#         metrics['rouge1_r'] = rouge_scores['rouge1'].recall
#         metrics['rouge2_f'] = rouge_scores['rouge2'].fmeasure
#         metrics['rouge2_p'] = rouge_scores['rouge2'].precision  
#         metrics['rouge2_r'] = rouge_scores['rouge2'].recall
#         metrics['rougeL_f'] = rouge_scores['rougeL'].fmeasure
#         metrics['rougeL_p'] = rouge_scores['rougeL'].precision
#         metrics['rougeL_r'] = rouge_scores['rougeL'].recall
#     except Exception as e:
#         print(f"Error calculating ROUGE: {e}")
    
#     try:
#         # BLEU score
#         reference_tokens = reference_text.split()
#         response_tokens = response_text.split()
#         smoothing = SmoothingFunction().method1
#         metrics['bleu'] = sentence_bleu([reference_tokens], response_tokens, smoothing_function=smoothing)
#     except Exception as e:
#         print(f"Error calculating BLEU: {e}")
    
#     try:
#         # BERTScore
#         P, R, F1 = bert_score([response_text], [reference_text], lang='en', verbose=False)
#         metrics['bert_precision'] = P.item()
#         metrics['bert_recall'] = R.item()
#         metrics['bert_f1'] = F1.item()
#     except Exception as e:
#         print(f"Error calculating BERTScore: {e}")
    
#     try:
#         # METEOR score
#         reference_tokens = reference_text.split()
#         response_tokens = response_text.split()
#         metrics['meteor'] = meteor_score([reference_tokens], response_tokens)
#     except Exception as e:
#         print(f"Error calculating METEOR: {e}")
    
#     # Additional semantic metrics
#     try:
#         # Cosine similarity (simple word overlap)
#         ref_words = set(reference_text.lower().split())
#         resp_words = set(response_text.lower().split())
#         intersection = len(ref_words.intersection(resp_words))
#         union = len(ref_words.union(resp_words))
#         metrics['jaccard_similarity'] = intersection / union if union > 0 else 0
        
#         # Coverage metrics
#         metrics['reference_coverage'] = intersection / len(ref_words) if ref_words else 0
#         metrics['response_coverage'] = intersection / len(resp_words) if resp_words else 0
#     except Exception as e:
#         print(f"Error calculating additional metrics: {e}")
    
#     return metrics


# def create_analysis_tables_gpt(responses_folder: str, output_date: str, output_past_days: int, 
#                           reference_text: str = None):
#     """
#     Creates 3 tables analyzing LLM responses with various metrics.
    
#     Args:
#         responses_folder: Path to folder containing JSON response files
#         output_date: Date string for output folder structure
#         output_past_days: Number of past days for output folder structure  
#         reference_text: Reference text (ground truth)
#     """
    
#     # Get all JSON files except test_summary
#     json_files = glob(os.path.join(responses_folder, "*.json"))
#     json_files = [f for f in json_files if not os.path.basename(f).startswith("test_summary")]
    
#     if not json_files:
#         print(f"No valid JSON files found in {responses_folder}")
#         return
    
#     print(f"Found {len(json_files)} JSON files to process")
    
#     # Store all data
#     all_data = []
    
#     for json_file in json_files:
#         try:
#             model_name, date, past_days = parse_filename(json_file)
            
#             with open(json_file, 'r', encoding='utf-8') as f:
#                 json_data = json.load(f)
            
#             response_text = extract_response_text(json_data)
            
#             # Postprocess response and reference text
#             response_text = postprocess_text(response_text)
#             processed_reference_text = postprocess_text(reference_text) if reference_text else None

#             metrics = calculate_metrics(response_text, processed_reference_text)
            
#             # Store data
#             data_point = {
#                 'model': model_name,
#                 'date': date,
#                 'past_days': past_days,
#                 'filename': os.path.basename(json_file),
#                 'response_text': response_text,
#                 **metrics
#             }
#             all_data.append(data_point)
            
#         except Exception as e:
#             print(f"Error processing {json_file}: {e}")
#             continue
    
#     if not all_data:
#         print("No data was successfully processed")
#         return
    
#     # Convert to DataFrame
#     df = pd.DataFrame(all_data)
    
#     # Get all metric columns (exclude metadata columns)
#     metric_columns = [col for col in df.columns if col not in ['model', 'date', 'past_days', 'filename', 'response_text']]
    
#     print(f"Calculated metrics: {metric_columns}")
    
#     # Create output directory
#     output_dir = os.path.join("results", output_date, f"{output_past_days}_past_days")
#     os.makedirs(output_dir, exist_ok=True)
    
#     # Create tables for each metric
#     for metric in metric_columns:
#         print(f"Creating tables for metric: {metric}")
        
#         # Table 1: Models as columns, past_days as rows
#         pivot_table = df.pivot_table(
#             index='past_days', 
#             columns='model', 
#             values=metric, 
#             aggfunc='mean'
#         )
#         pivot_table.to_csv(os.path.join(output_dir, f"table1_{metric}_models_vs_past_days.csv"))
        
#         # Table 2: Mean per model
#         model_means = df.groupby('model')[metric].agg(['mean', 'std', 'count']).round(4)
#         model_means.to_csv(os.path.join(output_dir, f"table2_{metric}_mean_per_model.csv"))
        
#         # Table 3: Mean per past_days
#         past_days_means = df.groupby('past_days')[metric].agg(['mean', 'std', 'count']).round(4)
#         past_days_means.to_csv(os.path.join(output_dir, f"table3_{metric}_mean_per_past_days.csv"))
    
#     # Create summary tables with all metrics
#     print("Creating summary tables...")
    
#     # Summary by model
#     model_summary = df.groupby('model')[metric_columns].mean().round(4)
#     model_summary.to_csv(os.path.join(output_dir, "summary_by_model.csv"))
    
#     # Summary by past_days  
#     past_days_summary = df.groupby('past_days')[metric_columns].mean().round(4)
#     past_days_summary.to_csv(os.path.join(output_dir, "summary_by_past_days.csv"))
    
#     # Overall summary statistics
#     overall_summary = df[metric_columns].describe().round(4)
#     overall_summary.to_csv(os.path.join(output_dir, "overall_summary_statistics.csv"))
    
#     # Save raw data for reference
#     df.drop('response_text', axis=1).to_csv(os.path.join(output_dir, "raw_data_summary.csv"), index=False)
    
#     print(f"Analysis complete! Results saved in {output_dir}")
#     print(f"Processed {len(df)} responses from {df['model'].nunique()} models")
#     print(f"Past days range: {df['past_days'].min()} to {df['past_days'].max()}")


"""
Response evaluation for the meteorological diagnosis pipeline.

Computes per-response and aggregate metrics against reference diagnoses, and
provides the shared helpers used by llm_as_a_judge.py.

Two evaluation entry points are exposed, one per prompting track:

    create_analysis_tables       PDF-context track.
                                 Reference text is typically the raw ANM
                                 PDF diagnosis passed in directly. Uses
                                 loose response extraction.

    create_analysis_tables_gpt   GPT-CoT track.
                                 Reference text is typically the
                                 gpt-5-mini-formatted PRIMA_PROPOZITIE
                                 loaded via load_reference_text(). Uses
                                 strict structured-sentence extraction.

Both functions receive the reference text as an argument. The choice of
reference source (raw PDF vs gpt-5-mini reformatted) is a methodology
decision made at the call site and is intentionally not unified here,
because doing so would hide the circular "evaluating gpt-5-mini outputs
against gpt-5-mini reformatting" concern.

Public API (signatures unchanged from the previous postprocessing_romanian.py
and postprocessing_romanian_gpt.py modules):

    create_analysis_tables        build metric tables for the PDF-context track
    create_analysis_tables_gpt    build metric tables for the GPT-CoT track
    load_reference_text           load first-sentence reference for a date
    extract_response_text         strict structured-sentence extraction
                                  (used by llm_as_a_judge.py)
    parse_filename                extract (model_name, date, past_days)
                                  from a response filename
"""

import json
import os
import re
import unicodedata
from glob import glob
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Metric library imports
# ---------------------------------------------------------------------------

try:
    import nltk
    from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
    from nltk.translate.meteor_score import meteor_score
    from rouge_score import rouge_scorer
    from bert_score import score as bert_score_fn
    _METRICS_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: metric libraries unavailable ({e}); install rouge-score bert-score nltk")
    _METRICS_AVAILABLE = False

# Make sure the NLTK resources needed for METEOR tokenization are present.
if _METRICS_AVAILABLE:
    for _resource, _path in (("punkt", "tokenizers/punkt"), ("wordnet", "corpora/wordnet")):
        try:
            nltk.data.find(_path)
        except LookupError:
            try:
                nltk.download(_resource, quiet=True)
            except Exception as _e:
                print(f"WARNING: failed to download NLTK resource {_resource}: {_e}")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# BERTScore model. xlm-roberta-large is the strongest multilingual encoder
# with Romanian in its pre-training distribution, and it fits comfortably
# within an RTX A6000's 48 GB at batch size 64 (peak ~15 GB for typical
# short Romanian diagnoses). Increase _BERTSCORE_BATCH_SIZE if you have
# much larger response sets and want faster evaluation, or drop it to 32
# if you ever run evaluation alongside Ollama inference on the same GPU.
#
# WARNING: the previous pipeline used lang='en' here, which routed BERTScore
# to an English roberta-large encoder applied to Romanian text. Every
# BERTScore number in the previous project report was computed that way and
# is not meaningful; numbers produced by this module will differ from the
# report's numbers and cannot be compared to them directly.
_BERTSCORE_MODEL_TYPE = "xlm-roberta-large"
_BERTSCORE_BATCH_SIZE = 64

# Split metric columns into basic stats (included in raw_data_summary.csv
# only) and quality metrics (pivoted into per-metric tables).
_BASIC_STATS_KEYS: Tuple[str, ...] = ("length", "word_count", "sentence_count")
_QUALITY_METRIC_KEYS: Tuple[str, ...] = (
    "rouge1_f", "rouge1_p", "rouge1_r",
    "rouge2_f", "rouge2_p", "rouge2_r",
    "rougeL_f", "rougeL_p", "rougeL_r",
    "bleu",
    "bert_precision", "bert_recall", "bert_f1",
    "meteor",
    "jaccard_similarity", "reference_coverage", "response_coverage",
)

# Filename parsing. Expected shapes (seed is optional, used only for
# multi-seed variance-estimation runs):
#     <model_name>_<YYYY-MM-DD>_<N>_past_days.json
#     <model_name>_<YYYY-MM-DD>_<N>_past_days_seed<M>.json
# Model name may contain letters, digits, underscores, dots, colons, hyphens.
_FILENAME_RE = re.compile(
    r"^(?P<model>.+?)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<past_days>\d+)_past_days"
    r"(?:_seed(?P<seed>\d+))?$"
)

# Strict structured-sentence extraction. The capture group is [^\n]* to
# capture the entire same-line content after each marker. The previous
# pipeline used [^.]*\.? here, which silently truncated sentences at the
# first decimal point, corrupting every metric for responses containing
# numbers like "31.5°C".
_STRUCTURED_SENTENCE_RE: Dict[str, "re.Pattern"] = {
    "PRIMA PROPOZIȚIE":   re.compile(r"PRIMA PROPOZIȚ?I[AE]:\s*([^\n]*)",    re.IGNORECASE),
    "A DOUA PROPOZIȚIE":  re.compile(r"A DOUA PROPOZIȚ?I[AE]:\s*([^\n]*)",   re.IGNORECASE),
    "A TREIA PROPOZIȚIE": re.compile(r"A TREIA PROPOZIȚ?I[AE]:\s*([^\n]*)",  re.IGNORECASE),
    "A PATRA PROPOZIȚIE": re.compile(r"A PATRA PROPOZIȚ?I[AE]:\s*([^\n]*)",  re.IGNORECASE),
    "PROPOZIȚIA FINALĂ":  re.compile(r"PROPOZIȚ?IA FINAL[AĂ]:\s*([^\n]*)",   re.IGNORECASE),
}

_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# Diacritic folding: legacy cedilla forms -> modern comma-below forms.
# Applied after NFC normalization so it works regardless of whether the
# input used composed or decomposed Unicode.
_DIACRITIC_FOLD_MAP = str.maketrans({
    "ş": "ș",  # U+015F -> U+0219
    "Ş": "Ș",
    "ţ": "ț",  # U+0163 -> U+021B
    "Ţ": "Ț",
})


# ---------------------------------------------------------------------------
# Romanian stopword handling
# ---------------------------------------------------------------------------

# Time-related words to PRESERVE even when stopword removal is enabled. These
# are semantically critical for meteorological diagnoses: 'azi' vs 'ieri' is
# the difference between today's and yesterday's data.
_PRESERVED_TIME_WORDS = frozenset([
    "azi", "astăzi", "ieri", "alaltăieri", "mâine", "poimâine",
    "acum", "atunci", "înainte", "după", "apoi",
    "dimineață", "dimineața", "prânz", "seara", "seară",
    "noapte", "noaptea", "ziua", "zi",
])

# Hardcoded Romanian stopword fallback, used when spacy's ro_core_news_sm
# is not installed. Covers articles, prepositions, conjunctions, pronouns,
# auxiliaries, and high-frequency function words. Not meant to be exhaustive;
# spacy's list is larger and more accurate.
_FALLBACK_STOPWORDS = frozenset([
    # Articles and determiners
    "a", "al", "ale", "alor", "ai", "alei", "alui",
    "cel", "cea", "cei", "cele", "celor", "celui",
    "un", "o", "unei", "unui", "unor", "niște",
    "acel", "acea", "acei", "acele", "acest", "această", "acești", "aceste",
    "același", "aceeași", "aceiași", "aceleași",
    # Prepositions
    "de", "la", "în", "pe", "cu", "din", "până", "pentru", "prin",
    "sub", "peste", "lângă", "despre", "între", "către", "spre",
    "fără", "dintre", "printre",
    # Conjunctions
    "și", "dar", "sau", "ori", "ci", "iar", "însă", "deci",
    "că", "să", "dacă", "deși", "fiindcă", "întrucât",
    "precum", "astfel", "decât", "cât",
    # Pronouns
    "eu", "tu", "el", "ea", "noi", "voi", "ei", "ele",
    "mine", "tine", "sine", "mie", "ție", "lui", "nouă", "vouă", "lor",
    "mă", "te", "se", "ne", "vă", "le", "li",
    "meu", "mea", "mei", "mele", "tău", "ta", "tăi", "tale",
    "său", "sa", "săi", "sale",
    "nostru", "noastră", "noștri", "noastre",
    "vostru", "voastră", "voștri", "voastre",
    "cine", "ce", "care", "cui", "cărei", "cărui", "căror",
    "altul", "alta", "alții", "altele", "altcineva", "altceva",
    # Verbs (auxiliaries, copulas, modals, common forms)
    "sunt", "ești", "este", "e", "suntem", "sunteți",
    "eram", "erai", "era", "erați", "erau",
    "fi", "fie", "fost", "fiind",
    "am", "ai", "are", "avem", "aveți", "au",
    "aveam", "aveai", "avea", "aveați", "aveau",
    "avut", "având",
    "vei", "va", "vom", "veți", "vor",
    "aș", "ar", "ați",
    "trebui", "poate", "putea", "pot",
    # Common adverbs and particles
    "nu", "mai", "doar", "cam", "foarte", "prea", "chiar",
    "numai", "tot", "toate", "toți", "toată",
    "oare", "totuși", "mereu", "uneori",
    "aproape", "cumva", "oarecum",
])


# Module-level cache for spacy. Sentinel values:
#   None  = not yet attempted
#   False = attempted and unavailable (use fallback)
#   <obj> = spacy.Language instance
_spacy_nlp: Any = None


def _get_romanian_stopwords() -> frozenset:
    """
    Resolve the Romanian stopword set, preferring spacy's ro_core_news_sm and
    falling back to _FALLBACK_STOPWORDS if spacy or the model is unavailable.

    _PRESERVED_TIME_WORDS is subtracted from the final set so time adverbs
    like 'azi', 'ieri', 'mâine' are never stripped, regardless of source.
    """
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            _spacy_nlp = spacy.load("ro_core_news_sm")
            print("Loaded spacy ro_core_news_sm for stopword removal")
        except (ImportError, OSError) as e:
            print(
                f"WARNING: spacy ro_core_news_sm unavailable ({e}); "
                "using built-in fallback stopword list"
            )
            _spacy_nlp = False

    if _spacy_nlp is False:
        base = _FALLBACK_STOPWORDS
    else:
        base = frozenset(_spacy_nlp.Defaults.stop_words)

    return base - _PRESERVED_TIME_WORDS


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def _normalize_romanian(text: str) -> str:
    """
    NFC-normalize and fold legacy cedilla diacritics to modern comma-below
    forms, so that 'ați' and 'aţi' compare equal at the character level.
    """
    return unicodedata.normalize("NFC", text).translate(_DIACRITIC_FOLD_MAP)


def _postprocess_text(
    text: str,
    *,
    lowercase: bool = True,
    remove_stopwords: bool = True,
) -> str:
    """
    Normalize text for metric comparison.

    Steps, in order:
      1. NFC normalization and Romanian cedilla-to-comma-below folding
      2. Whitespace normalization
      3. Lowercasing (optional)
      4. Stopword removal with time-word preservation (optional)

    Stopword removal is enabled by default for use with n-gram-based metrics
    (ROUGE, BLEU, METEOR, Jaccard), because function words dominate n-gram
    overlap and wash out the semantic signal. Callers that want the full
    text for contextual-embedding metrics like BERTScore should pass
    remove_stopwords=False.
    """
    if not text:
        return ""

    text = _normalize_romanian(text)
    text = " ".join(text.split())

    if lowercase:
        text = text.lower()

    if remove_stopwords:
        stopwords = _get_romanian_stopwords()
        # Whitespace tokenization is sufficient here: the stopword set is
        # already at word granularity, so we don't need spacy's linguistic
        # tokenizer for the filter step.
        text = " ".join(t for t in text.split() if t not in stopwords)

    return text.strip()


# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------

def parse_filename(filename: str) -> Tuple[str, str, int]:
    """
    Extract (model_name, date, past_days) from a response filename of the
    form '<model_name>_<YYYY-MM-DD>_<N>_past_days[_seed<M>].json'.

    The optional _seed<M> suffix is recognized but not returned (for that,
    use parse_filename_with_seed). This function preserves the original
    3-tuple contract used by existing call sites in judge_evaluation.py
    and in the analysis pipelines.

    On parse failure, returns a best-effort result with past_days=1 and
    prints a WARNING so malformed filenames do not halt bulk processing
    silently. Raises ValueError only if no date can be found at all.
    """
    basename = os.path.basename(filename).replace(".json", "")

    m = _FILENAME_RE.match(basename)
    if m is not None:
        return m.group("model"), m.group("date"), int(m.group("past_days"))

    # Fallback: find any YYYY-MM-DD in the name, take the prefix as the model.
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", basename)
    if date_match is None:
        raise ValueError(f"Could not find date in filename: {filename}")

    date_str = date_match.group(0)
    model_name = basename[: date_match.start()].rstrip("_")
    print(
        f"WARNING: could not parse past_days from '{basename}'; "
        f"defaulting to past_days=1"
    )
    return model_name, date_str, 1


def parse_filename_with_seed(
    filename: str,
) -> Tuple[str, str, int, Optional[int]]:
    """
    Same as parse_filename but also returns the seed if present in the
    filename (via an optional '_seed<M>' suffix). Files saved by
    single-seed runs return seed=None; files saved by multi-seed runs
    return the integer seed used for that response.

    Use this variant when aggregating over the seed dimension for
    variance estimation.
    """
    basename = os.path.basename(filename).replace(".json", "")
    m = _FILENAME_RE.match(basename)
    if m is not None:
        seed_str = m.group("seed")
        seed_val = int(seed_str) if seed_str is not None else None
        return m.group("model"), m.group("date"), int(m.group("past_days")), seed_val

    # Fallback path (no date or mangled filename): delegate to parse_filename.
    model, date_str, past_days = parse_filename(filename)
    return model, date_str, past_days, None


# ---------------------------------------------------------------------------
# Response extraction
# ---------------------------------------------------------------------------

def extract_response_text(json_data: Dict[str, Any]) -> str:
    """
    Strict structured-sentence extraction.

    Looks for the five structured markers
    (PRIMA PROPOZIȚIE: ... PROPOZIȚIA FINALĂ: ...) that the test-model system
    prompt asks for, extracts only the content of those sentences, and joins
    them with spaces. Falls back to whitespace-normalized full text if no
    markers are found.

    The raw response is first cleaned of <think>...</think> reasoning tags so
    that chain-of-thought text from reasoning models (phi4-reasoning,
    magistral) does not pollute the metrics.

    This is the public extractor used by llm_as_a_judge.py and by
    create_analysis_tables_gpt.
    """
    response = _get_response_field(json_data)
    if not response:
        return ""

    response = _THINK_TAG_RE.sub("", response)

    extracted: List[str] = []
    for label, pattern in _STRUCTURED_SENTENCE_RE.items():
        matches = pattern.findall(response)
        if not matches:
            continue
        sentence = max(matches, key=len).strip()
        if not sentence or sentence == "-":
            continue
        extracted.append(f"{label}: {sentence}")

    if extracted:
        return " ".join(extracted)

    # No structured markers found - fall back to whitespace-normalized full text.
    return " ".join(response.split())


def _extract_response_text_loose(json_data: Dict[str, Any]) -> str:
    """
    Loose response extraction: strip <think> tags and normalize whitespace,
    but do not require the structured sentence format.

    Used by create_analysis_tables (the PDF-context track), because responses
    in that track are compared against raw ANM PDF text which itself is not
    in the structured format.
    """
    response = _get_response_field(json_data)
    if not response:
        return ""
    response = _THINK_TAG_RE.sub("", response)
    return " ".join(response.split())


def _get_response_field(json_data: Dict[str, Any]) -> str:
    """Extract the 'response' field from a response JSON, tolerating shape."""
    if "response" not in json_data:
        return ""
    response = json_data["response"]
    if isinstance(response, dict):
        return response.get("text") or response.get("content") or str(response)
    if not isinstance(response, str):
        return str(response)
    return response


# ---------------------------------------------------------------------------
# Reference text loader
# ---------------------------------------------------------------------------

def load_reference_text(date: str) -> str:
    """
    Load the first-sentence reference text for a date from
    formatted_diagnoses_{year}/formatted_diagnoses_{year}.json.

    IMPORTANT on the name: despite being called 'load_reference_text', this
    returns ONLY the PRIMA_PROPOZITIE field of the structured diagnosis, not
    the full five-sentence reference. The name is kept for API compatibility
    with existing call sites in main.py and llama_finetuning_pipeline.py. If
    you need the full reference, build a separate loader rather than changing
    this one.

    Returns an empty string on failure. If PRIMA_PROPOZITIE is missing but
    the date exists in the JSON, falls back to original_diagnosis with a
    warning.
    """
    year = date.split("-")[0]
    file_path = Path(f"formatted_diagnoses_{year}/formatted_diagnoses_{year}.json")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: formatted diagnoses file not found: {file_path}")
        return ""
    except Exception as e:
        print(f"ERROR loading formatted diagnoses from {file_path}: {e}")
        return ""

    if date not in data:
        print(f"WARNING: date {date} not found in {file_path}")
        return ""

    formatted = data[date].get("formatted_diagnosis", {})
    first_sentence = formatted.get("PRIMA_PROPOZITIE", "")
    if first_sentence:
        return first_sentence

    print(f"WARNING: no PRIMA_PROPOZITIE for {date}, falling back to original_diagnosis")
    return data[date].get("original_diagnosis", "")


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def _track_error(
    error_counts: Dict[str, int],
    first_error_messages: Dict[str, str],
    metric_name: str,
    exception: Exception,
) -> None:
    """
    Track per-metric failures. Prints the first exception encountered per
    metric, then silently increments a counter for subsequent failures so
    logs are not spammed.
    """
    if error_counts[metric_name] == 0:
        print(f"WARNING: first {metric_name} failure: {exception}")
        first_error_messages[metric_name] = str(exception)
    error_counts[metric_name] += 1


def _calculate_non_bert_metrics(
    response_filtered: str,
    reference_filtered: str,
    response_full: str,
    error_counts: Dict[str, int],
    first_error_messages: Dict[str, str],
) -> Dict[str, float]:
    """
    Compute ROUGE / BLEU / METEOR / Jaccard on stopword-FILTERED text and
    length-based basic stats on FULL text. BERTScore is computed separately
    in a batched call by _compute_bertscore_batched.
    """
    metrics: Dict[str, float] = {
        "length": len(response_full),
        "word_count": len(response_full.split()),
        "sentence_count": max(0, len(re.split(r"[.!?]+", response_full)) - 1),
    }

    if not reference_filtered or not _METRICS_AVAILABLE:
        return metrics

    # ROUGE
    try:
        scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
        rouge_scores = scorer.score(reference_filtered, response_filtered)
        for key in ("rouge1", "rouge2", "rougeL"):
            metrics[f"{key}_f"] = rouge_scores[key].fmeasure
            metrics[f"{key}_p"] = rouge_scores[key].precision
            metrics[f"{key}_r"] = rouge_scores[key].recall
    except Exception as e:
        _track_error(error_counts, first_error_messages, "rouge", e)

    # BLEU
    try:
        ref_tokens = reference_filtered.split()
        resp_tokens = response_filtered.split()
        smoothing = SmoothingFunction().method1
        metrics["bleu"] = sentence_bleu([ref_tokens], resp_tokens, smoothing_function=smoothing)
    except Exception as e:
        _track_error(error_counts, first_error_messages, "bleu", e)

    # METEOR
    try:
        ref_tokens = reference_filtered.split()
        resp_tokens = response_filtered.split()
        metrics["meteor"] = meteor_score([ref_tokens], resp_tokens)
    except Exception as e:
        _track_error(error_counts, first_error_messages, "meteor", e)

    # Jaccard and coverage on the same filtered tokenization.
    try:
        ref_words = set(reference_filtered.split())
        resp_words = set(response_filtered.split())
        intersection = len(ref_words & resp_words)
        union = len(ref_words | resp_words)
        metrics["jaccard_similarity"] = intersection / union if union > 0 else 0.0
        metrics["reference_coverage"] = intersection / len(ref_words) if ref_words else 0.0
        metrics["response_coverage"] = intersection / len(resp_words) if resp_words else 0.0
    except Exception as e:
        _track_error(error_counts, first_error_messages, "jaccard", e)

    return metrics


def _compute_bertscore_batched(
    responses_full: List[str],
    references_full: List[str],
    error_counts: Dict[str, int],
    first_error_messages: Dict[str, str],
) -> List[Dict[str, float]]:
    """
    Compute BERTScore for every (response, reference) pair in a single batched
    call using xlm-roberta-large. Operates on FULL text - BERTScore relies on
    contextual embeddings and stopwords provide useful grammatical scaffolding
    that should not be stripped.

    If BERTScore is unavailable or the batched call fails, returns empty
    dicts for every row so downstream pivot generation still works on the
    other metrics.
    """
    n = len(responses_full)
    if n == 0 or not _METRICS_AVAILABLE:
        return [{} for _ in range(n)]

    try:
        P, R, F1 = bert_score_fn(
            responses_full,
            references_full,
            model_type=_BERTSCORE_MODEL_TYPE,
            batch_size=_BERTSCORE_BATCH_SIZE,
            verbose=False,
        )
        return [
            {
                "bert_precision": float(P[i].item()),
                "bert_recall": float(R[i].item()),
                "bert_f1": float(F1[i].item()),
            }
            for i in range(n)
        ]
    except Exception as e:
        _track_error(error_counts, first_error_messages, "bertscore", e)
        return [{} for _ in range(n)]


# ---------------------------------------------------------------------------
# Analysis table generation (shared core)
# ---------------------------------------------------------------------------

def _run_analysis_pipeline(
    responses_folder: str,
    output_date: str,
    output_past_days: int,
    reference_text: str,
    extract_fn: Callable[[Dict[str, Any]], str],
    output_dir: Optional[str] = None,
) -> None:
    """
    Shared core for create_analysis_tables and create_analysis_tables_gpt.
    Walks the responses folder, computes metrics, writes per-metric and
    summary tables to results/{output_date}/{output_past_days}_past_days/
    by default, or to a caller-specified output_dir when provided.
    """
    json_files = [
        f for f in glob(os.path.join(responses_folder, "*.json"))
        if not os.path.basename(f).startswith("test_summary")
    ]
    if not json_files:
        print(f"ERROR: no response JSON files found in {responses_folder}")
        return

    print(f"Found {len(json_files)} response files in {responses_folder}")

    if not reference_text:
        print("WARNING: empty reference text; only basic stats will be computed")

    # Preprocess the reference ONCE outside the loop. Two versions:
    #   - full:     NFC+fold+lower, no stopword removal, for BERTScore
    #   - filtered: same plus stopword removal, for ROUGE/BLEU/METEOR/Jaccard
    reference_full = _postprocess_text(reference_text, remove_stopwords=False)
    reference_filtered = _postprocess_text(reference_text, remove_stopwords=True)

    rows: List[Dict[str, Any]] = []
    responses_full_batch: List[str] = []
    references_full_batch: List[str] = []
    error_counts: Dict[str, int] = {
        "rouge": 0, "bleu": 0, "meteor": 0, "jaccard": 0, "bertscore": 0,
    }
    first_error_messages: Dict[str, str] = {}
    fallback_extractions = 0
    is_strict_extractor = (extract_fn is extract_response_text)

    for json_file in json_files:
        try:
            model_name, file_date, past_days, seed_val = parse_filename_with_seed(json_file)
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            raw_response = extract_fn(json_data)
        except Exception as e:
            print(f"ERROR processing {os.path.basename(json_file)}: {e}")
            continue

        # Detect when the strict extractor fell back to loose (response did
        # not contain any structured sentence markers). Approximate check:
        # the strict extractor's success path always re-emits 'PRIMA PROPOZIȚIE:'
        # or 'PROPOZIȚIA FINALĂ:' prefixes, so their absence strongly implies
        # a fallback.
        if is_strict_extractor and raw_response:
            if ("PRIMA PROPOZIȚIE:" not in raw_response
                    and "PROPOZIȚIA FINALĂ:" not in raw_response):
                fallback_extractions += 1

        response_full = _postprocess_text(raw_response, remove_stopwords=False)
        response_filtered = _postprocess_text(raw_response, remove_stopwords=True)

        row_metrics = _calculate_non_bert_metrics(
            response_filtered=response_filtered,
            reference_filtered=reference_filtered,
            response_full=response_full,
            error_counts=error_counts,
            first_error_messages=first_error_messages,
        )

        rows.append({
            "model": model_name,
            "date": file_date,
            "past_days": past_days,
            "seed": seed_val,  # None for single-seed files, int for multi-seed
            "filename": os.path.basename(json_file),
            "response_text": response_full,
            **row_metrics,
        })
        responses_full_batch.append(response_full)
        references_full_batch.append(reference_full)

    if not rows:
        print("ERROR: no responses were successfully processed")
        return

    # Batched BERTScore over all collected pairs
    if reference_text:
        bert_rows = _compute_bertscore_batched(
            responses_full_batch,
            references_full_batch,
            error_counts,
            first_error_messages,
        )
        for row, bert_metrics in zip(rows, bert_rows):
            row.update(bert_metrics)

    # Summarize extraction fallbacks and metric failures
    if is_strict_extractor and fallback_extractions > 0:
        pct = fallback_extractions / len(rows) * 100
        print(
            f"NOTE: {fallback_extractions}/{len(rows)} responses ({pct:.1f}%) "
            f"fell back to loose extraction (no structured sentence markers found)"
        )
    for metric_name, count in error_counts.items():
        if count > 0:
            print(f"WARNING: {metric_name} failed for {count}/{len(rows)} rows")

    df = pd.DataFrame(rows)
    _write_analysis_tables(df, output_date, output_past_days, output_dir)


def _write_analysis_tables(
    df: pd.DataFrame,
    output_date: str,
    output_past_days: int,
    output_dir: Optional[str] = None,
) -> None:
    """
    Write per-metric pivot tables and summary tables.

    By default, writes to results/{output_date}/{output_past_days}_past_days/
    (the legacy hardcoded location). When output_dir is provided, writes
    directly to that path instead. The caller-provided override lets the
    fine-tuning pipeline send results straight to its own directory tree
    rather than landing in the global results/ folder and being copied.

    Only quality metrics get pivoted into per-metric files; basic length
    stats (length, word_count, sentence_count) are included in
    raw_data_summary.csv for inspection but are not pivoted.

    When multi-seed response files are present (any (model, past_days)
    cell has count > 1 after grouping), also emits std companion files
    for each per-metric pivot and includes a variance_summary.csv listing
    per-cell mean, std, and count across the seed dimension.
    """
    if output_dir is None:
        output_path = Path("results") / output_date / f"{output_past_days}_past_days"
    else:
        output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    quality_columns = [c for c in _QUALITY_METRIC_KEYS if c in df.columns]

    # Detect whether this run has any multi-seed cells. If every (model,
    # past_days) cell has exactly one row, the pivot means and the raw
    # values are identical; no std reporting is useful.
    cell_counts = df.groupby(["model", "past_days"]).size()
    has_multi_seed = (cell_counts > 1).any()

    for metric in quality_columns:
        pivot_mean = df.pivot_table(
            index="past_days", columns="model", values=metric, aggfunc="mean",
        )
        pivot_mean.to_csv(output_path / f"table1_{metric}_models_vs_past_days.csv")

        if has_multi_seed:
            pivot_std = df.pivot_table(
                index="past_days", columns="model", values=metric, aggfunc="std",
            )
            pivot_std.to_csv(output_path / f"table1_{metric}_models_vs_past_days_std.csv")

        per_model = df.groupby("model")[metric].agg(["mean", "std", "count"]).round(4)
        per_model.to_csv(output_path / f"table2_{metric}_mean_per_model.csv")

        per_past_days = df.groupby("past_days")[metric].agg(["mean", "std", "count"]).round(4)
        per_past_days.to_csv(output_path / f"table3_{metric}_mean_per_past_days.csv")

    if quality_columns:
        df.groupby("model")[quality_columns].mean().round(4).to_csv(
            output_path / "summary_by_model.csv"
        )
        df.groupby("past_days")[quality_columns].mean().round(4).to_csv(
            output_path / "summary_by_past_days.csv"
        )
        df[quality_columns].describe().round(4).to_csv(
            output_path / "overall_summary_statistics.csv"
        )

        if has_multi_seed:
            # Per-cell (model, past_days) variance summary across seeds.
            # One row per cell, one column group per quality metric with
            # mean, std, count columns. Designed for plotting error bars.
            variance_summary = df.groupby(
                ["model", "past_days"]
            )[quality_columns].agg(["mean", "std", "count"]).round(4)
            variance_summary.to_csv(output_path / "variance_summary.csv")

    # Raw per-row data (without the full response text, which bloats the CSV)
    raw_columns = (
        ["model", "date", "past_days", "seed", "filename"]
        + list(_BASIC_STATS_KEYS)
        + quality_columns
    )
    raw_columns = [c for c in raw_columns if c in df.columns]
    df[raw_columns].to_csv(output_path / "raw_data_summary.csv", index=False)

    n_models = df["model"].nunique()
    pd_min = df["past_days"].min()
    pd_max = df["past_days"].max()
    seed_desc = ""
    if has_multi_seed and "seed" in df.columns:
        n_seeds = df.dropna(subset=["seed"])["seed"].nunique()
        seed_desc = f", {n_seeds} distinct seeds"
    print(
        f"Analysis tables written to {output_path}: "
        f"{len(df)} responses, {n_models} models, "
        f"past_days {pd_min}..{pd_max}{seed_desc}"
    )


# ---------------------------------------------------------------------------
# Public analysis-table entry points
# ---------------------------------------------------------------------------

def create_analysis_tables(
    responses_folder: str,
    output_date: str,
    output_past_days: int,
    reference_text: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> None:
    """
    Build analysis tables for the PDF-context track.

    The reference_text argument is expected to be the raw ANM PDF diagnosis
    text (typically the first entry from extract_forecasts_sequential). This
    is a lossier comparison than the GPT-CoT track, because the raw PDF text
    is not normalized to the five-sentence structured format, so lexical
    overlap will be systematically lower.

    Uses loose response extraction (strip <think> tags only) rather than
    strict structured-sentence extraction.

    Args:
        output_dir: Optional override for the result file destination. When
            None, files land in results/{output_date}/{output_past_days}_past_days/.
            When provided, files land directly under output_dir. Used by
            the fine-tuning pipeline to send results to its own tree.
    """
    _run_analysis_pipeline(
        responses_folder=responses_folder,
        output_date=output_date,
        output_past_days=output_past_days,
        reference_text=reference_text or "",
        extract_fn=_extract_response_text_loose,
        output_dir=output_dir,
    )


def create_analysis_tables_gpt(
    responses_folder: str,
    output_date: str,
    output_past_days: int,
    reference_text: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> None:
    """
    Build analysis tables for the GPT-CoT track.

    The reference_text argument is expected to be the gpt-5-mini-formatted
    first-sentence reference loaded via load_reference_text(). Note that this
    creates a circular evaluation: responses are compared against text that
    gpt-5-mini itself produced by reformatting the raw ANM diagnoses. This
    methodology choice is inherited from the previous pipeline and preserved
    here; see the project report for discussion.

    Uses strict structured-sentence extraction (extract only the
    'PRIMA PROPOZIȚIE: ... PROPOZIȚIA FINALĂ: ...' blocks) on responses.

    Args:
        output_dir: Optional override for the result file destination. When
            None, files land in results/{output_date}/{output_past_days}_past_days/.
            When provided, files land directly under output_dir. Used by
            the fine-tuning pipeline to send results to its own tree.
    """
    _run_analysis_pipeline(
        responses_folder=responses_folder,
        output_date=output_date,
        output_past_days=output_past_days,
        reference_text=reference_text or "",
        extract_fn=extract_response_text,
        output_dir=output_dir,
    )
    

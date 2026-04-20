# import pandas as pd
# from datetime import datetime, timedelta
# import pdfplumber
# import re
# import os
# import argparse
# from pathlib import Path
# from typing import List, Tuple, Optional

# from prompting.utils.check_data_availability import check_data_availability
# from prompting.utils.input_extraction import (
#     extract_comprehensive_weather_data,
#     extract_forecasts_sequential,
# )
# from prompting.utils.create_prompts import test_prompt_generation
# from prompting.utils.model_select_gui import generate_gui
# from prompting.utils.ollama_calls import download_models_only, test_downloaded_models
# from prompting.utils.postprocessing_romanian import create_analysis_tables
# from prompting.utils.llm_as_a_judge import create_judge_analysis
# from prompting.utils.create_dataset import extract_yearly_diagnoses_and_format, validate_yearly_extraction
# from prompting.utils.create_prompts_gpt import test_prompt_generation_gpt
# from prompting.utils.postprocessing_romanian_gpt import create_analysis_tables_gpt, load_reference_text
# from prompting.utils.judge_analysis_table import generate_judge_analysis_tables

# INITIAL_PAGES = 11
# MULTIPAGE_TABLE = 329 + INITIAL_PAGES
# SINGLE_PAGE_TABLE = 298 + INITIAL_PAGES

# # Define arguments
# parser = argparse.ArgumentParser(description='Process meteorological data from multiple sources')
# parser.add_argument(
#     '--tables',
#     '-tab',
#     action='store_true', 
#     help='Flag to indicate that table codes and meanings should be extracted and saved as CSV'
# )
# parser.add_argument(
#     '--bucharest',
#     '-buc',
#     action='store_true',
#     help='Flag to indicate that only Bucharest data should be extracted and saved'
# )
# parser.add_argument(
#     '--phenomena_codes',
#     '-pc',
#     action='store_true',
#     help='Flag to indicate that weather phenomena should be extracted and added based on table codes'
# )
# parser.add_argument(
#     '--timestamp',
#     '-t',
#     type=str,
#     default=None,
#     required=False,
#     help='Timestamp in yyyy-mm-dd format (e.g., 2024-12-31) to filter data by date'
# )
# parser.add_argument(
#     '--past_days',
#     '-pd',
#     type=int,
#     default=None,
#     required=False,
#     help='Number of past days to include in the data extraction as context for LLMs'
# )
# parser.add_argument(
#     '--select_models',
#     '-sm',
#     action='store_true',
#     help='Flag to indicate that model selection should be performed'
# )
# parser.add_argument(
#     '--n_models',
#     '-n',
#     type=int,
#     default=10,
#     required=False,
#     help='Number of models to select'
# )
# parser.add_argument(
#     '--download_models',
#     '-dm',
#     action='store_true',
#     help='Flag to indicate that models should be downloaded'
# )
# parser.add_argument(
#     '--test_models',
#     '-tm',
#     action='store_true',
#     help='Flag to indicate that downloaded models should be tested'
# )
# parser.add_argument(
#     '--statistical_analysis',
#     '-sa',
#     action='store_true',
#     help='Flag to indicate that statistical analysis should be performed'
# )
# parser.add_argument(
#     '--judge_analysis',
#     '-ja',
#     action='store_true',
#     help='Flag to indicate that LLM as a judge analysis should be performed'
# )
# parser.add_argument(
#     '--judge',
#     type=str,
#     default='gpt-5-mini',
#     required=False,
#     help='Define the judge model to be used for analysis (e.g., gpt-5-mini)'
# )
# parser.add_argument(
#     '--get_test_time_interval',
#     '-interval',
#     default=None,
#     nargs=2, 
#     metavar=('START_TIME', 'END_TIME'), 
#     help='Start and end times in format yyyy-mm-dd'
# )
# parser.add_argument(
#     '--generate_training_dataset_for_year',
#     '-gen_data',
#     type=int,
#     default=None,
#     required=False,
#     help='Flag to indicate that a training dataset should be generated for the specified year'
# )
# parser.add_argument(
#     '--generate_prompts_gpt',
#     '-gen_prompts',
#     action='store_true',
#     help='Flag to indicate that prompts for GPT should be generated'
# )
# parser.add_argument(
#     '--finetune',
#     '-ft',
#     action='store_true',
#     help='Flag to indicate that fine-tuning pipeline should be run'
# )
# parser.add_argument(
#     '--year',
#     '-y',
#     type=int,
#     default=2024,
#     required=False,
#     help='Year for fine-tuning data (default: 2024)'
# )
# parser.add_argument(
#     '--skip_training',
#     '-st',
#     action='store_true',
#     help='Skip training phase and only prepare testing data'
# )
# parser.add_argument(
#     '--skip_testing',
#     '-sk',
#     action='store_true',
#     help='Skip testing phase'
# )
# parser.add_argument(
#     '--batch_size',
#     '-bs',
#     type=int,
#     default=24,
#     help='Batch size for training (default: 24)'
# )
# parser.add_argument(
#     '--zero_shot',
#     '-zs',
#     action='store_true',
#     help='Use zero-shot approach for testing instead of few-shot'
# )
# parser.add_argument(
#     '--compare',
#     action='store_true',
#     help='Compare both few-shot and zero-shot approaches'
# )
# args = parser.parse_args()


# def extract_bucharest_data(path_to_csv_data="date"):
#     """
#     Extract Bucharest meteorological data from Romanian county CSV files.
    
#     Args:
#         path_to_csv_data (str): Path to directory containing CSV files
#     """
    
#     # Create bucuresti folder if it doesn't exist
#     bucuresti_folder = Path(path_to_csv_data) / "bucuresti"
#     bucuresti_folder.mkdir(exist_ok=True)
#     print(f"✓ Created/verified folder: {bucuresti_folder}")
    
#     # List all CSV files in the directory
#     csv_files = [f for f in os.listdir(path_to_csv_data) if f.endswith('.csv')]
    
#     if not csv_files:
#         print(f"❌ No CSV files found in {path_to_csv_data}")
#         return
    
#     print(f"Found {len(csv_files)} CSV files: {csv_files}")
    
#     bucharest_files_created = []
    
#     for csv_file in csv_files:
#         try:
#             print(f"\n--- Processing: {csv_file} ---")
            
#             # Read the CSV file
#             file_path = os.path.join(path_to_csv_data, csv_file)
#             df = pd.read_csv(file_path, encoding='utf-8')
            
#             print(f"Original data shape: {df.shape}")
#             print(f"Columns: {list(df.columns)}")
            
#             # Check if 'Denumire' column exists
#             if 'Denumire' not in df.columns:
#                 print(f"❌ 'Denumire' column not found in {csv_file}")
#                 print(f"Available columns: {list(df.columns)}")
#                 continue
            
#             # Filter for Bucharest data (case insensitive)
#             bucharest_mask = df['Denumire'].str.contains('bucure', case=False, na=False)
#             bucharest_data = df[bucharest_mask].copy()
            
#             print(f"Bucharest data shape: {bucharest_data.shape}")
            
#             if bucharest_data.empty:
#                 print(f"⚠️  No Bucharest data found in {csv_file}")
                
#                 # Show unique values in Denumire column for debugging
#                 unique_locations = df['Denumire'].unique()
#                 print(f"Available locations in file: {unique_locations[:10]}...")  # Show first 10
#                 continue
            
#             # Display Bucharest locations found
#             bucharest_locations = bucharest_data['Denumire'].unique()
#             print(f"✓ Found Bucharest locations: {bucharest_locations}")
            
#             # Create output filename
#             file_name, file_ext = os.path.splitext(csv_file)
#             output_filename = f"{file_name}_Bucuresti{file_ext}"
#             output_path = bucuresti_folder / output_filename
            
#             # Save the filtered data
#             bucharest_data.to_csv(output_path, index=False, encoding='utf-8')
#             print(f"✓ Saved: {output_path}")
            
#             # Show some statistics
#             print(f"  - Total rows: {len(bucharest_data)}")
#             if 'Data' in bucharest_data.columns:
#                 try:
#                     date_range = pd.to_datetime(bucharest_data['Data'])
#                     print(f"  - Date range: {date_range.min()} to {date_range.max()}")
#                 except:
#                     print(f"  - Date column exists but couldn't parse dates")
            
#             bucharest_files_created.append(output_filename)
            
#         except Exception as e:
#             print(f"❌ Error processing {csv_file}: {e}")
#             continue
    
#     # Summary
#     print(f"\n{'='*60}")
#     print(f"EXTRACTION SUMMARY")
#     print(f"{'='*60}")
#     print(f"Total files processed: {len(csv_files)}")
#     print(f"Bucharest files created: {len(bucharest_files_created)}")
#     print(f"Output folder: {bucuresti_folder}")
    
#     if bucharest_files_created:
#         print(f"\nFiles created:")
#         for file in bucharest_files_created:
#             file_path = bucuresti_folder / file
#             if file_path.exists():
#                 file_size = file_path.stat().st_size / 1024  # Size in KB
#                 print(f"  ✓ {file} ({file_size:.1f} KB)")
#     else:
#         print(f"\n⚠️  No Bucharest data files were created.")
#         print(f"   Check if 'Denumire' column contains Bucharest locations.")


# def debug_csv_structure(path_to_csv_data="date"):
#     """
#     Debug function to understand the structure of CSV files and available locations.
#     """
#     csv_files = [f for f in os.listdir(path_to_csv_data) if f.endswith('.csv')]
    
#     print(f"{'='*60}")
#     print(f"CSV FILES DEBUG INFO")
#     print(f"{'='*60}")
    
#     for csv_file in csv_files:
#         try:
#             print(f"\n--- {csv_file} ---")
            
#             file_path = os.path.join(path_to_csv_data, csv_file)
#             df = pd.read_csv(file_path, encoding='utf-8', nrows=5)  # Just first 5 rows for structure
            
#             print(f"Shape: {df.shape}")
#             print(f"Columns: {list(df.columns)}")
            
#             if 'Denumire' in df.columns:
#                 # Read full file to get all unique locations
#                 full_df = pd.read_csv(file_path, encoding='utf-8')
#                 all_locations = full_df['Denumire'].unique()
                
#                 # Look for Bucharest-related locations
#                 bucharest_locations = [loc for loc in all_locations if 'bucure' in str(loc).lower()]
                
#                 print(f"Total unique locations: {len(all_locations)}")
#                 print(f"Bucharest-related locations: {bucharest_locations}")
                
#                 if not bucharest_locations:
#                     print(f"Sample locations: {all_locations[:10]}")
#             else:
#                 print(f"❌ No 'Denumire' column found")
                
#         except Exception as e:
#             print(f"❌ Error reading {csv_file}: {e}")


# def create_manually_cod_table():
#     """
#     Manually extracted data from COD 4677 meteorological table.
#     Creates a CSV with two columns: Cifra de cod, Semnificatia
#     """
    
#     # Manually extracted data from the images
#     data = [
#         # ww= 00-19 section
#         ("00", "Evoluția norilor nu a fost observată sau această evoluție nu a putut fi urmărită"),
#         ("01", "Nori, în ansamblu, în rărire, sau devin mai puțin groși"),
#         ("02", "Starea cerului, în ansamblu, nu s-a schimbat"),
#         ("03", "Nori în formare sau pe cale de a se dezvolta"),
#         ("04", "Vizibilitate redusă din cauza fumului, spre exemplu, focuri de mărăcini sau incendii de pădure, fumuri industriale sau ceață vulcanică"),
#         ("05", "Pâclă"),
#         ("06", "Praf în suspensie în aer, generalizat, dar nerăspândit de vânt la stație sau în apropierea acesteia. În momentul observației"),
#         ("07", "Praf sau nisip ridicat de vânt la stație sau în apropierea acesteia, în cursul orei precedente sau în cursul orei de praf sau de nisip bine dezvoltate și care a observa furtuna de praf sau de nisip. În momentul observației"),
#         ("08", "Vârtejuri de praf sau de nisip bine dezvoltate la stație sau în apropierea acesteia, în cursul orei precedente, dar se pare că în momentul observației furtuna de praf sau de nisip"),
#         ("09", "Furtună de praf sau de nisip observată la stație în ora precedentă sau în câmpul vizual al stației în momentul observației"),
#         ("10", "Aer ceţos"),
#         ("11", "Strat subțire de ceață sau de ceață"),
#         ("12", "Înghețată la stație, cu o grosime care să nu depășească 2 m de la suprafața terestră. În cazul stațiilor de pe mare - mai mult sau mai puțin continuu."),
#         ("13", "Fulgere, nu se aude tunetul"),
#         ("14", "Precipitații în câmpul vizual, care nu ating solul sau suprafața mării"),
#         ("15", "Precipitații în câmpul vizual, care ating solul sau suprafața mării, dar la distanță de stație (ceea ce apreciază la mai mult de 5 km de stație)"),
#         ("16", "Precipitații în câmpul vizual, care ating solul sau suprafața mării, la mai puțin de 5 km de stație, dar nu chiar la stație"),
#         ("17", "Oraj, dar neregulat de precipitații în momentul observației. La stație sau în câmpul vizual al acesteia în cursul orei precedente sau în"),
#         ("18", "Vijelle"),
        
#         # ww= 20-29 section
#         ("19", "Trombă (e) pe uscat sau pe mare, nori de tornadă sau pâcluri de apă în cursul orei precedente sau în momentul observației"),
#         ("20", "Burniță (care nu înghează) sau zăpadă graunțoasă"),
#         ("21", "Ploaie (care nu înghează)"),
#         ("22", "Ninsoare"),
#         ("23", "Lapoviță sau granule de ghează"),
#         ("24", "Burniță sau ploaie care înghează"),
#         ("25", "Aversă (e) de ploaie"),
#         ("26", "Aversă (e) de ninsoare sau lapoviță"),
#         ("27", "Aversă (e) de grindină, măzăriche moale, măzăriche tare sau aversă de ploaie și grindină sau aversă de măzăriche moale sau măzăriche tare"),
#         ("28", "Ceață sau ceață înghețată"),
#         ("29", "Oraj (cu sau fără precipitații)"),
        
#         # ww= 30-39 section
#         ("30", "Furtună de praf sau de nisip, transport de zăpadă la sol sau la înălțime la stație în cursul orei precedente"),
#         ("31", "Furtună de praf sau de nisip, slabă sau moderată - fără schimbare apreciabilă în cursul orei precedente"),
#         ("32", "Furtună de praf sau de nisip, slabă sau moderată - a început sau s-a intensificat în cursul orei precedente"),
#         ("33", "Furtună de praf sau de nisip, slabă sau moderată - a slăbit în cursul orei precedente"),
#         ("34", "Furtună de praf sau de nisip, violentă - fără schimbare apreciabilă în cursul orei precedente"),
#         ("35", "Furtună de praf sau de nisip, violentă - a început sau s-a intensificat în cursul orei precedente"),
#         ("36", "Transport de zăpadă, slab sau moderat - în general, în straturile joase (sub nivelul stației)"),
#         ("37", "Transport de zăpadă, puternic - în general, în straturile joase (sub nivelul observatorului)"),
#         ("38", "Transport de zăpadă, slab sau moderat - în general, la înălțime (mai sus de nivelul observatorului)"),
#         ("39", "Transport de zăpadă, puternic"),
        
#         # ww= 40-49 section
#         ("40", "Ceață sau ceață înghețată la distanță. În momentul observației, care se întinde la un nivel mai sus decât ochiul observatorului. În cursul orei precedente nu a fost ceață la stație"),
#         ("41", "Ceață sau ceață înghețată în bancuri"),
#         ("42", "Ceață sau ceață înghețată cu cer vizibil - s-a subțiat în cursul orei precedente"),
#         ("43", "Ceață sau ceață înghețată cu cer invizibil"),
#         ("44", "Ceață sau ceață înghețată cu cer vizibil - fără schimbare apreciabilă în cursul orei precedente"),
#         ("45", "Ceață sau ceață înghețată cu cer invizibil"),
#         ("46", "Ceață sau ceață înghețată cu cer vizibil - a început sau a devenit mai groasă în cursul orei precedente"),
#         ("47", "Ceață sau ceață înghețată cu cer invizibil"),
        
#         # ww= 50-59 section
#         ("50", "Burniță care nu înghează, intermitentă - slabă în momentul observației"),
#         ("51", "Burniță care nu înghează, continuă - slabă în momentul observației"),
#         ("52", "Burniță care nu înghează, intermitentă - moderată în momentul observației"),
#         ("53", "Burniță care nu înghează, continuă - moderată în momentul observației"),
#         ("54", "Burniță care nu înghează, intermitentă - puternică (densă) în momentul observației"),
#         ("55", "Burniță care nu înghează, continuă - puternică (densă) în momentul observației"),
#         ("56", "Burniță care înghează, slabă (depune polei)"),
#         ("57", "Burniță care înghează, moderată sau puternică (densă)(depune polei)"),
#         ("58", "Burniță și ploaie, slabă"),
#         ("59", "Burniță și ploaie, moderată sau puternică"),
        
#         # ww= 60-69 section
#         ("60", "Ploaie care nu înghează, intermitentă - slabă în momentul observației"),
#         ("61", "Ploaie care nu înghează, continuă - slabă în momentul observației"),
#         ("62", "Ploaie care nu înghează, intermitentă - moderată în momentul observației"),
#         ("63", "Ploaie care nu înghează, continuă - moderată în momentul observației"),
#         ("64", "Ploaie care nu înghează, intermitentă - puternică în momentul observației"),
#         ("65", "Ploaie care nu înghează, continuă - puternică în momentul observației"),
#         ("66", "Ploaie care înghează, moderată sau puternică (depune polei)"),
#         ("67", "Ploaie care înghează, moderată sau puternică (depune polei)"),
#         ("68", "Ploaie (sau burniță) și ninsoare (lapoviță), slabă"),
#         ("69", "Ploaie (sau burniță) și ninsoare (lapoviță), moderată sau puternică"),
        
#         # ww= 70-79 section
#         ("70", "Ninsoare intermitentă - slabă în momentul observației"),
#         ("71", "Ninsoare continuă - slabă în momentul observației"),
#         ("72", "Ninsoare intermitentă - moderată în momentul observației"),
#         ("73", "Ninsoare continuă - moderată în momentul observației"),
#         ("74", "Ninsoare intermitentă - puternică în momentul observației"),
#         ("75", "Ninsoare continuă - puternică în momentul observației"),
#         ("76", "Ace de ghează (cu sau fără ceață)"),
#         ("77", "Ninsoare graunțoasă (cu sau fără ceață)"),
#         ("78", "Steluțe de ninsoare, izolate (cu sau fără ceață)"),
#         ("79", "Granule de ghează"),
        
#         # ww= 80-99 section
#         ("80", "Aversă (e) de ploaie, slabă (e)"),
#         ("81", "Aversă (e) de ploaie, moderată (e) sau puternică (e)"),
#         ("82", "Aversă (e) de ploaie, violentă (e)"),
#         ("83", "Aversă (e) de lapoviță, slabă (e)"),
#         ("84", "Aversă (e) de lapoviță, moderată (e) sau puternică (e)"),
#         ("85", "Aversă (e) de ninsoare, slabă (e)"),
#         ("86", "Aversă (e) de ninsoare, moderată (e) sau puternică (e)"),
#         ("87", "Aversă de măzăriche moale sau slabă (e) măzăriche tare cu sau fără ploaie ori lapoviță - moderată (e) sau puternică (e)"),
#         ("88", "Aversă (e) de grindină cu sau fără ploaie, ninsoare sau cu lapoviță, neînsoțite de tunet - slabă (e)"),
#         ("89", "Aversă (e) de grindină cu sau fără ploaie, ninsoare sau cu lapoviță, neînsoțite de tunet - moderată (e) sau puternică (e)"),
#         ("90", "Aversă (e) de grindină cu sau fără ploaie, ninsoare sau cu lapoviță, neînsoțite de tunet - moderată (e) sau puternică (e)"),
#         ("91", "Ploaie slabă în momentul observației - oraj în cursul orei precedente, dar nu în momentul observației"),
#         ("92", "Ploaie moderată sau puternică în momentul observației - oraj în cursul orei prece-dente, dar nu în momentul observației"),
#         ("93", "Ninsoare sau lapoviță ori grindină, măzăriche tare sau măzăriche moale, slabă în momentul observației - oraj în cursul orei prece-dente, dar nu în momentul observației"),
#         ("94", "Ninsoare sau lapoviță, ori grindină, măzăriche tare sau măzăriche moale, moderată sau puternică în momentul observației - oraj în cursul orei prece-dente, dar nu în momentul observației"),
#         ("95", "Oraj slab sau moderat, fără grindină, măzăriche tare sau măzăriche moale, dar cu ploaie, ninsoare sau cu lapoviță în momentul observației - oraj în momentul observației"),
#         ("96", "Oraj slab sau moderat cu grindină, măzăriche tare sau măzăriche moale în momentul observației - oraj în momentul observației"),
#         ("97", "Oraj puternic, fără grindină, măzăriche tare sau măzăriche moale, dar cu ploaie, ninsoare sau cu lapoviță în momentul observației - oraj în momentul observației"),
#         ("98", "Oraj cu furtună de praf sau de nisip în momentul observației - oraj în momentul observației"),
#         ("99", "Oraj puternic cu grindină, măzăriche tare sau măzăriche moale în momentul observației - oraj în momentul observației")
#     ]
    
#     # Create DataFrame
#     df = pd.DataFrame(data, columns=['Cifra de cod', 'Semnificatia'])
    
#     return df

# def save_manually_cod_table():
#     """
#     Create and save the COD 4677 table as CSV file.
#     """
#     print("Creating COD 4677 meteorological codes table...")
    
#     # Create the table
#     df = create_manually_cod_table()
    
#     # Display info
#     print(f"✓ Successfully created table with {len(df)} rows")
#     print(f"Columns: {list(df.columns)}")
#     print(f"Code range: {df['Cifra de cod'].min()} to {df['Cifra de cod'].max()}")
    
#     # Save to CSV
#     filename = "cod_4677_meteorological_codes.csv"
#     df.to_csv(filename, index=False, encoding='utf-8')
#     print(f"✓ Table saved as: {filename}")
    
#     # Display first and last few rows
#     print("\nFirst 5 rows:")
#     print(df.head().to_string(index=False))
    
#     print("\nLast 5 rows:")
#     print(df.tail().to_string(index=False))
    
#     # Show some statistics
#     print(f"\nStatistics:")
#     print(f"- Total codes: {len(df)}")
#     print(f"- Codes 00-19: {len(df[df['Cifra de cod'].astype(int) <= 19])}")
#     print(f"- Codes 20-29: {len(df[(df['Cifra de cod'].astype(int) >= 20) & (df['Cifra de cod'].astype(int) <= 29)])}")
#     print(f"- Codes 30-39: {len(df[(df['Cifra de cod'].astype(int) >= 30) & (df['Cifra de cod'].astype(int) <= 39)])}")
#     print(f"- Codes 40-49: {len(df[(df['Cifra de cod'].astype(int) >= 40) & (df['Cifra de cod'].astype(int) <= 49)])}")
#     print(f"- Codes 50-59: {len(df[(df['Cifra de cod'].astype(int) >= 50) & (df['Cifra de cod'].astype(int) <= 59)])}")
#     print(f"- Codes 60-69: {len(df[(df['Cifra de cod'].astype(int) >= 60) & (df['Cifra de cod'].astype(int) <= 69)])}")
#     print(f"- Codes 70-79: {len(df[(df['Cifra de cod'].astype(int) >= 70) & (df['Cifra de cod'].astype(int) <= 79)])}")
#     print(f"- Codes 80-99: {len(df[df['Cifra de cod'].astype(int) >= 80])}")
    
#     return df


# class PDFTableExtractor:
#     def __init__(self, pdf_path: str):
#         """
#         Initialize the PDF table extractor.
        
#         Args:
#             pdf_path (str): Path to the PDF file
#         """
#         self.pdf_path = pdf_path
    
#     def debug_page_content(self, page_number: int, title_pattern: str = None) -> None:
#         """Debug helper to see page content and search for patterns."""
#         try:
#             with pdfplumber.open(self.pdf_path) as pdf:
#                 if page_number > len(pdf.pages) or page_number < 1:
#                     print(f"Page {page_number} not found in PDF")
#                     return
                
#                 page = pdf.pages[page_number - 1]
#                 text = page.extract_text()
                
#                 print(f"=== PAGE {page_number} CONTENT ===")
#                 if text:
#                     lines = text.split('\n')[:20]  # First 20 lines
#                     for i, line in enumerate(lines):
#                         print(f"{i+1:2d}: {line}")
                    
#                     if title_pattern:
#                         matches = re.findall(title_pattern, text, re.IGNORECASE)
#                         print(f"\nPattern '{title_pattern}' matches: {matches}")
                        
#                         # Try different variations
#                         variations = [
#                             title_pattern.replace(' ', r'\s+'),  # flexible whitespace
#                             title_pattern.replace(' ', '.*?'),   # any characters between
#                             f".*{title_pattern}.*",              # anywhere in line
#                         ]
                        
#                         for var in variations:
#                             if re.search(var, text, re.IGNORECASE | re.DOTALL):
#                                 print(f"✓ Found with pattern: {var}")
                
#                 tables = page.extract_tables()
#                 print(f"\nFound {len(tables)} tables on page {page_number}")
                
#                 # Show preview of each table
#                 for i, table in enumerate(tables):
#                     if table and len(table) > 0:
#                         print(f"\n--- Table {i+1} ---")
#                         print(f"Dimensions: {len(table)} rows x {len(table[0]) if table[0] else 0} columns")
#                         if len(table) > 0:
#                             print(f"Header: {table[0][:3]}...")  # First 3 columns of header
#                         if len(table) > 1:
#                             print(f"First row: {table[1][:3]}...")  # First 3 columns of first data row
                
#         except Exception as e:
#             print(f"Debug error: {e}")
    
#     def extract_multipage_table_by_headers(self, 
#                                           headers_to_find: List[str], 
#                                           start_page: int,
#                                           max_pages: int = 10,
#                                           exact_match: bool = False) -> Optional[pd.DataFrame]:
#         """
#         Extract a table that spans multiple pages based on headers.
        
#         Args:
#             headers_to_find (List[str]): List of header names to look for
#             start_page (int): Starting page number
#             max_pages (int): Maximum number of pages to check for continuation
#             exact_match (bool): If True, headers must match exactly
            
#         Returns:
#             pd.DataFrame: Combined table from multiple pages or None if not found
#         """
#         try:
#             print(f"=== EXTRACTING MULTIPAGE TABLE STARTING FROM PAGE {start_page} ===")
            
#             # First, find the table on the starting page
#             first_table = self.extract_table_by_headers(headers_to_find, start_page, exact_match)
            
#             if first_table is None:
#                 print(f"No table with matching headers found on starting page {start_page}")
#                 return None
            
#             print(f"✓ Found initial table on page {start_page} with {len(first_table)} rows")
            
#             # Store all table parts
#             table_parts = [first_table]
#             current_page = start_page + 1
            
#             # Check subsequent pages for continuation
#             for page_offset in range(1, max_pages + 1):
#                 current_page = start_page + page_offset
                
#                 print(f"\n--- Checking page {current_page} for continuation ---")
                
#                 # Check if this page has a continuation of the table
#                 continuation_table = self._extract_table_continuation(
#                     headers_to_find, current_page, first_table.columns.tolist(), exact_match
#                 )
                
#                 if continuation_table is not None and not continuation_table.empty:
#                     print(f"✓ Found continuation on page {current_page} with {len(continuation_table)} rows")
#                     table_parts.append(continuation_table)
#                 else:
#                     print(f"✗ No continuation found on page {current_page}, stopping search")
#                     break
            
#             # Combine all table parts
#             if len(table_parts) == 1:
#                 print(f"\nTable found only on page {start_page}")
#                 return table_parts[0]
#             else:
#                 print(f"\nCombining table parts from {len(table_parts)} pages...")
#                 combined_table = pd.concat(table_parts, ignore_index=True)
#                 print(f"✓ Combined table has {len(combined_table)} total rows")
#                 return combined_table
                
#         except Exception as e:
#             print(f"Error extracting multipage table: {e}")
#             return None

#     def _extract_table_continuation(self, 
#                                    headers_to_find: List[str], 
#                                    page_number: int,
#                                    expected_columns: List[str],
#                                    exact_match: bool = False) -> Optional[pd.DataFrame]:
#         """
#         Extract a table continuation from a specific page.
        
#         Args:
#             headers_to_find (List[str]): Original headers to look for
#             page_number (int): Page number to check
#             expected_columns (List[str]): Expected column names from the first table
#             exact_match (bool): Whether to use exact matching
            
#         Returns:
#             pd.DataFrame: Table continuation or None if not found
#         """
#         try:
#             with pdfplumber.open(self.pdf_path) as pdf:
#                 if page_number > len(pdf.pages) or page_number < 1:
#                     return None
                
#                 page = pdf.pages[page_number - 1]
#                 tables = page.extract_tables()
                
#                 if not tables:
#                     return None
                
#                 # Check each table on the page
#                 for table_idx, table in enumerate(tables):
#                     if not table or len(table) < 1:
#                         continue
                    
#                     # Get potential header row
#                     potential_header = table[0]
                    
#                     # Case 1: Table continues with repeated headers
#                     if self._headers_match(potential_header, headers_to_find, exact_match):
#                         print(f"  Found table with repeated headers (table {table_idx + 1})")
#                         # Skip the header row and return data
#                         if len(table) > 1:
#                             df = pd.DataFrame(table[1:], columns=expected_columns)
#                             return self._clean_table(df)
                    
#                     # Case 2: Table continues without headers (data directly)
#                     elif self._looks_like_continuation(table, expected_columns):
#                         print(f"  Found table continuation without headers (table {table_idx + 1})")
#                         # Use the data as-is with expected column names
#                         df = pd.DataFrame(table, columns=expected_columns)
#                         return self._clean_table(df)
                
#                 return None
                
#         except Exception as e:
#             print(f"Error checking continuation on page {page_number}: {e}")
#             return None

#     def _looks_like_continuation(self, table: List[List], expected_columns: List[str]) -> bool:
#         """
#         Check if a table looks like a continuation (data without headers).
        
#         Args:
#             table: Raw table data
#             expected_columns: Expected column structure
            
#         Returns:
#             bool: True if this looks like a table continuation
#         """
#         if not table or len(table) < 1:
#             return False
        
#         # Check if the number of columns matches
#         first_row = table[0]
#         if len(first_row) != len(expected_columns):
#             return False
        
#         # Check if the first row looks like data rather than headers
#         # (This is a heuristic - you might need to adjust based on your data)
#         first_cell = str(first_row[0]).strip() if first_row[0] else ""
        
#         # If first cell is numeric or matches expected data patterns, it's likely data
#         if first_cell.isdigit() or any(char.isdigit() for char in first_cell):
#             return True
        
#         # Additional heuristics can be added here based on your specific data patterns
        
#         return False

#     def extract_table_by_headers(self, 
#                                 headers_to_find: List[str], 
#                                 page_number: int,
#                                 exact_match: bool = False) -> Optional[pd.DataFrame]:
#         """
#         Extract a table based on specific column headers.
        
#         Args:
#             headers_to_find (List[str]): List of header names to look for
#             page_number (int): Page number where the table should be found
#             exact_match (bool): If True, all headers must match exactly; if False, use partial matching
            
#         Returns:
#             pd.DataFrame: Extracted table or None if not found
#         """
#         try:
#             # Using pdfplumber (better for text extraction)
#             table_df = self._extract_by_headers_pdfplumber(headers_to_find, page_number, exact_match)
            
#             if table_df is not None:
#                 return table_df
            
#         except Exception as e:
#             print(f"Error extracting table: {e}")
#             return None
        

#     def _extract_by_headers_pdfplumber(self, 
#                                       headers_to_find: List[str], 
#                                       page_number: int,
#                                       exact_match: bool = False) -> Optional[pd.DataFrame]:
#         """Extract table using pdfplumber based on headers."""
#         try:
#             with pdfplumber.open(self.pdf_path) as pdf:
#                 if page_number > len(pdf.pages) or page_number < 1:
#                     print(f"Page {page_number} not found in PDF")
#                     return None
                
#                 page = pdf.pages[page_number - 1]  # Convert to 0-indexed
                
#                 # Extract all tables from the page
#                 tables = page.extract_tables()
                
#                 if not tables:
#                     print(f"No tables found on page {page_number}")
#                     return None
                
#                 print(f"Found {len(tables)} table(s) on page {page_number}")
                
#                 # Check each table for matching headers
#                 for table_idx, table in enumerate(tables):
#                     if not table or len(table) < 1:
#                         continue
                    
#                     # Get the header row
#                     header_row = table[0]
#                     print(f"\nChecking table {table_idx + 1}:")
#                     print(f"Headers: {header_row}")
                    
#                     # Check if this table has the required headers
#                     if self._headers_match(header_row, headers_to_find, exact_match):
#                         print(f"✓ Found matching table {table_idx + 1}")
                        
#                         # Create DataFrame
#                         table_df = pd.DataFrame(table[1:], columns=table[0])
#                         return self._clean_table(table_df)
#                     else:
#                         print(f"✗ Table {table_idx + 1} headers don't match")
                
#                 print("No table found with matching headers")
#                 return None
                
#         except Exception as e:
#             print(f"Error with pdfplumber: {e}")
#             return None


#     def _headers_match(self, table_headers: List, target_headers: List[str], exact_match: bool = False) -> bool:
#         """Check if table headers match the target headers."""
#         # Clean and normalize headers
#         clean_table_headers = []
#         for header in table_headers:
#             if header is not None:
#                 # Remove newlines, normalize whitespace, and convert to lowercase
#                 clean_header = str(header).replace('\n', ' ').replace('\r', ' ')
#                 clean_header = ' '.join(clean_header.split())  # Normalize whitespace
#                 clean_header = clean_header.strip().lower()
#                 clean_table_headers.append(clean_header)
        
#         # Also clean target headers
#         clean_target_headers = []
#         for header in target_headers:
#             clean_header = header.replace('\n', ' ').replace('\r', ' ')
#             clean_header = ' '.join(clean_header.split())  # Normalize whitespace
#             clean_header = clean_header.strip().lower()
#             clean_target_headers.append(clean_header)
        
#         print(f"  Table headers (cleaned): {clean_table_headers}")
#         print(f"  Target headers (cleaned): {clean_target_headers}")
        
#         if exact_match:
#             # All target headers must be exactly present
#             for target in clean_target_headers:
#                 if target not in clean_table_headers:
#                     return False
#             return True
#         else:
#             # Use partial matching - target headers can be contained within table headers
#             matches = 0
#             for i, target in enumerate(clean_target_headers):
#                 target_found = False
#                 for j, table_header in enumerate(clean_table_headers):
#                     # Check both directions: target in table_header AND table_header in target
#                     if (target in table_header or table_header in target or 
#                         self._fuzzy_header_match(target, table_header)):
#                         print(f"    ✓ Match: '{target}' ≈ '{table_header}'")
#                         matches += 1
#                         target_found = True
#                         break
                
#                 if not target_found:
#                     print(f"    ✗ No match for: '{target}'")
            
#             # Require at least 70% of target headers to match
#             match_ratio = matches / len(clean_target_headers)
#             print(f"  Match ratio: {matches}/{len(clean_target_headers)} = {match_ratio:.2f}")
#             return match_ratio >= 0.7

#     def _fuzzy_header_match(self, target: str, table_header: str) -> bool:
#         """Perform fuzzy matching for headers with potential formatting differences."""
#         # Remove common words and check if key terms match
#         target_words = set(target.split())
#         table_words = set(table_header.split())
        
#         # Check if significant words overlap
#         common_words = target_words.intersection(table_words)
#         if len(common_words) >= min(len(target_words), len(table_words)) * 0.6:
#             return True
        
#         # Check for character similarity (simple approach)
#         target_chars = ''.join(target.split())
#         table_chars = ''.join(table_header.split())
        
#         if len(target_chars) > 0 and len(table_chars) > 0:
#             # Simple character overlap check
#             common_chars = sum(1 for char in target_chars if char in table_chars)
#             similarity = common_chars / max(len(target_chars), len(table_chars))
#             return similarity >= 0.7
        
#         return False

    
#     def _clean_table(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Clean and format the extracted table."""
#         if df is None or df.empty:
#             return df
        
#         # Remove completely empty rows and columns
#         df = df.dropna(how='all').loc[:, df.notna().any()]
        
#         # Clean column names
#         df.columns = [str(col).strip() if col and str(col) != 'nan' else f"Column_{i}" 
#                      for i, col in enumerate(df.columns)]
        
#         # Clean cell values
#         for col in df.columns:
#             if df[col].dtype == 'object':
#                 df[col] = df[col].astype(str).str.strip()
#                 # Replace 'nan' strings with actual NaN
#                 df[col] = df[col].replace(['nan', 'None', '', 'NaN'], pd.NA)
        
#         return df


# def extract_multipage_cod_table(pdf_path: str, 
#                                start_page: int, 
#                                headers: List[str],
#                                max_pages: int = 10) -> Optional[pd.DataFrame]:
#     """
#     Extract a multi-page table with specific headers.
    
#     Args:
#         pdf_path (str): Path to the PDF file
#         start_page (int): Starting page number
#         headers (List[str]): List of header names to search for
#         max_pages (int): Maximum pages to check for continuation
    
#     Returns:
#         pd.DataFrame: Combined table from multiple pages
#     """
#     extractor = PDFTableExtractor(pdf_path)
    
#     print(f"=== EXTRACTING MULTIPAGE TABLE ===")
#     print(f"Starting page: {start_page}")
#     print(f"Target headers: {headers}")
#     print(f"Max pages to check: {max_pages}")
    
#     return extractor.extract_multipage_table_by_headers(headers, start_page, max_pages)


# def extract_single_page_cod_table(pdf_path: str, page_number: int = 298) -> Optional[pd.DataFrame]:
#     """
#     Specific function to extract the COD 1600 table from page 298 based on headers.
    
#     Args:
#         pdf_path (str): Path to the PDF file
#         page_number (int): Page number (default 298)
    
#     Returns:
#         pd.DataFrame: Extracted table
#     """
#     extractor = PDFTableExtractor(pdf_path)
    
#     # Define the target headers for COD 1600 table
#     target_headers = ["Cifră de cod", "Înălţimea bazei norilor"]
    
#     # First, debug the page to see what's available
#     print("=== DEBUGGING PAGE CONTENT ===")
#     extractor.debug_page_content(page_number, "COD 1600")
#     print("\n=== EXTRACTING TABLE BY HEADERS ===")
    
#     return extractor.extract_table_by_headers(target_headers, page_number)


# def process_bucharest_weather_codes():
#     """
#     Process Bucharest weather data by correlating ww and ix codes with meteorological meanings.
#     """
    
#     print("=" * 60)
#     print("WEATHER CODE PROCESSING FOR BUCHAREST")
#     print("=" * 60)
    
#     # Define paths
#     bucuresti_folder = Path("date/bucuresti")
#     target_file = "SirDate_1748514797752_Bucuresti.csv"
#     target_path = bucuresti_folder / target_file
    
#     # Check if target file exists
#     if not target_path.exists():
#         print(f"❌ Target file not found: {target_path}")
#         return None
    
#     # List current working directory to find reference tables
#     print("Available files in current directory:")
#     current_files = [f for f in os.listdir('.') if f.endswith('.csv')]
#     for file in current_files:
#         print(f"  - {file}")
    
#     # Load reference tables
#     try:
#         print(f"\n--- Loading Reference Tables ---")
        
#         # Load COD 4677 table
#         cod_4677_path = "cod_4677_meteorological_codes.csv"
#         if os.path.exists(cod_4677_path):
#             cod_4677_df = pd.read_csv(cod_4677_path, encoding='utf-8')
#             print(f"✓ Loaded {cod_4677_path}: {cod_4677_df.shape}")
#         else:
#             print(f"❌ {cod_4677_path} not found")
#             return None
            
#         # Load multipage table
#         cod_multipage_path = "cod_4680_multipage_table.csv"
#         if os.path.exists(cod_multipage_path):
#             cod_multipage_df = pd.read_csv(cod_multipage_path, encoding='utf-8')
#             print(f"✓ Loaded {cod_multipage_path}: {cod_multipage_df.shape}")
#         else:
#             print(f"❌ {cod_multipage_path} not found")
#             return None
            
#     except Exception as e:
#         print(f"❌ Error loading reference tables: {e}")
#         return None
    
#     # Load target data
#     try:
#         print(f"\n--- Loading Target Data ---")
#         df = pd.read_csv(target_path, encoding='utf-8')
#         print(f"✓ Loaded {target_file}: {df.shape}")
#         print(f"Columns: {list(df.columns)}")
        
#     except Exception as e:
#         print(f"❌ Error loading target file: {e}")
#         return None
    
#     # Extract last 2 columns (ww and ix)
#     if len(df.columns) < 2:
#         print(f"❌ Not enough columns in the data. Found: {len(df.columns)}")
#         return None
    
#     # Get the last 2 columns
#     ww_col = df.columns[-2]  # Second to last column (ww)
#     ix_col = df.columns[-1]  # Last column (ix)
    
#     print(f"\n--- Extracting Last 2 Columns ---")
#     print(f"WW column: '{ww_col}'")
#     print(f"IX column: '{ix_col}'")
    
#     # Extract and preprocess the columns
#     ww_data = df[ww_col].copy()
#     ix_data = df[ix_col].copy()
    
#     print(f"Original WW data sample: {ww_data.head()}")
#     print(f"Original IX data sample: {ix_data.head()}")
    
#     # Preprocess WW column: replace NaN and "//" with "*"
#     print(f"\n--- Preprocessing WW Column ---")
#     print(f"Original NaN count: {ww_data.isna().sum()}")
#     print(f"Original '//' count: {(ww_data == '//').sum()}")
    
#     # Replace NaN and "//" with "*"
#     ww_data = ww_data.fillna("*")
#     ww_data = ww_data.replace("//", "*")
    
#     print(f"After preprocessing - '*' count: {(ww_data == '*').sum()}")
    
#     # Preprocess IX column: convert to int
#     print(f"\n--- Preprocessing IX Column ---")
#     print(f"Original IX data type: {ix_data.dtype}")
#     print(f"IX NaN count: {ix_data.isna().sum()}")
    
#     # Handle NaN values in IX column (replace with a default value, e.g., 0)
#     ix_data = ix_data.fillna(0)
    
#     # Convert to int
#     try:
#         ix_data = ix_data.astype(int)
#         print(f"✓ Converted IX to int. New data type: {ix_data.dtype}")
#         print(f"IX value range: {ix_data.min()} to {ix_data.max()}")
#         print(f"IX unique values: {sorted(ix_data.unique())}")
#     except Exception as e:
#         print(f"❌ Error converting IX to int: {e}")
#         return None
    
#     # Create dictionaries for fast lookup
#     print(f"\n--- Creating Lookup Dictionaries ---")
    
#     # Convert cod_4677 to dictionary (code -> meaning)
#     cod_4677_dict = {}
#     for _, row in cod_4677_df.iterrows():
#         code = str(row['Cifra de cod']).zfill(2)  # Ensure 2 digits with leading zero
#         meaning = row['Semnificatia']
#         cod_4677_dict[code] = meaning
    
#     print(f"✓ COD 4677 dictionary created with {len(cod_4677_dict)} entries")
#     print(f"Sample entries: {list(cod_4677_dict.items())[:3]}")
    
#     # Convert multipage to dictionary
#     cod_multipage_dict = {}
#     for _, row in cod_multipage_df.iterrows():
#         # Assume first column is code, second is meaning
#         code = str(row.iloc[0]).zfill(2) if pd.notna(row.iloc[0]) else ""
#         meaning = row.iloc[1] if pd.notna(row.iloc[1]) else ""
#         if code and meaning:
#             cod_multipage_dict[code] = meaning
    
#     print(f"✓ Multipage dictionary created with {len(cod_multipage_dict)} entries")
#     if cod_multipage_dict:
#         print(f"Sample entries: {list(cod_multipage_dict.items())[:3]}")
    
#     # Process weather codes based on ix values
#     print(f"\n--- Processing Weather Codes ---")
    
#     fenomen_data = []
#     stats = {"nu_avem_fenomen": 0, "cod_4677": 0, "cod_multipage": 0, "not_found": 0}
    
#     for i, (ww_val, ix_val) in enumerate(zip(ww_data, ix_data)):
#         if ww_val == "*":
#             fenomen = "Nu avem fenomen"
#             stats["nu_avem_fenomen"] += 1
#         else:
#             # Convert ww_val to string and pad with zeros
#             ww_code = str(ww_val).zfill(2)
            
#             if 1 <= ix_val <= 3:
#                 # Use cod_4677
#                 if ww_code in cod_4677_dict:
#                     fenomen = cod_4677_dict[ww_code]
#                     stats["cod_4677"] += 1
#                 else:
#                     fenomen = f"Cod necunoscut: {ww_code} (4677)"
#                     stats["not_found"] += 1
                    
#             elif 4 <= ix_val <= 7:
#                 # Use cod_multipage
#                 if ww_code in cod_multipage_dict:
#                     fenomen = cod_multipage_dict[ww_code]
#                     stats["cod_multipage"] += 1
#                 else:
#                     fenomen = f"Cod necunoscut: {ww_code} (multipage)"
#                     stats["not_found"] += 1
#             else:
#                 # IX value outside expected range
#                 fenomen = f"IX invalid: {ix_val}, WW: {ww_code}"
#                 stats["not_found"] += 1
        
#         fenomen_data.append(fenomen)
        
#         # Show progress for every 1000 rows
#         if (i + 1) % 1000 == 0:
#             print(f"  Processed {i + 1} rows...")
    
#     print(f"✓ Processing complete!")
#     print(f"Statistics:")
#     for key, value in stats.items():
#         print(f"  - {key}: {value}")
    
#     # Create new dataframe without the last 2 columns and add Fenomen column
#     print(f"\n--- Creating Final Dataset ---")
    
#     # Remove last 2 columns
#     df_final = df.iloc[:, :-2].copy()
    
#     # Add Fenomen column
#     df_final['Fenomen'] = fenomen_data
    
#     print(f"Original shape: {df.shape}")
#     print(f"Final shape: {df_final.shape}")
#     print(f"New columns: {list(df_final.columns)}")
    
#     # Show sample of final data
#     print(f"\nSample of final data:")
#     print(df_final[['Fenomen']].head(10))
    
#     # Save the file
#     try:
#         df_final.to_csv(target_path, index=False, encoding='utf-8')
#         print(f"✓ File saved successfully: {target_path}")
        
#         # Verify the saved file
#         verification_df = pd.read_csv(target_path, encoding='utf-8')
#         print(f"✓ Verification - saved file shape: {verification_df.shape}")
        
#     except Exception as e:
#         print(f"❌ Error saving file: {e}")
#         return None
    
#     return df_final

# def verify_processing_results():
#     """
#     Verify the results of the weather code processing.
#     """
#     print(f"\n" + "=" * 60)
#     print("VERIFICATION OF PROCESSING RESULTS")
#     print("=" * 60)
    
#     # Load the processed file
#     target_path = Path("date/bucuresti/SirDate_1748514797752_Bucuresti.csv")
    
#     if not target_path.exists():
#         print(f"❌ Processed file not found: {target_path}")
#         return
    
#     try:
#         df = pd.read_csv(target_path, encoding='utf-8')
        
#         print(f"✓ Processed file loaded successfully")
#         print(f"Shape: {df.shape}")
#         print(f"Columns: {list(df.columns)}")
        
#         if 'Fenomen' in df.columns:
#             fenomen_counts = df['Fenomen'].value_counts()
#             print(f"\nTop 10 most frequent weather phenomena:")
#             print(fenomen_counts.head(10))
            
#             # Count special cases
#             nu_avem_count = (df['Fenomen'] == 'Nu avem fenomen').sum()
#             necunoscut_count = df['Fenomen'].str.contains('Cod necunoscut', na=False).sum()
            
#             print(f"\nSpecial cases:")
#             print(f"  - 'Nu avem fenomen': {nu_avem_count}")
#             print(f"  - 'Cod necunoscut': {necunoscut_count}")
#             print(f"  - Total unique phenomena: {df['Fenomen'].nunique()}")
        
#     except Exception as e:
#         print(f"❌ Error verifying results: {e}")

# def generate_analysis_dates(date_range: Tuple[str, str], past_days: int, output_file: str = "analysis_dates.txt") -> List[str]:
#     """
#     Generate analysis dates with specified intervals and save to a text file.
    
#     Args:
#         date_range (Tuple[str, str]): Tuple of (start_date, end_date) in format "yyyy-mm-dd"
#         past_days (int): Number of past days needed for each analysis
#         output_file (str): Name of the output text file
    
#     Returns:
#         List[str]: List of generated dates in "yyyy-mm-dd" format
    
#     Logic:
#         - First analysis date = start_date + past_days
#         - Interval between dates = past_days + 1
#         - Stop when target date exceeds end_date or insufficient historical data
#     """
    
#     start_date_str, end_date_str = date_range
    
#     # Parse input dates
#     try:
#         start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
#         end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
#     except ValueError as e:
#         raise ValueError(f"Invalid date format. Use yyyy-mm-dd format. Error: {e}")
    
#     # Validate date range
#     if start_date >= end_date:
#         raise ValueError("Start date must be before end date")
    
#     # Calculate first analysis date
#     first_analysis_date = start_date + timedelta(days=past_days)
    
#     # Check if first analysis date is valid
#     if first_analysis_date > end_date:
#         print(f"Warning: Not enough data in range. First possible analysis date ({first_analysis_date}) exceeds end date ({end_date})")
#         return []
    
#     # Generate analysis dates
#     analysis_dates = []
#     current_date = first_analysis_date
#     interval = past_days + 1
    
#     while current_date <= end_date:
#         # Check if we have enough historical data for this analysis date
#         # We need past_days worth of data before current_date
#         required_start_date = current_date - timedelta(days=past_days)
        
#         if required_start_date >= start_date:
#             analysis_dates.append(current_date.strftime("%Y-%m-%d"))
#             print(f"Added analysis date: {current_date.strftime('%Y-%m-%d')} (requires data from {required_start_date.strftime('%Y-%m-%d')} to {(current_date - timedelta(days=1)).strftime('%Y-%m-%d')})")
#         else:
#             print(f"Skipping {current_date.strftime('%Y-%m-%d')}: insufficient historical data (would need data from {required_start_date.strftime('%Y-%m-%d')})")
        
#         # Move to next analysis date
#         current_date += timedelta(days=interval)
    
#     # Save to text file
#     try:
#         with open(output_file, 'w', encoding='utf-8') as f:
#             for date in analysis_dates:
#                 f.write(f"{date}\n")
        
#         print(f"\nSuccessfully saved {len(analysis_dates)} analysis dates to '{output_file}'")
        
#     except IOError as e:
#         print(f"Error saving to file '{output_file}': {e}")
    
#     return analysis_dates

# def validate_date_generation(date_range: Tuple[str, str], past_days: int) -> None:
#     """
#     Validate and demonstrate the date generation logic.
    
#     Args:
#         date_range: Tuple of (start_date, end_date)
#         past_days: Number of past days needed
#     """
    
#     start_date_str, end_date_str = date_range
    
#     print(f"Date Generation Validation")
#     print(f"=" * 40)
#     print(f"Start date: {start_date_str}")
#     print(f"End date: {end_date_str}")
#     print(f"Past days required: {past_days}")
#     print(f"Interval: {past_days + 1} days")
#     print(f"First analysis date: {(datetime.strptime(start_date_str, '%Y-%m-%d').date() + timedelta(days=past_days)).strftime('%Y-%m-%d')}")
#     print(f"=" * 40)
    
#     dates = generate_analysis_dates(date_range, past_days, f"dates_{start_date_str}_to_{end_date_str}_past{past_days}.txt")
    
#     print(f"\nGenerated dates: {dates}")
#     return dates


# if __name__ == "__main__":
        
#     if args.tables:
#         # Define the pdf path for the tables
#         pdf_path = "date\\VOLUMUL_I_Ed_II_08nov2017.pdf"
        
#         # Create extractor instance
#         extractor = PDFTableExtractor(pdf_path)
        
#         # Try to extract specific table by headers (single page)
#         print("=== SINGLE PAGE EXTRACTION ===")
#         table = extract_single_page_cod_table(pdf_path, SINGLE_PAGE_TABLE)
        
#         if table is not None:
#             print("\n✓ Successfully extracted single-page table:")
#             print(f"Shape: {table.shape}")
#             print(f"Columns: {list(table.columns)}")
#             print("\nFirst few rows:")
#             print(table.head())
            
#             # Save to CSV if needed
#             table.to_csv("cod_1600_single_page.csv", index=False)
#             print("Single-page table saved to cod_1600_single_page.csv")
        
#         # Try multipage extraction
#         print("\n" + "="*60)
#         print("=== MULTIPAGE EXTRACTION EXAMPLE ===")
        
#         # Example: Extract COD 4680 table that might span multiple pages
#         multipage_headers = ["Cifra de cod", "Semnificatie"]  # Based on your image
#         multipage_table = extract_multipage_cod_table(pdf_path, MULTIPAGE_TABLE, multipage_headers, max_pages=2)
        
#         if multipage_table is not None:
#             print("\n✓ Successfully extracted multipage table:")
#             print(f"Shape: {multipage_table.shape}")
#             print(f"Columns: {list(multipage_table.columns)}")
#             print(f"Total rows: {len(multipage_table)}")
#             print("\nFirst few rows:")
#             print(multipage_table.head())
#             print("\nLast few rows:")
#             print(multipage_table.tail())
            
#             # Save to CSV
#             multipage_table.to_csv("cod_4680_multipage_table.csv", index=False)
#             print("Multipage table saved!")
#         else:
#             print("❌ Multipage table not found")

#         # Create and save the table
#         table = save_manually_cod_table()
        
#         print("\n✓ All tables created successfully!")

#     elif args.bucharest:
#         path_to_csv_data = "date"

#         # First, debug the CSV structure to understand the data
#         print("STEP 1: Debugging CSV structure...")
#         debug_csv_structure(path_to_csv_data)
        
#         # Extract Bucharest data
#         print(f"\n\nSTEP 2: Extracting Bucharest data...")
#         extract_bucharest_data(path_to_csv_data)

#         print(f"\n✓ Processing complete!")

#     elif args.phenomena_codes:
#         # Process the weather codes
#         result = process_bucharest_weather_codes()
        
#         if result is not None:
#             # Verify the results
#             verify_processing_results()
#             print(f"\n✓ Weather code processing completed successfully!")
#         else:
#             print(f"\n❌ Weather code processing failed!")

#     elif args.timestamp is not None and args.past_days is not None:
#         # Check data availability for a specific timestamp and past days
#         result = check_data_availability(args.timestamp, args.past_days)

#         if result['sufficient_data']:
#             print(f"✓ Sufficient data available for {args.timestamp}")
#             # TESTING COMPREHENSIVE WEATHER DATA EXTRACTION
#             # Extract from pdf files
#             # # Run performance comparison
#             # comparison = compare_extraction_performance(args.timestamp, args.past_days, max_workers=4)
#             sequential_pdf_data = extract_forecasts_sequential(args.timestamp, args.past_days)
#             print(f"✓ PDF extraction complete \n{sequential_pdf_data}")

#             if sequential_pdf_data:
#                 # Show sample results
#                 print(f"\nSample extracted forecast:")
#                 first_date = list(sequential_pdf_data.keys())[0]
#                 first_forecast = sequential_pdf_data[first_date]
#                 print(f"Date: {first_date}")
#                 print(f"Interval: {first_forecast['interval']}")
#                 print(f"Forecast preview: {first_forecast['forecast_text'][:300]}...")
            
#             # Extract from csv tables
#             all_table_data = extract_comprehensive_weather_data(args.timestamp, args.past_days)

#             if all_table_data:
#                 if all_table_data['wind_analysis']['mean_speed_ms']:
#                     print(f"Wind Speed: {all_table_data['wind_analysis']['mean_speed_ms']:.2f} m/s")

#                 if all_table_data['nebulosity_analysis']['most_frequent_value']:
#                     print(f"Most frequent nebulosity: {all_table_data['nebulosity_analysis']['most_frequent_value']}")
#                     print(f"Occurred {all_table_data['nebulosity_analysis']['total_occurrences']} times")

#                 print(f"Temperature records: {len(all_table_data['daily_temperatures'])}")
#                 print(f"Precipitation records: {len(all_table_data['daily_precipitation'])}")

#             # Test the prompt generation
#             # user_prompts = []
#             past_days = args.past_days
#             for day in range(past_days):
#                 test_prompt_generation(
#                     current_date=args.timestamp, 
#                     weather_data=all_table_data,
#                     pdf_forecasts=sequential_pdf_data,
#                     saving_past_days=past_days,
#                     past_days=day + 1
#                 )
#                 # user_prompts.append(user_prompt)

#             # Now test the Ollama models with the generated prompts
#             # Read model names from file (one name per row)
#             if not os.path.exists("models_to_test.txt"):
#                 print("❌ Models not selected for test!")
#             else:
#                 with open("models_to_test.txt", "r") as f:
#                     models_to_test = [model[:-1] for model in f.readlines()]

#                 print(f"\nModels to test: {models_to_test}")
                
#                 if args.download_models:
#                     # Downloading models
#                     download_models_only(models_to_test)
#                 elif args.test_models:
#                     # Test the downloaded models
#                     test_downloaded_models(
#                         models_list=models_to_test,
#                         past_days=args.past_days,
#                         base_date=args.timestamp,
#                         keep_alive="10m"  # Keep each model loaded during testing
#                     )
#                 elif args.statistical_analysis:

#                     # Run the analysis
#                     create_analysis_tables(
#                         responses_folder=f"responses\\{args.timestamp}\\{args.past_days}_past_days",
#                         output_date=args.timestamp, 
#                         output_past_days=args.past_days,
#                         reference_text=first_forecast['forecast_text']
#                     )
#                 elif args.judge_analysis:

#                     # Run the judge analysis
#                     create_judge_analysis(
#                         responses_folder=f"responses\\{args.timestamp}\\{args.past_days}_past_days",
#                         reference_text=first_forecast['forecast_text'],
#                         judge_model=args.judge,
#                         n_past_days=args.past_days,
#                         api_key=...
#                     )
#                 else:
#                     print(
#                         "No model action specified."\
#                         " Use --download_models (-dm) or --test_models (-tm)."
#                     )
#         else:
#             print(f"❌ Insufficient data for {args.timestamp}")

#     elif args.get_test_time_interval is not None and args.past_days is not None:
#         # Generate testing dates
#         dates = validate_date_generation(args.get_test_time_interval, args.past_days)

#         # Now test the Ollama models with the generated prompts
#         # Read model names from file (one name per row)
#         if not os.path.exists("models_to_test.txt"):
#             print("❌ Models not selected for test!")
#         else:
#             with open("models_to_test.txt", "r") as f:
#                 models_to_test = [model[:-1] for model in f.readlines()]

#             print(f"\nModels to test: {models_to_test}")
#             if args.download_models:
#                 # Downloading models
#                 download_models_only(models_to_test)
                
#         for date in dates:
#             # Check data availability for a specific timestamp and past days
#             result = check_data_availability(date, args.past_days)

#             if result['sufficient_data']:
#                 print(f"✓ Sufficient data available for {date}")
#                 # TESTING COMPREHENSIVE WEATHER DATA EXTRACTION
#                 # Extract from pdf files
                
#                 # Extract from csv tables
#                 all_table_data = extract_comprehensive_weather_data(date, args.past_days)

#                 if args.generate_prompts_gpt:
#                 # Test the prompt generation
#                     past_days = args.past_days
#                     for day in range(past_days):
#                         test_prompt_generation_gpt(
#                             current_date=date, 
#                             weather_data=all_table_data,
#                             saving_past_days=past_days,
#                             past_days=day + 1,
#                             openai_api_key=...
#                         )
#                 elif args.test_models:
#                     # Test the downloaded models
#                     test_downloaded_models(
#                         models_list=models_to_test,
#                         past_days=args.past_days,
#                         base_date=date,
#                         keep_alive="30m"  # Keep each model loaded during testing
#                     )
#                 elif args.statistical_analysis:
#                     # Load reference text from formatted diagnoses
#                     reference_text = load_reference_text(date)

#                     # Run the analysis
#                     create_analysis_tables_gpt(
#                         responses_folder=f"responses\\{date}\\{args.past_days}_past_days",
#                         output_date=date, 
#                         output_past_days=args.past_days,
#                         reference_text=reference_text
#                     )
#                 elif args.judge_analysis:
#                     # Load reference text from formatted diagnoses
#                     reference_text = load_reference_text(date)

#                     # Run the judge analysis
#                     create_judge_analysis(
#                         responses_folder=f"responses\\{date}\\{args.past_days}_past_days",
#                         reference_text=reference_text,
#                         judge_model=args.judge,
#                         n_past_days=args.past_days,
#                         api_key=...
#                     )
#                     # Setting the judge directory to look for data
#                     judge_output_dir = f"llm_as_a_judge\\gpt-5-mini\\{date}\\{args.past_days}_past_days"
#                     generate_judge_analysis_tables(judge_output_dir)
#                 else:
#                     print(
#                         "No model action specified."\
#                         " Use --download_models (-dm) or --test_models (-tm)."
#                     )
#             else:
#                 print(f"❌ Insufficient data for {date}")

#     # Generate training dataset if flag is set
#     elif args.generate_training_dataset_for_year is not None:
#         year_to_process = args.generate_training_dataset_for_year
#         # Run the extraction
#         results = extract_yearly_diagnoses_and_format(
#             year=year_to_process,
#             judge_model=args.judge,
#             output_folder=f"formatted_diagnoses_{year_to_process}",
#             api_key=...,
#             delay_between_calls=1.0  # 1 second delay between API calls
#         )
        
#         # Validate results
#         if results:
#             validate_yearly_extraction(year_to_process)
#         else:
#             print("No results to validate")

#     elif args.finetune:
#         # Import fine-tuning integration
#         from prompting.utils.finetune_integration import run_finetuning_pipeline, run_comparison_pipeline
        
#         if not args.year:
#             print("Year is required for fine-tuning. Use --year (-y) to specify.")
#             exit(1)
        
#         # Set default past_days if not provided
#         if not args.past_days:
#             args.past_days = 4
#             print(f"Using default past_days: {args.past_days}")
        
#         # Handle comparison mode
#         if args.compare:
#             print(f"Starting comparison pipeline for year {args.year}")
#             print(f"Configuration:")
#             print(f"  - Year: {args.year}")
#             print(f"  - Past days: {args.past_days}")
#             print(f"  - Mode: Comparison (few-shot vs zero-shot)")
            
#             success = run_comparison_pipeline(args)
            
#             if success:
#                 print("\n✅ Comparison pipeline completed successfully!")
#                 print("Check the 'fine_tuned_llm' folder for results:")
#                 print("  - fine_tuned_llm/results/few-shot/ (few-shot results)")
#                 print("  - fine_tuned_llm/results/zero-shot/ (zero-shot results)")
#             else:
#                 print("\n❌ Comparison pipeline failed!")
        
#         else:
#             # Regular pipeline
#             approach = "zero-shot" if args.zero_shot else "few-shot"
#             print(f"Starting {approach} fine-tuning pipeline for year {args.year}")
#             print(f"Configuration:")
#             print(f"  - Year: {args.year}")
#             print(f"  - Past days: {args.past_days}")
#             print(f"  - Approach: {approach}")
#             print(f"  - Batch size: {args.batch_size}")
#             print(f"  - Skip training: {args.skip_training}")
#             print(f"  - Skip testing: {args.skip_testing}")
            
#             # Run the fine-tuning pipeline
#             success = run_finetuning_pipeline(args)
            
#             if success:
#                 print(f"\n✅ {approach.capitalize()} fine-tuning pipeline completed successfully!")
#                 print("Check the 'fine_tuned_llm' folder for results:")
#                 print("  - fine_tuned_llm/model/final_model/ (trained model)")
#                 print(f"  - fine_tuned_llm/responses/{approach}/ (test responses)")
#                 print(f"  - fine_tuned_llm/results/{approach}/ (analysis results)")
#             else:
#                 print(f"\n❌ {approach.capitalize()} fine-tuning pipeline failed!")
            
#     elif args.select_models:
#         # Call the model selection function here
#         generate_gui(n_models=args.n_models)
        
#     else:
#         print("No valid arguments provided.")
#         parser.print_help()

import pandas as pd
from datetime import datetime, timedelta
import pdfplumber
import re
import os
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

from prompting.utils.check_data_availability import check_data_availability
from prompting.utils.input_extraction import (
    extract_comprehensive_weather_data,
    extract_forecasts_sequential,
)
from prompting.utils.prompt_construction import (
    test_prompt_generation,
    test_prompt_generation_gpt,
)
from prompting.utils.model_select_gui import generate_gui
from prompting.utils.ollama_inference import download_models_only, test_downloaded_models
from prompting.utils.response_evaluation import (
    create_analysis_tables,
    create_analysis_tables_gpt,
    load_reference_text,
)
from prompting.utils.judge_evaluation import create_judge_analysis
from prompting.utils.diagnoses_formatting import (
    extract_yearly_diagnoses_and_format,
    validate_yearly_extraction,
)

INITIAL_PAGES = 11
MULTIPAGE_TABLE = 329 + INITIAL_PAGES
SINGLE_PAGE_TABLE = 298 + INITIAL_PAGES

# Define arguments
parser = argparse.ArgumentParser(description='Process meteorological data from multiple sources')
parser.add_argument(
    '--tables',
    '-tab',
    action='store_true', 
    help='Flag to indicate that table codes and meanings should be extracted and saved as CSV'
)
parser.add_argument(
    '--bucharest',
    '-buc',
    action='store_true',
    help='Flag to indicate that only Bucharest data should be extracted and saved'
)
parser.add_argument(
    '--phenomena_codes',
    '-pc',
    action='store_true',
    help='Flag to indicate that weather phenomena should be extracted and added based on table codes'
)
parser.add_argument(
    '--timestamp',
    '-t',
    type=str,
    default=None,
    required=False,
    help='Timestamp in yyyy-mm-dd format (e.g., 2024-12-31) to filter data by date'
)
parser.add_argument(
    '--past_days',
    '-pd',
    type=int,
    default=None,
    required=False,
    help='Number of past days to include in the data extraction as context for LLMs'
)
parser.add_argument(
    '--select_models',
    '-sm',
    action='store_true',
    help='Flag to indicate that model selection should be performed'
)
parser.add_argument(
    '--n_models',
    '-n',
    type=int,
    default=10,
    required=False,
    help='Number of models to select'
)
parser.add_argument(
    '--download_models',
    '-dm',
    action='store_true',
    help='Flag to indicate that models should be downloaded'
)
parser.add_argument(
    '--test_models',
    '-tm',
    action='store_true',
    help='Flag to indicate that downloaded models should be tested'
)
parser.add_argument(
    '--statistical_analysis',
    '-sa',
    action='store_true',
    help='Flag to indicate that statistical analysis should be performed'
)
parser.add_argument(
    '--judge_analysis',
    '-ja',
    action='store_true',
    help='Flag to indicate that LLM as a judge analysis should be performed'
)
parser.add_argument(
    '--judge',
    type=str,
    default='gpt-5-mini',
    required=False,
    help='Define the judge model to be used for analysis (e.g., gpt-5-mini)'
)
parser.add_argument(
    '--get_test_time_interval',
    '-interval',
    default=None,
    nargs=2, 
    metavar=('START_TIME', 'END_TIME'), 
    help='Start and end times in format yyyy-mm-dd'
)
parser.add_argument(
    '--generate_training_dataset_for_year',
    '-gen_data',
    type=int,
    default=None,
    required=False,
    help='Flag to indicate that a training dataset should be generated for the specified year'
)
parser.add_argument(
    '--generate_prompts_gpt',
    '-gen_prompts',
    action='store_true',
    help='Flag to indicate that prompts for GPT should be generated'
)
parser.add_argument(
    '--finetune',
    '-ft',
    action='store_true',
    help='Flag to indicate that fine-tuning pipeline should be run'
)
parser.add_argument(
    '--year',
    '-y',
    type=int,
    default=2024,
    required=False,
    help='Year for fine-tuning data (default: 2024)'
)
parser.add_argument(
    '--skip_training',
    '-st',
    action='store_true',
    help='Skip training phase and only prepare testing data'
)
parser.add_argument(
    '--skip_testing',
    '-sk',
    action='store_true',
    help='Skip testing phase'
)
parser.add_argument(
    '--batch_size',
    '-bs',
    type=int,
    default=24,
    help='Batch size for training (default: 24)'
)
parser.add_argument(
    '--zero_shot',
    '-zs',
    action='store_true',
    help='Use zero-shot approach for testing instead of few-shot'
)
parser.add_argument(
    '--compare',
    action='store_true',
    help='Compare both few-shot and zero-shot approaches'
)
parser.add_argument(
    '--n_seeds',
    type=int,
    default=1,
    help='Number of inference seeds per (model, date, past_days) cell. '
         '>1 produces multi-seed response files with _seed{N} suffixes and '
         'triggers std reporting in analysis tables (default: 1)'
)
parser.add_argument(
    '--n_judge_runs_per_response',
    type=int,
    default=1,
    help='Number of judge runs per response for judge-noise variance '
         'estimation. >1 produces _judge{K} suffixed files (default: 1)'
)
parser.add_argument(
    '--training_seed',
    type=int,
    default=42,
    help='Seed for the LoRA trainer (init, dropout, data shuffle). '
         'Sweep for training-time variance studies (default: 42)'
)
parser.add_argument(
    '--legacy_collator',
    action='store_true',
    help='Use DataCollatorForLanguageModeling(mlm=False) instead of the '
         'default DataCollatorForCompletionOnlyLM. The legacy collator '
         'computes loss on every token (including the user prompt); the '
         'default completion-only collator masks non-response tokens so '
         'loss is computed only on the assistant response. Pass this flag '
         'to reproduce the pre-cleanup fine-tuning behavior.'
)
parser.add_argument(
    '--num_ctx',
    type=int,
    default=16384,
    help='Override Ollama num_ctx (context window size in tokens). '
         'Default 16384 avoids the silent truncation at 4096 that '
         'corrupted prior experiments (default: 16384)'
)
args = parser.parse_args()


def extract_bucharest_data(path_to_csv_data="date"):
    """
    Extract Bucharest meteorological data from Romanian county CSV files.
    
    Args:
        path_to_csv_data (str): Path to directory containing CSV files
    """
    
    # Create bucuresti folder if it doesn't exist
    bucuresti_folder = Path(path_to_csv_data) / "bucuresti"
    bucuresti_folder.mkdir(exist_ok=True)
    print(f"Created/verified folder: {bucuresti_folder}")
    
    # List all CSV files in the directory
    csv_files = [f for f in os.listdir(path_to_csv_data) if f.endswith('.csv')]
    
    if not csv_files:
        print(f"No CSV files found in {path_to_csv_data}")
        return
    
    print(f"Found {len(csv_files)} CSV files: {csv_files}")
    
    bucharest_files_created = []
    
    for csv_file in csv_files:
        try:
            print(f"\n--- Processing: {csv_file} ---")
            
            # Read the CSV file
            file_path = os.path.join(path_to_csv_data, csv_file)
            df = pd.read_csv(file_path, encoding='utf-8')
            
            print(f"Original data shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            
            # Check if 'Denumire' column exists
            if 'Denumire' not in df.columns:
                print(f"'Denumire' column not found in {csv_file}")
                print(f"Available columns: {list(df.columns)}")
                continue
            
            # Filter for Bucharest data (case insensitive)
            bucharest_mask = df['Denumire'].str.contains('bucure', case=False, na=False)
            bucharest_data = df[bucharest_mask].copy()
            
            print(f"Bucharest data shape: {bucharest_data.shape}")
            
            if bucharest_data.empty:
                print(f"No Bucharest data found in {csv_file}")
                
                # Show unique values in Denumire column for debugging
                unique_locations = df['Denumire'].unique()
                print(f"Available locations in file: {unique_locations[:10]}...")  # Show first 10
                continue
            
            # Display Bucharest locations found
            bucharest_locations = bucharest_data['Denumire'].unique()
            print(f"Found Bucharest locations: {bucharest_locations}")
            
            # Create output filename
            file_name, file_ext = os.path.splitext(csv_file)
            output_filename = f"{file_name}_Bucuresti{file_ext}"
            output_path = bucuresti_folder / output_filename
            
            # Save the filtered data
            bucharest_data.to_csv(output_path, index=False, encoding='utf-8')
            print(f"Saved: {output_path}")
            
            # Show some statistics
            print(f"  - Total rows: {len(bucharest_data)}")
            if 'Data' in bucharest_data.columns:
                try:
                    date_range = pd.to_datetime(bucharest_data['Data'])
                    print(f"  - Date range: {date_range.min()} to {date_range.max()}")
                except:
                    print(f"  - Date column exists but couldn't parse dates")
            
            bucharest_files_created.append(output_filename)
            
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
            continue
    
    # Summary
    print(f"\n{'='*60}")
    print(f"EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total files processed: {len(csv_files)}")
    print(f"Bucharest files created: {len(bucharest_files_created)}")
    print(f"Output folder: {bucuresti_folder}")
    
    if bucharest_files_created:
        print(f"\nFiles created:")
        for file in bucharest_files_created:
            file_path = bucuresti_folder / file
            if file_path.exists():
                file_size = file_path.stat().st_size / 1024  # Size in KB
                print(f"  ✓ {file} ({file_size:.1f} KB)")
    else:
        print(f"\nNo Bucharest data files were created.")
        print(f"   Check if 'Denumire' column contains Bucharest locations.")


def debug_csv_structure(path_to_csv_data="date"):
    """
    Debug function to understand the structure of CSV files and available locations.
    """
    csv_files = [f for f in os.listdir(path_to_csv_data) if f.endswith('.csv')]
    
    print(f"{'='*60}")
    print(f"CSV FILES DEBUG INFO")
    print(f"{'='*60}")
    
    for csv_file in csv_files:
        try:
            print(f"\n--- {csv_file} ---")
            
            file_path = os.path.join(path_to_csv_data, csv_file)
            df = pd.read_csv(file_path, encoding='utf-8', nrows=5)  # Just first 5 rows for structure
            
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            
            if 'Denumire' in df.columns:
                # Read full file to get all unique locations
                full_df = pd.read_csv(file_path, encoding='utf-8')
                all_locations = full_df['Denumire'].unique()
                
                # Look for Bucharest-related locations
                bucharest_locations = [loc for loc in all_locations if 'bucure' in str(loc).lower()]
                
                print(f"Total unique locations: {len(all_locations)}")
                print(f"Bucharest-related locations: {bucharest_locations}")
                
                if not bucharest_locations:
                    print(f"Sample locations: {all_locations[:10]}")
            else:
                print(f"No 'Denumire' column found")
                
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")


def create_manually_cod_table():
    """
    Manually extracted data from COD 4677 meteorological table.
    Creates a CSV with two columns: Cifra de cod, Semnificatia
    """
    
    # Manually extracted data from the images
    data = [
        # ww= 00-19 section
        ("00", "Evoluția norilor nu a fost observată sau această evoluție nu a putut fi urmărită"),
        ("01", "Nori, în ansamblu, în rărire, sau devin mai puțin groși"),
        ("02", "Starea cerului, în ansamblu, nu s-a schimbat"),
        ("03", "Nori în formare sau pe cale de a se dezvolta"),
        ("04", "Vizibilitate redusă din cauza fumului, spre exemplu, focuri de mărăcini sau incendii de pădure, fumuri industriale sau ceață vulcanică"),
        ("05", "Pâclă"),
        ("06", "Praf în suspensie în aer, generalizat, dar nerăspândit de vânt la stație sau în apropierea acesteia. În momentul observației"),
        ("07", "Praf sau nisip ridicat de vânt la stație sau în apropierea acesteia, în cursul orei precedente sau în cursul orei de praf sau de nisip bine dezvoltate și care a observa furtuna de praf sau de nisip. În momentul observației"),
        ("08", "Vârtejuri de praf sau de nisip bine dezvoltate la stație sau în apropierea acesteia, în cursul orei precedente, dar se pare că în momentul observației furtuna de praf sau de nisip"),
        ("09", "Furtună de praf sau de nisip observată la stație în ora precedentă sau în câmpul vizual al stației în momentul observației"),
        ("10", "Aer ceţos"),
        ("11", "Strat subțire de ceață sau de ceață"),
        ("12", "Înghețată la stație, cu o grosime care să nu depășească 2 m de la suprafața terestră. În cazul stațiilor de pe mare - mai mult sau mai puțin continuu."),
        ("13", "Fulgere, nu se aude tunetul"),
        ("14", "Precipitații în câmpul vizual, care nu ating solul sau suprafața mării"),
        ("15", "Precipitații în câmpul vizual, care ating solul sau suprafața mării, dar la distanță de stație (ceea ce apreciază la mai mult de 5 km de stație)"),
        ("16", "Precipitații în câmpul vizual, care ating solul sau suprafața mării, la mai puțin de 5 km de stație, dar nu chiar la stație"),
        ("17", "Oraj, dar neregulat de precipitații în momentul observației. La stație sau în câmpul vizual al acesteia în cursul orei precedente sau în"),
        ("18", "Vijelle"),
        
        # ww= 20-29 section
        ("19", "Trombă (e) pe uscat sau pe mare, nori de tornadă sau pâcluri de apă în cursul orei precedente sau în momentul observației"),
        ("20", "Burniță (care nu înghează) sau zăpadă graunțoasă"),
        ("21", "Ploaie (care nu înghează)"),
        ("22", "Ninsoare"),
        ("23", "Lapoviță sau granule de ghează"),
        ("24", "Burniță sau ploaie care înghează"),
        ("25", "Aversă (e) de ploaie"),
        ("26", "Aversă (e) de ninsoare sau lapoviță"),
        ("27", "Aversă (e) de grindină, măzăriche moale, măzăriche tare sau aversă de ploaie și grindină sau aversă de măzăriche moale sau măzăriche tare"),
        ("28", "Ceață sau ceață înghețată"),
        ("29", "Oraj (cu sau fără precipitații)"),
        
        # ww= 30-39 section
        ("30", "Furtună de praf sau de nisip, transport de zăpadă la sol sau la înălțime la stație în cursul orei precedente"),
        ("31", "Furtună de praf sau de nisip, slabă sau moderată - fără schimbare apreciabilă în cursul orei precedente"),
        ("32", "Furtună de praf sau de nisip, slabă sau moderată - a început sau s-a intensificat în cursul orei precedente"),
        ("33", "Furtună de praf sau de nisip, slabă sau moderată - a slăbit în cursul orei precedente"),
        ("34", "Furtună de praf sau de nisip, violentă - fără schimbare apreciabilă în cursul orei precedente"),
        ("35", "Furtună de praf sau de nisip, violentă - a început sau s-a intensificat în cursul orei precedente"),
        ("36", "Transport de zăpadă, slab sau moderat - în general, în straturile joase (sub nivelul stației)"),
        ("37", "Transport de zăpadă, puternic - în general, în straturile joase (sub nivelul observatorului)"),
        ("38", "Transport de zăpadă, slab sau moderat - în general, la înălțime (mai sus de nivelul observatorului)"),
        ("39", "Transport de zăpadă, puternic"),
        
        # ww= 40-49 section
        ("40", "Ceață sau ceață înghețată la distanță. În momentul observației, care se întinde la un nivel mai sus decât ochiul observatorului. În cursul orei precedente nu a fost ceață la stație"),
        ("41", "Ceață sau ceață înghețată în bancuri"),
        ("42", "Ceață sau ceață înghețată cu cer vizibil - s-a subțiat în cursul orei precedente"),
        ("43", "Ceață sau ceață înghețată cu cer invizibil"),
        ("44", "Ceață sau ceață înghețată cu cer vizibil - fără schimbare apreciabilă în cursul orei precedente"),
        ("45", "Ceață sau ceață înghețată cu cer invizibil"),
        ("46", "Ceață sau ceață înghețată cu cer vizibil - a început sau a devenit mai groasă în cursul orei precedente"),
        ("47", "Ceață sau ceață înghețată cu cer invizibil"),
        
        # ww= 50-59 section
        ("50", "Burniță care nu înghează, intermitentă - slabă în momentul observației"),
        ("51", "Burniță care nu înghează, continuă - slabă în momentul observației"),
        ("52", "Burniță care nu înghează, intermitentă - moderată în momentul observației"),
        ("53", "Burniță care nu înghează, continuă - moderată în momentul observației"),
        ("54", "Burniță care nu înghează, intermitentă - puternică (densă) în momentul observației"),
        ("55", "Burniță care nu înghează, continuă - puternică (densă) în momentul observației"),
        ("56", "Burniță care înghează, slabă (depune polei)"),
        ("57", "Burniță care înghează, moderată sau puternică (densă)(depune polei)"),
        ("58", "Burniță și ploaie, slabă"),
        ("59", "Burniță și ploaie, moderată sau puternică"),
        
        # ww= 60-69 section
        ("60", "Ploaie care nu înghează, intermitentă - slabă în momentul observației"),
        ("61", "Ploaie care nu înghează, continuă - slabă în momentul observației"),
        ("62", "Ploaie care nu înghează, intermitentă - moderată în momentul observației"),
        ("63", "Ploaie care nu înghează, continuă - moderată în momentul observației"),
        ("64", "Ploaie care nu înghează, intermitentă - puternică în momentul observației"),
        ("65", "Ploaie care nu înghează, continuă - puternică în momentul observației"),
        ("66", "Ploaie care înghează, moderată sau puternică (depune polei)"),
        ("67", "Ploaie care înghează, moderată sau puternică (depune polei)"),
        ("68", "Ploaie (sau burniță) și ninsoare (lapoviță), slabă"),
        ("69", "Ploaie (sau burniță) și ninsoare (lapoviță), moderată sau puternică"),
        
        # ww= 70-79 section
        ("70", "Ninsoare intermitentă - slabă în momentul observației"),
        ("71", "Ninsoare continuă - slabă în momentul observației"),
        ("72", "Ninsoare intermitentă - moderată în momentul observației"),
        ("73", "Ninsoare continuă - moderată în momentul observației"),
        ("74", "Ninsoare intermitentă - puternică în momentul observației"),
        ("75", "Ninsoare continuă - puternică în momentul observației"),
        ("76", "Ace de ghează (cu sau fără ceață)"),
        ("77", "Ninsoare graunțoasă (cu sau fără ceață)"),
        ("78", "Steluțe de ninsoare, izolate (cu sau fără ceață)"),
        ("79", "Granule de ghează"),
        
        # ww= 80-99 section
        ("80", "Aversă (e) de ploaie, slabă (e)"),
        ("81", "Aversă (e) de ploaie, moderată (e) sau puternică (e)"),
        ("82", "Aversă (e) de ploaie, violentă (e)"),
        ("83", "Aversă (e) de lapoviță, slabă (e)"),
        ("84", "Aversă (e) de lapoviță, moderată (e) sau puternică (e)"),
        ("85", "Aversă (e) de ninsoare, slabă (e)"),
        ("86", "Aversă (e) de ninsoare, moderată (e) sau puternică (e)"),
        ("87", "Aversă de măzăriche moale sau slabă (e) măzăriche tare cu sau fără ploaie ori lapoviță - moderată (e) sau puternică (e)"),
        ("88", "Aversă (e) de grindină cu sau fără ploaie, ninsoare sau cu lapoviță, neînsoțite de tunet - slabă (e)"),
        ("89", "Aversă (e) de grindină cu sau fără ploaie, ninsoare sau cu lapoviță, neînsoțite de tunet - moderată (e) sau puternică (e)"),
        ("90", "Aversă (e) de grindină cu sau fără ploaie, ninsoare sau cu lapoviță, neînsoțite de tunet - moderată (e) sau puternică (e)"),
        ("91", "Ploaie slabă în momentul observației - oraj în cursul orei precedente, dar nu în momentul observației"),
        ("92", "Ploaie moderată sau puternică în momentul observației - oraj în cursul orei prece-dente, dar nu în momentul observației"),
        ("93", "Ninsoare sau lapoviță ori grindină, măzăriche tare sau măzăriche moale, slabă în momentul observației - oraj în cursul orei prece-dente, dar nu în momentul observației"),
        ("94", "Ninsoare sau lapoviță, ori grindină, măzăriche tare sau măzăriche moale, moderată sau puternică în momentul observației - oraj în cursul orei prece-dente, dar nu în momentul observației"),
        ("95", "Oraj slab sau moderat, fără grindină, măzăriche tare sau măzăriche moale, dar cu ploaie, ninsoare sau cu lapoviță în momentul observației - oraj în momentul observației"),
        ("96", "Oraj slab sau moderat cu grindină, măzăriche tare sau măzăriche moale în momentul observației - oraj în momentul observației"),
        ("97", "Oraj puternic, fără grindină, măzăriche tare sau măzăriche moale, dar cu ploaie, ninsoare sau cu lapoviță în momentul observației - oraj în momentul observației"),
        ("98", "Oraj cu furtună de praf sau de nisip în momentul observației - oraj în momentul observației"),
        ("99", "Oraj puternic cu grindină, măzăriche tare sau măzăriche moale în momentul observației - oraj în momentul observației")
    ]
    
    # Create DataFrame
    df = pd.DataFrame(data, columns=['Cifra de cod', 'Semnificatia'])
    
    return df

def save_manually_cod_table():
    """
    Create and save the COD 4677 table as CSV file.
    """
    print("Creating COD 4677 meteorological codes table...")
    
    # Create the table
    df = create_manually_cod_table()
    
    # Display info
    print(f"Successfully created table with {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    print(f"Code range: {df['Cifra de cod'].min()} to {df['Cifra de cod'].max()}")
    
    # Save to CSV
    filename = "cod_4677_meteorological_codes.csv"
    df.to_csv(filename, index=False, encoding='utf-8')
    print(f"Table saved as: {filename}")
    
    # Display first and last few rows
    print("\nFirst 5 rows:")
    print(df.head().to_string(index=False))
    
    print("\nLast 5 rows:")
    print(df.tail().to_string(index=False))
    
    # Show some statistics
    print(f"\nStatistics:")
    print(f"- Total codes: {len(df)}")
    print(f"- Codes 00-19: {len(df[df['Cifra de cod'].astype(int) <= 19])}")
    print(f"- Codes 20-29: {len(df[(df['Cifra de cod'].astype(int) >= 20) & (df['Cifra de cod'].astype(int) <= 29)])}")
    print(f"- Codes 30-39: {len(df[(df['Cifra de cod'].astype(int) >= 30) & (df['Cifra de cod'].astype(int) <= 39)])}")
    print(f"- Codes 40-49: {len(df[(df['Cifra de cod'].astype(int) >= 40) & (df['Cifra de cod'].astype(int) <= 49)])}")
    print(f"- Codes 50-59: {len(df[(df['Cifra de cod'].astype(int) >= 50) & (df['Cifra de cod'].astype(int) <= 59)])}")
    print(f"- Codes 60-69: {len(df[(df['Cifra de cod'].astype(int) >= 60) & (df['Cifra de cod'].astype(int) <= 69)])}")
    print(f"- Codes 70-79: {len(df[(df['Cifra de cod'].astype(int) >= 70) & (df['Cifra de cod'].astype(int) <= 79)])}")
    print(f"- Codes 80-99: {len(df[df['Cifra de cod'].astype(int) >= 80])}")
    
    return df


class PDFTableExtractor:
    def __init__(self, pdf_path: str):
        """
        Initialize the PDF table extractor.
        
        Args:
            pdf_path (str): Path to the PDF file
        """
        self.pdf_path = pdf_path
    
    def debug_page_content(self, page_number: int, title_pattern: str = None) -> None:
        """Debug helper to see page content and search for patterns."""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                if page_number > len(pdf.pages) or page_number < 1:
                    print(f"Page {page_number} not found in PDF")
                    return
                
                page = pdf.pages[page_number - 1]
                text = page.extract_text()
                
                print(f"=== PAGE {page_number} CONTENT ===")
                if text:
                    lines = text.split('\n')[:20]  # First 20 lines
                    for i, line in enumerate(lines):
                        print(f"{i+1:2d}: {line}")
                    
                    if title_pattern:
                        matches = re.findall(title_pattern, text, re.IGNORECASE)
                        print(f"\nPattern '{title_pattern}' matches: {matches}")
                        
                        # Try different variations
                        variations = [
                            title_pattern.replace(' ', r'\s+'),  # flexible whitespace
                            title_pattern.replace(' ', '.*?'),   # any characters between
                            f".*{title_pattern}.*",              # anywhere in line
                        ]
                        
                        for var in variations:
                            if re.search(var, text, re.IGNORECASE | re.DOTALL):
                                print(f"Found with pattern: {var}")
                
                tables = page.extract_tables()
                print(f"\nFound {len(tables)} tables on page {page_number}")
                
                # Show preview of each table
                for i, table in enumerate(tables):
                    if table and len(table) > 0:
                        print(f"\n--- Table {i+1} ---")
                        print(f"Dimensions: {len(table)} rows x {len(table[0]) if table[0] else 0} columns")
                        if len(table) > 0:
                            print(f"Header: {table[0][:3]}...")  # First 3 columns of header
                        if len(table) > 1:
                            print(f"First row: {table[1][:3]}...")  # First 3 columns of first data row
                
        except Exception as e:
            print(f"Debug error: {e}")
    
    def extract_multipage_table_by_headers(self, 
                                          headers_to_find: List[str], 
                                          start_page: int,
                                          max_pages: int = 10,
                                          exact_match: bool = False) -> Optional[pd.DataFrame]:
        """
        Extract a table that spans multiple pages based on headers.
        
        Args:
            headers_to_find (List[str]): List of header names to look for
            start_page (int): Starting page number
            max_pages (int): Maximum number of pages to check for continuation
            exact_match (bool): If True, headers must match exactly
            
        Returns:
            pd.DataFrame: Combined table from multiple pages or None if not found
        """
        try:
            print(f"=== EXTRACTING MULTIPAGE TABLE STARTING FROM PAGE {start_page} ===")
            
            # First, find the table on the starting page
            first_table = self.extract_table_by_headers(headers_to_find, start_page, exact_match)
            
            if first_table is None:
                print(f"No table with matching headers found on starting page {start_page}")
                return None
            
            print(f"Found initial table on page {start_page} with {len(first_table)} rows")
            
            # Store all table parts
            table_parts = [first_table]
            current_page = start_page + 1
            
            # Check subsequent pages for continuation
            for page_offset in range(1, max_pages + 1):
                current_page = start_page + page_offset
                
                print(f"\n--- Checking page {current_page} for continuation ---")
                
                # Check if this page has a continuation of the table
                continuation_table = self._extract_table_continuation(
                    headers_to_find, current_page, first_table.columns.tolist(), exact_match
                )
                
                if continuation_table is not None and not continuation_table.empty:
                    print(f"Found continuation on page {current_page} with {len(continuation_table)} rows")
                    table_parts.append(continuation_table)
                else:
                    print(f"No continuation found on page {current_page}, stopping search")
                    break
            
            # Combine all table parts
            if len(table_parts) == 1:
                print(f"\nTable found only on page {start_page}")
                return table_parts[0]
            else:
                print(f"\nCombining table parts from {len(table_parts)} pages...")
                combined_table = pd.concat(table_parts, ignore_index=True)
                print(f"Combined table has {len(combined_table)} total rows")
                return combined_table
                
        except Exception as e:
            print(f"Error extracting multipage table: {e}")
            return None

    def _extract_table_continuation(self, 
                                   headers_to_find: List[str], 
                                   page_number: int,
                                   expected_columns: List[str],
                                   exact_match: bool = False) -> Optional[pd.DataFrame]:
        """
        Extract a table continuation from a specific page.
        
        Args:
            headers_to_find (List[str]): Original headers to look for
            page_number (int): Page number to check
            expected_columns (List[str]): Expected column names from the first table
            exact_match (bool): Whether to use exact matching
            
        Returns:
            pd.DataFrame: Table continuation or None if not found
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                if page_number > len(pdf.pages) or page_number < 1:
                    return None
                
                page = pdf.pages[page_number - 1]
                tables = page.extract_tables()
                
                if not tables:
                    return None
                
                # Check each table on the page
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 1:
                        continue
                    
                    # Get potential header row
                    potential_header = table[0]
                    
                    # Case 1: Table continues with repeated headers
                    if self._headers_match(potential_header, headers_to_find, exact_match):
                        print(f"  Found table with repeated headers (table {table_idx + 1})")
                        # Skip the header row and return data
                        if len(table) > 1:
                            df = pd.DataFrame(table[1:], columns=expected_columns)
                            return self._clean_table(df)
                    
                    # Case 2: Table continues without headers (data directly)
                    elif self._looks_like_continuation(table, expected_columns):
                        print(f"  Found table continuation without headers (table {table_idx + 1})")
                        # Use the data as-is with expected column names
                        df = pd.DataFrame(table, columns=expected_columns)
                        return self._clean_table(df)
                
                return None
                
        except Exception as e:
            print(f"Error checking continuation on page {page_number}: {e}")
            return None

    def _looks_like_continuation(self, table: List[List], expected_columns: List[str]) -> bool:
        """
        Check if a table looks like a continuation (data without headers).
        
        Args:
            table: Raw table data
            expected_columns: Expected column structure
            
        Returns:
            bool: True if this looks like a table continuation
        """
        if not table or len(table) < 1:
            return False
        
        # Check if the number of columns matches
        first_row = table[0]
        if len(first_row) != len(expected_columns):
            return False
        
        # Check if the first row looks like data rather than headers
        # (This is a heuristic - you might need to adjust based on your data)
        first_cell = str(first_row[0]).strip() if first_row[0] else ""
        
        # If first cell is numeric or matches expected data patterns, it's likely data
        if first_cell.isdigit() or any(char.isdigit() for char in first_cell):
            return True
        
        # Additional heuristics can be added here based on your specific data patterns
        
        return False

    def extract_table_by_headers(self, 
                                headers_to_find: List[str], 
                                page_number: int,
                                exact_match: bool = False) -> Optional[pd.DataFrame]:
        """
        Extract a table based on specific column headers.
        
        Args:
            headers_to_find (List[str]): List of header names to look for
            page_number (int): Page number where the table should be found
            exact_match (bool): If True, all headers must match exactly; if False, use partial matching
            
        Returns:
            pd.DataFrame: Extracted table or None if not found
        """
        try:
            # Using pdfplumber (better for text extraction)
            table_df = self._extract_by_headers_pdfplumber(headers_to_find, page_number, exact_match)
            
            if table_df is not None:
                return table_df
            
        except Exception as e:
            print(f"Error extracting table: {e}")
            return None
        

    def _extract_by_headers_pdfplumber(self, 
                                      headers_to_find: List[str], 
                                      page_number: int,
                                      exact_match: bool = False) -> Optional[pd.DataFrame]:
        """Extract table using pdfplumber based on headers."""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                if page_number > len(pdf.pages) or page_number < 1:
                    print(f"Page {page_number} not found in PDF")
                    return None
                
                page = pdf.pages[page_number - 1]  # Convert to 0-indexed
                
                # Extract all tables from the page
                tables = page.extract_tables()
                
                if not tables:
                    print(f"No tables found on page {page_number}")
                    return None
                
                print(f"Found {len(tables)} table(s) on page {page_number}")
                
                # Check each table for matching headers
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 1:
                        continue
                    
                    # Get the header row
                    header_row = table[0]
                    print(f"\nChecking table {table_idx + 1}:")
                    print(f"Headers: {header_row}")
                    
                    # Check if this table has the required headers
                    if self._headers_match(header_row, headers_to_find, exact_match):
                        print(f"Found matching table {table_idx + 1}")
                        
                        # Create DataFrame
                        table_df = pd.DataFrame(table[1:], columns=table[0])
                        return self._clean_table(table_df)
                    else:
                        print(f"Table {table_idx + 1} headers don't match")
                
                print("No table found with matching headers")
                return None
                
        except Exception as e:
            print(f"Error with pdfplumber: {e}")
            return None


    def _headers_match(self, table_headers: List, target_headers: List[str], exact_match: bool = False) -> bool:
        """Check if table headers match the target headers."""
        # Clean and normalize headers
        clean_table_headers = []
        for header in table_headers:
            if header is not None:
                # Remove newlines, normalize whitespace, and convert to lowercase
                clean_header = str(header).replace('\n', ' ').replace('\r', ' ')
                clean_header = ' '.join(clean_header.split())  # Normalize whitespace
                clean_header = clean_header.strip().lower()
                clean_table_headers.append(clean_header)
        
        # Also clean target headers
        clean_target_headers = []
        for header in target_headers:
            clean_header = header.replace('\n', ' ').replace('\r', ' ')
            clean_header = ' '.join(clean_header.split())  # Normalize whitespace
            clean_header = clean_header.strip().lower()
            clean_target_headers.append(clean_header)
        
        print(f"  Table headers (cleaned): {clean_table_headers}")
        print(f"  Target headers (cleaned): {clean_target_headers}")
        
        if exact_match:
            # All target headers must be exactly present
            for target in clean_target_headers:
                if target not in clean_table_headers:
                    return False
            return True
        else:
            # Use partial matching - target headers can be contained within table headers
            matches = 0
            for i, target in enumerate(clean_target_headers):
                target_found = False
                for j, table_header in enumerate(clean_table_headers):
                    # Check both directions: target in table_header AND table_header in target
                    if (target in table_header or table_header in target or 
                        self._fuzzy_header_match(target, table_header)):
                        print(f"Match: '{target}' ≈ '{table_header}'")
                        matches += 1
                        target_found = True
                        break
                
                if not target_found:
                    print(f"No match for: '{target}'")
            
            # Require at least 70% of target headers to match
            match_ratio = matches / len(clean_target_headers)
            print(f"  Match ratio: {matches}/{len(clean_target_headers)} = {match_ratio:.2f}")
            return match_ratio >= 0.7

    def _fuzzy_header_match(self, target: str, table_header: str) -> bool:
        """Perform fuzzy matching for headers with potential formatting differences."""
        # Remove common words and check if key terms match
        target_words = set(target.split())
        table_words = set(table_header.split())
        
        # Check if significant words overlap
        common_words = target_words.intersection(table_words)
        if len(common_words) >= min(len(target_words), len(table_words)) * 0.6:
            return True
        
        # Check for character similarity (simple approach)
        target_chars = ''.join(target.split())
        table_chars = ''.join(table_header.split())
        
        if len(target_chars) > 0 and len(table_chars) > 0:
            # Simple character overlap check
            common_chars = sum(1 for char in target_chars if char in table_chars)
            similarity = common_chars / max(len(target_chars), len(table_chars))
            return similarity >= 0.7
        
        return False

    
    def _clean_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and format the extracted table."""
        if df is None or df.empty:
            return df
        
        # Remove completely empty rows and columns
        df = df.dropna(how='all').loc[:, df.notna().any()]
        
        # Clean column names
        df.columns = [str(col).strip() if col and str(col) != 'nan' else f"Column_{i}" 
                     for i, col in enumerate(df.columns)]
        
        # Clean cell values
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
                # Replace 'nan' strings with actual NaN
                df[col] = df[col].replace(['nan', 'None', '', 'NaN'], pd.NA)
        
        return df


def extract_multipage_cod_table(pdf_path: str, 
                               start_page: int, 
                               headers: List[str],
                               max_pages: int = 10) -> Optional[pd.DataFrame]:
    """
    Extract a multi-page table with specific headers.
    
    Args:
        pdf_path (str): Path to the PDF file
        start_page (int): Starting page number
        headers (List[str]): List of header names to search for
        max_pages (int): Maximum pages to check for continuation
    
    Returns:
        pd.DataFrame: Combined table from multiple pages
    """
    extractor = PDFTableExtractor(pdf_path)
    
    print(f"=== EXTRACTING MULTIPAGE TABLE ===")
    print(f"Starting page: {start_page}")
    print(f"Target headers: {headers}")
    print(f"Max pages to check: {max_pages}")
    
    return extractor.extract_multipage_table_by_headers(headers, start_page, max_pages)


def extract_single_page_cod_table(pdf_path: str, page_number: int = 298) -> Optional[pd.DataFrame]:
    """
    Specific function to extract the COD 1600 table from page 298 based on headers.
    
    Args:
        pdf_path (str): Path to the PDF file
        page_number (int): Page number (default 298)
    
    Returns:
        pd.DataFrame: Extracted table
    """
    extractor = PDFTableExtractor(pdf_path)
    
    # Define the target headers for COD 1600 table
    target_headers = ["Cifră de cod", "Înălţimea bazei norilor"]
    
    # First, debug the page to see what's available
    print("=== DEBUGGING PAGE CONTENT ===")
    extractor.debug_page_content(page_number, "COD 1600")
    print("\n=== EXTRACTING TABLE BY HEADERS ===")
    
    return extractor.extract_table_by_headers(target_headers, page_number)


def process_bucharest_weather_codes():
    """
    Process Bucharest weather data by correlating ww and ix codes with meteorological meanings.
    """
    
    print("=" * 60)
    print("WEATHER CODE PROCESSING FOR BUCHAREST")
    print("=" * 60)
    
    # Define paths
    bucuresti_folder = Path("date/bucuresti")
    target_file = "SirDate_1748514797752_Bucuresti.csv"
    target_path = bucuresti_folder / target_file
    
    # Check if target file exists
    if not target_path.exists():
        print(f"Target file not found: {target_path}")
        return None
    
    # List current working directory to find reference tables
    print("Available files in current directory:")
    current_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    for file in current_files:
        print(f"  - {file}")
    
    # Load reference tables
    try:
        print(f"\n--- Loading Reference Tables ---")
        
        # Load COD 4677 table
        cod_4677_path = "cod_4677_meteorological_codes.csv"
        if os.path.exists(cod_4677_path):
            cod_4677_df = pd.read_csv(cod_4677_path, encoding='utf-8')
            print(f"Loaded {cod_4677_path}: {cod_4677_df.shape}")
        else:
            print(f"{cod_4677_path} not found")
            return None
            
        # Load multipage table
        cod_multipage_path = "cod_4680_multipage_table.csv"
        if os.path.exists(cod_multipage_path):
            cod_multipage_df = pd.read_csv(cod_multipage_path, encoding='utf-8')
            print(f"Loaded {cod_multipage_path}: {cod_multipage_df.shape}")
        else:
            print(f"{cod_multipage_path} not found")
            return None
            
    except Exception as e:
        print(f"Error loading reference tables: {e}")
        return None
    
    # Load target data
    try:
        print(f"\n--- Loading Target Data ---")
        df = pd.read_csv(target_path, encoding='utf-8')
        print(f"Loaded {target_file}: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        
    except Exception as e:
        print(f"Error loading target file: {e}")
        return None
    
    # Extract last 2 columns (ww and ix)
    if len(df.columns) < 2:
        print(f"Not enough columns in the data. Found: {len(df.columns)}")
        return None
    
    # Get the last 2 columns
    ww_col = df.columns[-2]  # Second to last column (ww)
    ix_col = df.columns[-1]  # Last column (ix)
    
    print(f"\n--- Extracting Last 2 Columns ---")
    print(f"WW column: '{ww_col}'")
    print(f"IX column: '{ix_col}'")
    
    # Extract and preprocess the columns
    ww_data = df[ww_col].copy()
    ix_data = df[ix_col].copy()
    
    print(f"Original WW data sample: {ww_data.head()}")
    print(f"Original IX data sample: {ix_data.head()}")
    
    # Preprocess WW column: replace NaN and "//" with "*"
    print(f"\n--- Preprocessing WW Column ---")
    print(f"Original NaN count: {ww_data.isna().sum()}")
    print(f"Original '//' count: {(ww_data == '//').sum()}")
    
    # Replace NaN and "//" with "*"
    ww_data = ww_data.fillna("*")
    ww_data = ww_data.replace("//", "*")
    
    print(f"After preprocessing - '*' count: {(ww_data == '*').sum()}")
    
    # Preprocess IX column: convert to int
    print(f"\n--- Preprocessing IX Column ---")
    print(f"Original IX data type: {ix_data.dtype}")
    print(f"IX NaN count: {ix_data.isna().sum()}")
    
    # Handle NaN values in IX column (replace with a default value, e.g., 0)
    ix_data = ix_data.fillna(0)
    
    # Convert to int
    try:
        ix_data = ix_data.astype(int)
        print(f"Converted IX to int. New data type: {ix_data.dtype}")
        print(f"IX value range: {ix_data.min()} to {ix_data.max()}")
        print(f"IX unique values: {sorted(ix_data.unique())}")
    except Exception as e:
        print(f"Error converting IX to int: {e}")
        return None
    
    # Create dictionaries for fast lookup
    print(f"\n--- Creating Lookup Dictionaries ---")
    
    # Convert cod_4677 to dictionary (code -> meaning)
    cod_4677_dict = {}
    for _, row in cod_4677_df.iterrows():
        code = str(row['Cifra de cod']).zfill(2)  # Ensure 2 digits with leading zero
        meaning = row['Semnificatia']
        cod_4677_dict[code] = meaning
    
    print(f"COD 4677 dictionary created with {len(cod_4677_dict)} entries")
    print(f"Sample entries: {list(cod_4677_dict.items())[:3]}")
    
    # Convert multipage to dictionary
    cod_multipage_dict = {}
    for _, row in cod_multipage_df.iterrows():
        # Assume first column is code, second is meaning
        code = str(row.iloc[0]).zfill(2) if pd.notna(row.iloc[0]) else ""
        meaning = row.iloc[1] if pd.notna(row.iloc[1]) else ""
        if code and meaning:
            cod_multipage_dict[code] = meaning
    
    print(f"Multipage dictionary created with {len(cod_multipage_dict)} entries")
    if cod_multipage_dict:
        print(f"Sample entries: {list(cod_multipage_dict.items())[:3]}")
    
    # Process weather codes based on ix values
    print(f"\n--- Processing Weather Codes ---")
    
    fenomen_data = []
    stats = {"nu_avem_fenomen": 0, "cod_4677": 0, "cod_multipage": 0, "not_found": 0}
    
    for i, (ww_val, ix_val) in enumerate(zip(ww_data, ix_data)):
        if ww_val == "*":
            fenomen = "Nu avem fenomen"
            stats["nu_avem_fenomen"] += 1
        else:
            # Convert ww_val to string and pad with zeros
            ww_code = str(ww_val).zfill(2)
            
            if 1 <= ix_val <= 3:
                # Use cod_4677
                if ww_code in cod_4677_dict:
                    fenomen = cod_4677_dict[ww_code]
                    stats["cod_4677"] += 1
                else:
                    fenomen = f"Cod necunoscut: {ww_code} (4677)"
                    stats["not_found"] += 1
                    
            elif 4 <= ix_val <= 7:
                # Use cod_multipage
                if ww_code in cod_multipage_dict:
                    fenomen = cod_multipage_dict[ww_code]
                    stats["cod_multipage"] += 1
                else:
                    fenomen = f"Cod necunoscut: {ww_code} (multipage)"
                    stats["not_found"] += 1
            else:
                # IX value outside expected range
                fenomen = f"IX invalid: {ix_val}, WW: {ww_code}"
                stats["not_found"] += 1
        
        fenomen_data.append(fenomen)
        
        # Show progress for every 1000 rows
        if (i + 1) % 1000 == 0:
            print(f"  Processed {i + 1} rows...")
    
    print(f"Processing complete!")
    print(f"Statistics:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")
    
    # Create new dataframe without the last 2 columns and add Fenomen column
    print(f"\n--- Creating Final Dataset ---")
    
    # Remove last 2 columns
    df_final = df.iloc[:, :-2].copy()
    
    # Add Fenomen column
    df_final['Fenomen'] = fenomen_data
    
    print(f"Original shape: {df.shape}")
    print(f"Final shape: {df_final.shape}")
    print(f"New columns: {list(df_final.columns)}")
    
    # Show sample of final data
    print(f"\nSample of final data:")
    print(df_final[['Fenomen']].head(10))
    
    # Save the file
    try:
        df_final.to_csv(target_path, index=False, encoding='utf-8')
        print(f"File saved successfully: {target_path}")
        
        # Verify the saved file
        verification_df = pd.read_csv(target_path, encoding='utf-8')
        print(f"Verification - saved file shape: {verification_df.shape}")
        
    except Exception as e:
        print(f"Error saving file: {e}")
        return None
    
    return df_final

def verify_processing_results():
    """
    Verify the results of the weather code processing.
    """
    print(f"\n" + "=" * 60)
    print("VERIFICATION OF PROCESSING RESULTS")
    print("=" * 60)
    
    # Load the processed file
    target_path = Path("date/bucuresti/SirDate_1748514797752_Bucuresti.csv")
    
    if not target_path.exists():
        print(f"Processed file not found: {target_path}")
        return
    
    try:
        df = pd.read_csv(target_path, encoding='utf-8')
        
        print(f"Processed file loaded successfully")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        
        if 'Fenomen' in df.columns:
            fenomen_counts = df['Fenomen'].value_counts()
            print(f"\nTop 10 most frequent weather phenomena:")
            print(fenomen_counts.head(10))
            
            # Count special cases
            nu_avem_count = (df['Fenomen'] == 'Nu avem fenomen').sum()
            necunoscut_count = df['Fenomen'].str.contains('Cod necunoscut', na=False).sum()
            
            print(f"\nSpecial cases:")
            print(f"  - 'Nu avem fenomen': {nu_avem_count}")
            print(f"  - 'Cod necunoscut': {necunoscut_count}")
            print(f"  - Total unique phenomena: {df['Fenomen'].nunique()}")
        
    except Exception as e:
        print(f"Error verifying results: {e}")

def generate_analysis_dates(date_range: Tuple[str, str], past_days: int, output_file: str = "analysis_dates.txt") -> List[str]:
    """
    Generate analysis dates with specified intervals and save to a text file.
    
    Args:
        date_range (Tuple[str, str]): Tuple of (start_date, end_date) in format "yyyy-mm-dd"
        past_days (int): Number of past days needed for each analysis
        output_file (str): Name of the output text file
    
    Returns:
        List[str]: List of generated dates in "yyyy-mm-dd" format
    
    Logic:
        - First analysis date = start_date + past_days
        - Interval between dates = past_days + 1
        - Stop when target date exceeds end_date or insufficient historical data
    """
    
    start_date_str, end_date_str = date_range
    
    # Parse input dates
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date format. Use yyyy-mm-dd format. Error: {e}")
    
    # Validate date range
    if start_date >= end_date:
        raise ValueError("Start date must be before end date")
    
    # Calculate first analysis date
    first_analysis_date = start_date + timedelta(days=past_days)
    
    # Check if first analysis date is valid
    if first_analysis_date > end_date:
        print(f"Warning: Not enough data in range. First possible analysis date ({first_analysis_date}) exceeds end date ({end_date})")
        return []
    
    # Generate analysis dates
    analysis_dates = []
    current_date = first_analysis_date
    interval = past_days + 1
    
    while current_date <= end_date:
        # Check if we have enough historical data for this analysis date
        # We need past_days worth of data before current_date
        required_start_date = current_date - timedelta(days=past_days)
        
        if required_start_date >= start_date:
            analysis_dates.append(current_date.strftime("%Y-%m-%d"))
            print(f"Added analysis date: {current_date.strftime('%Y-%m-%d')} (requires data from {required_start_date.strftime('%Y-%m-%d')} to {(current_date - timedelta(days=1)).strftime('%Y-%m-%d')})")
        else:
            print(f"Skipping {current_date.strftime('%Y-%m-%d')}: insufficient historical data (would need data from {required_start_date.strftime('%Y-%m-%d')})")
        
        # Move to next analysis date
        current_date += timedelta(days=interval)
    
    # Save to text file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for date in analysis_dates:
                f.write(f"{date}\n")
        
        print(f"\nSuccessfully saved {len(analysis_dates)} analysis dates to '{output_file}'")
        
    except IOError as e:
        print(f"Error saving to file '{output_file}': {e}")
    
    return analysis_dates

def validate_date_generation(date_range: Tuple[str, str], past_days: int) -> None:
    """
    Validate and demonstrate the date generation logic.
    
    Args:
        date_range: Tuple of (start_date, end_date)
        past_days: Number of past days needed
    """
    
    start_date_str, end_date_str = date_range
    
    print(f"Date Generation Validation")
    print(f"=" * 40)
    print(f"Start date: {start_date_str}")
    print(f"End date: {end_date_str}")
    print(f"Past days required: {past_days}")
    print(f"Interval: {past_days + 1} days")
    print(f"First analysis date: {(datetime.strptime(start_date_str, '%Y-%m-%d').date() + timedelta(days=past_days)).strftime('%Y-%m-%d')}")
    print(f"=" * 40)
    
    dates = generate_analysis_dates(date_range, past_days, f"dates_{start_date_str}_to_{end_date_str}_past{past_days}.txt")
    
    print(f"\nGenerated dates: {dates}")
    return dates


if __name__ == "__main__":

    if args.tables:
        pdf_path = Path("date") / "VOLUMUL_I_Ed_II_08nov2017.pdf"

        extractor = PDFTableExtractor(str(pdf_path))

        print("Single page extraction")
        table = extract_single_page_cod_table(str(pdf_path), SINGLE_PAGE_TABLE)

        if table is not None:
            print(f"Extracted single-page table: {table.shape}")
            table.to_csv("cod_1600_single_page.csv", index=False)
            print("Saved to cod_1600_single_page.csv")

        print("Multipage extraction")
        multipage_headers = ["Cifra de cod", "Semnificatie"]
        multipage_table = extract_multipage_cod_table(
            str(pdf_path), MULTIPAGE_TABLE, multipage_headers, max_pages=2,
        )

        if multipage_table is not None:
            print(f"Extracted multipage table: {multipage_table.shape}, {len(multipage_table)} rows")
            multipage_table.to_csv("cod_4680_multipage_table.csv", index=False)
            print("Saved to cod_4680_multipage_table.csv")
        else:
            print("WARNING: multipage table not found")

        table = save_manually_cod_table()
        print("All tables created")

    elif args.bucharest:
        path_to_csv_data = "date"
        print("Step 1: debugging CSV structure")
        debug_csv_structure(path_to_csv_data)
        print("Step 2: extracting Bucharest data")
        extract_bucharest_data(path_to_csv_data)
        print("Processing complete")

    elif args.phenomena_codes:
        result = process_bucharest_weather_codes()
        if result is not None:
            verify_processing_results()
            print("Weather code processing complete")
        else:
            print("ERROR: weather code processing failed")

    elif args.timestamp is not None and args.past_days is not None:
        # Single-date branch (PDF-context track)
        result = check_data_availability(args.timestamp, args.past_days)

        if result["sufficient_data"]:
            print(f"Sufficient data available for {args.timestamp}")

            # PDF extraction
            sequential_pdf_data = extract_forecasts_sequential(
                args.timestamp, args.past_days,
            )
            if sequential_pdf_data:
                first_date = list(sequential_pdf_data.keys())[0]
                first_forecast = sequential_pdf_data[first_date]
                print(f"PDF extraction complete: {len(sequential_pdf_data)} dates")

            # CSV extraction
            all_table_data = extract_comprehensive_weather_data(
                args.timestamp, args.past_days,
            )
            if all_table_data:
                wind = all_table_data["wind_analysis"].get("mean_speed_ms")
                if wind is not None:
                    print(f"Wind speed: {wind:.2f} m/s")
                neb = all_table_data["nebulosity_analysis"].get("most_frequent_value")
                if neb is not None:
                    print(f"Most frequent nebulosity: {neb}")
                print(f"Temperature records: {len(all_table_data['daily_temperatures'])}")
                print(f"Precipitation records: {len(all_table_data['daily_precipitation'])}")

            # Prompt generation for each past_days value
            past_days = args.past_days
            for day in range(past_days):
                test_prompt_generation(
                    current_date=args.timestamp,
                    weather_data=all_table_data,
                    pdf_forecasts=sequential_pdf_data,
                    saving_past_days=past_days,
                    past_days=day + 1,
                )

            # Model actions
            if not os.path.exists("models_to_test.txt"):
                print("WARNING: models_to_test.txt not found")
            else:
                with open("models_to_test.txt", "r") as f:
                    models_to_test = [model.strip() for model in f.readlines() if model.strip()]
                print(f"Models to test: {models_to_test}")

                responses_folder = str(
                    Path("responses") / args.timestamp / f"{args.past_days}_past_days"
                )

                if args.download_models:
                    download_models_only(models_to_test)

                elif args.test_models:
                    test_downloaded_models(
                        models_list=models_to_test,
                        past_days=args.past_days,
                        base_date=args.timestamp,
                        keep_alive="10m",
                        n_seeds=args.n_seeds,
                        num_ctx=args.num_ctx,
                    )

                elif args.statistical_analysis:
                    create_analysis_tables(
                        responses_folder=responses_folder,
                        output_date=args.timestamp,
                        output_past_days=args.past_days,
                        reference_text=first_forecast["forecast_text"],
                    )

                elif args.judge_analysis:
                    create_judge_analysis(
                        responses_folder=responses_folder,
                        reference_text=first_forecast["forecast_text"],
                        judge_model=args.judge,
                        n_past_days=args.past_days,
                        n_judge_runs_per_response=args.n_judge_runs_per_response,
                    )

                else:
                    print(
                        "No model action specified. "
                        "Use --download_models (-dm) or --test_models (-tm)."
                    )
        else:
            print(f"Insufficient data for {args.timestamp}")

    elif args.get_test_time_interval is not None and args.past_days is not None:
        # Multi-date branch (GPT-CoT track)
        dates = validate_date_generation(args.get_test_time_interval, args.past_days)

        if not os.path.exists("models_to_test.txt"):
            print("WARNING: models_to_test.txt not found")
        else:
            with open("models_to_test.txt", "r") as f:
                models_to_test = [model.strip() for model in f.readlines() if model.strip()]
            print(f"Models to test: {models_to_test}")

            if args.download_models:
                download_models_only(models_to_test)

        for date in dates:
            result = check_data_availability(date, args.past_days)

            if result["sufficient_data"]:
                print(f"Sufficient data for {date}")
                all_table_data = extract_comprehensive_weather_data(date, args.past_days)

                responses_folder = str(
                    Path("responses") / date / f"{args.past_days}_past_days"
                )

                if args.generate_prompts_gpt:
                    past_days = args.past_days
                    for day in range(past_days):
                        test_prompt_generation_gpt(
                            current_date=date,
                            weather_data=all_table_data,
                            saving_past_days=past_days,
                            past_days=day + 1,
                        )

                elif args.test_models:
                    test_downloaded_models(
                        models_list=models_to_test,
                        past_days=args.past_days,
                        base_date=date,
                        keep_alive="30m",
                        n_seeds=args.n_seeds,
                        num_ctx=args.num_ctx,
                    )

                elif args.statistical_analysis:
                    reference_text = load_reference_text(date)
                    create_analysis_tables_gpt(
                        responses_folder=responses_folder,
                        output_date=date,
                        output_past_days=args.past_days,
                        reference_text=reference_text,
                    )

                elif args.judge_analysis:
                    reference_text = load_reference_text(date)
                    create_judge_analysis(
                        responses_folder=responses_folder,
                        reference_text=reference_text,
                        judge_model=args.judge,
                        n_past_days=args.past_days,
                        n_judge_runs_per_response=args.n_judge_runs_per_response,
                    )
                    # NOTE: generate_judge_analysis_tables is now called
                    # automatically at the end of create_judge_analysis in
                    # the cleaned judge_evaluation.py; the previous explicit
                    # call here was redundant and has been removed.

                else:
                    print(
                        "No model action specified. "
                        "Use --download_models (-dm) or --test_models (-tm)."
                    )
            else:
                print(f"Insufficient data for {date}")

    elif args.generate_training_dataset_for_year is not None:
        year_to_process = args.generate_training_dataset_for_year
        output_folder = f"formatted_diagnoses_{year_to_process}"
        results = extract_yearly_diagnoses_and_format(
            year=year_to_process,
            judge_model=args.judge,
            output_folder=output_folder,
            delay_between_calls=1.0,
        )
        if results:
            validate_yearly_extraction(
                year=year_to_process,
                output_folder=output_folder,
            )
        else:
            print("No results to validate")

    elif args.finetune:
        from prompting.utils.finetune_integration import (
            run_finetuning_pipeline,
            run_comparison_pipeline,
        )

        if not args.year:
            print("ERROR: year is required for fine-tuning. Use --year (-y).")
            exit(1)

        if not args.past_days:
            args.past_days = 4
            print(f"Using default past_days: {args.past_days}")

        if args.compare:
            print(
                f"Starting comparison pipeline: year={args.year}, "
                f"past_days={args.past_days}"
            )
            success = run_comparison_pipeline(args)
            if success:
                print("Comparison pipeline complete")
            else:
                print("ERROR: comparison pipeline failed")

        else:
            approach = "zero-shot" if args.zero_shot else "few-shot"
            print(
                f"Starting {approach} fine-tuning pipeline: year={args.year}, "
                f"past_days={args.past_days}, batch_size={args.batch_size}, "
                f"skip_training={args.skip_training}, skip_testing={args.skip_testing}"
            )
            success = run_finetuning_pipeline(args)
            if success:
                print(f"{approach} fine-tuning pipeline complete")
            else:
                print(f"ERROR: {approach} fine-tuning pipeline failed")

    elif args.select_models:
        generate_gui(n_models=args.n_models)

    else:
        print("No valid arguments provided.")
        parser.print_help()

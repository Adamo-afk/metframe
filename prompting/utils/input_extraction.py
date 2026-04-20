###########################################################################
# ###################### extract_data_from_tables.py ######################
###########################################################################





# import pandas as pd
# from datetime import datetime, timedelta
# from pathlib import Path
# from collections import Counter
# import warnings
# warnings.filterwarnings('ignore')

# def extract_comprehensive_weather_data(target_date_str, past_days):
#     """
#     Extract comprehensive meteorological data including hourly measurements, 
#     daily temperatures, and precipitation data.
    
#     Args:
#         target_date_str (str): Target date in format "yyyy-mm-dd"
#         past_days (int): Number of past meteorological days to extract
    
#     Returns:
#         dict: Comprehensive weather data including:
#             - hourly_data: Raw hourly measurements
#             - wind_speed_mean: Average wind speed (m/s)
#             - nebulosity_mode: Most frequent cloud coverage value
#             - nebulosity_times: Times when mode nebulosity occurred
#             - daily_temperatures: Max/min temperatures for each day
#             - daily_precipitation: Precipitation amounts for each day
#             - summary_stats: Overall statistics
#     """
    
#     print(f"=" * 70)
#     print(f"COMPREHENSIVE WEATHER DATA EXTRACTION - FIXED VERSION")
#     print(f"Target date: {target_date_str}")
#     print(f"Past days: {past_days}")
#     print(f"=" * 70)
    
#     # Define file paths
#     bucuresti_folder = Path("date/bucuresti")
    
#     files = {
#         'hourly': "SirDate_1748514797752_Bucuresti.csv",
#         'temp': "DateZilniceTemp_1748520589580_Bucuresti.csv", 
#         'precip': "DateZilnicePrecip_1748521941631_Bucuresti.csv"
#     }
    
#     # Check if all files exist
#     for file_type, filename in files.items():
#         file_path = bucuresti_folder / filename
#         if not file_path.exists():
#             print(f"❌ {file_type.capitalize()} file not found: {file_path}")
#             return None
    
#     print(f"✅ All required files found")
    
#     # Parse target date
#     try:
#         target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
#         print(f"✅ Parsed target date: {target_date}")
#     except ValueError as e:
#         print(f"❌ Invalid date format: {target_date_str}")
#         return None
    
#     # Calculate meteorological date range
#     start_date = target_date - timedelta(days=past_days)
#     start_datetime = datetime.combine(start_date, datetime.min.time().replace(hour=8, minute=30))
#     end_datetime = datetime.combine(target_date, datetime.min.time().replace(hour=6, minute=30))
    
#     print(f"✅ Meteorological period:")
#     print(f"  Start: {start_datetime}")
#     print(f"  End: {end_datetime}")
    
#     # === STEP 1: Extract hourly data ===
#     print(f"\n--- STEP 1: EXTRACTING HOURLY DATA ---")
    
#     try:
#         hourly_df = pd.read_csv(bucuresti_folder / files['hourly'], encoding='utf-8')
#         print(f"✅ Loaded hourly data: {hourly_df.shape}")
#         print(f"📋 Hourly data columns: {list(hourly_df.columns)}")
        
#         # Convert timestamps
#         hourly_df['Data masurarii'] = pd.to_datetime(hourly_df['Data masurarii'])
        
#         # Filter for the time range
#         hourly_mask = (hourly_df['Data masurarii'] >= start_datetime) & (hourly_df['Data masurarii'] <= end_datetime)
#         hourly_filtered = hourly_df[hourly_mask].copy()
        
#         print(f"✅ Filtered hourly data: {len(hourly_filtered)} records")
#         print(f"  Date range: {hourly_filtered['Data masurarii'].min()} to {hourly_filtered['Data masurarii'].max()}")
        
#     except Exception as e:
#         print(f"❌ Error loading hourly data: {e}")
#         return None
    
#     # === STEP 2: Process wind speed (Rff1) ===
#     print(f"\n--- STEP 2: PROCESSING WIND SPEED ---")
    
#     if 'Rff1' not in hourly_filtered.columns:
#         print(f"❌ 'Rff1' column not found in hourly data")
#         wind_speed_mean = None
#     else:
#         # Calculate wind speed mean (excluding NaN values)
#         wind_speeds = hourly_filtered['Rff1'].dropna()
#         wind_speed_mean = wind_speeds.mean()
        
#         print(f"✅ Wind speed statistics:")
#         print(f"  Total measurements: {len(wind_speeds)}")
#         print(f"  Mean speed: {wind_speed_mean:.2f} m/s")
#         print(f"  Min speed: {wind_speeds.min():.2f} m/s")
#         print(f"  Max speed: {wind_speeds.max():.2f} m/s")
    
#     # === STEP 3: Process nebulosity (Nop) ===
#     print(f"\n--- STEP 3: PROCESSING NEBULOSITY ---")
    
#     if 'Nop' not in hourly_filtered.columns:
#         print(f"❌ 'Nop' column not found in hourly data")
#         nebulosity_mode = None
#         nebulosity_times = []
#     else:
#         # Get nebulosity values (excluding NaN)
#         nebulosity_data = hourly_filtered[['Data masurarii', 'Nop']].dropna()
        
#         if len(nebulosity_data) == 0:
#             print(f"❌ No valid nebulosity data found")
#             nebulosity_mode = None
#             nebulosity_times = []
#         else:
#             # Find the most recurring value
#             nebulosity_counts = Counter(nebulosity_data['Nop'])
#             nebulosity_mode = nebulosity_counts.most_common(1)[0][0]
#             mode_frequency = nebulosity_counts.most_common(1)[0][1]
            
#             # Get times when this mode occurred
#             mode_mask = nebulosity_data['Nop'] == nebulosity_mode
#             nebulosity_times = nebulosity_data[mode_mask]['Data masurarii'].tolist()
            
#             print(f"✅ Nebulosity statistics:")
#             print(f"  Total measurements: {len(nebulosity_data)}")
#             print(f"  Most frequent value: {nebulosity_mode} (occurs {mode_frequency} times)")
#             print(f"  Distribution: {dict(nebulosity_counts)}")
#             print(f"  Times of mode occurrence: {len(nebulosity_times)} timestamps")
            
#             # Show first few times
#             if nebulosity_times:
#                 print(f"  First few occurrences:")
#                 for i, time in enumerate(nebulosity_times[:5]):
#                     hour_minute = time.strftime("%H:%M")
#                     print(f"    {i+1}. {time.date()} at {hour_minute}")
    
#     # === STEP 4: Extract daily temperature data - FIXED ===
#     print(f"\n--- STEP 4: EXTRACTING DAILY TEMPERATURE DATA - FIXED ---")
    
#     try:
#         temp_df = pd.read_csv(bucuresti_folder / files['temp'], encoding='utf-8')
#         print(f"✅ Loaded temperature data: {temp_df.shape}")
#         print(f"📋 Temperature data columns: {list(temp_df.columns)}")
        
#         # Convert timestamps and extract date only
#         temp_df['Data masurarii'] = pd.to_datetime(temp_df['Data masurarii'])
#         temp_df['Date'] = temp_df['Data masurarii'].dt.date
        
#         # Calculate date range for temperature data (past_days + 1 to include target date)
#         temp_start_date = target_date - timedelta(days=past_days)
#         temp_end_date = target_date
        
#         # Filter temperature data
#         temp_mask = (temp_df['Date'] >= temp_start_date) & (temp_df['Date'] <= temp_end_date)
#         temp_filtered = temp_df[temp_mask].copy()
        
#         print(f"✅ Filtered temperature data: {len(temp_filtered)} records")
#         print(f"  Date range: {temp_filtered['Date'].min()} to {temp_filtered['Date'].max()}")
        
#         # IMPROVED: Find ALL columns except system columns
#         system_columns = ['Data masurarii', 'Date']
#         temp_columns = [col for col in temp_filtered.columns if col not in system_columns]
#         print(f"🔍 ALL temperature columns found: {temp_columns}")
        
#         # Show sample data to understand structure
#         if len(temp_filtered) > 0:
#             print(f"📊 Sample temperature data:")
#             sample_row = temp_filtered.iloc[0]
#             for col in temp_columns[:5]:  # Show first 5 data columns
#                 print(f"  {col}: {sample_row[col]}")
        
#         daily_temperatures = []
#         for _, row in temp_filtered.iterrows():
#             temp_record = {
#                 'date': row['Date'],
#                 'datetime': row['Data masurarii']
#             }
#             # Add ALL data columns (not just filtered ones)
#             for col in temp_columns:
#                 if pd.notna(row[col]):  # Only add non-NaN values
#                     temp_record[col] = row[col]
            
#             # DEBUG: Print what's being added
#             if len(daily_temperatures) < 3:  # Print first 3 records for debugging
#                 data_keys = [k for k in temp_record.keys() if k not in ['date', 'datetime']]
#                 print(f"  📝 Record {len(daily_temperatures)+1}: {len(data_keys)} data columns: {data_keys[:5]}...")
            
#             daily_temperatures.append(temp_record)
        
#         print(f"✅ Extracted {len(daily_temperatures)} daily temperature records")
        
#         # Additional debug: Show structure of first record
#         if daily_temperatures:
#             first_record = daily_temperatures[0]
#             all_keys = list(first_record.keys())
#             data_keys = [k for k in all_keys if k not in ['date', 'datetime']]
#             print(f"🔍 First temperature record contains {len(data_keys)} data fields")
#             if data_keys:
#                 print(f"  Sample data fields: {data_keys[:3]}")
#                 for key in data_keys[:3]:
#                     print(f"    {key}: {first_record[key]}")
        
#     except Exception as e:
#         print(f"❌ Error loading temperature data: {e}")
#         import traceback
#         traceback.print_exc()
#         daily_temperatures = []
    
#     # === STEP 5: Extract daily precipitation data - FIXED ===
#     print(f"\n--- STEP 5: EXTRACTING DAILY PRECIPITATION DATA - FIXED ---")
    
#     try:
#         precip_df = pd.read_csv(bucuresti_folder / files['precip'], encoding='utf-8')
#         print(f"✅ Loaded precipitation data: {precip_df.shape}")
#         print(f"📋 Precipitation data columns: {list(precip_df.columns)}")
        
#         # Convert timestamps and extract date only
#         precip_df['Data masurarii'] = pd.to_datetime(precip_df['Data masurarii'])
#         precip_df['Date'] = precip_df['Data masurarii'].dt.date
        
#         # Filter precipitation data (same date range as temperature)
#         precip_mask = (precip_df['Date'] >= temp_start_date) & (precip_df['Date'] <= temp_end_date)
#         precip_filtered = precip_df[precip_mask].copy()
        
#         print(f"✅ Filtered precipitation data: {len(precip_filtered)} records")
#         print(f"  Date range: {precip_filtered['Date'].min()} to {precip_filtered['Date'].max()}")
        
#         # IMPROVED: Find ALL columns except system columns
#         system_columns = ['Data masurarii', 'Date']
#         precip_columns = [col for col in precip_filtered.columns if col not in system_columns]
#         print(f"🔍 ALL precipitation columns found: {precip_columns}")
        
#         # Show sample data to understand structure
#         if len(precip_filtered) > 0:
#             print(f"📊 Sample precipitation data:")
#             sample_row = precip_filtered.iloc[0]
#             for col in precip_columns[:5]:  # Show first 5 data columns
#                 print(f"  {col}: {sample_row[col]}")
        
#         daily_precipitation = []
#         for _, row in precip_filtered.iterrows():
#             precip_record = {
#                 'date': row['Date'],
#                 'datetime': row['Data masurarii']
#             }
#             # Add ALL data columns (not just filtered ones)
#             for col in precip_columns:
#                 if pd.notna(row[col]):  # Only add non-NaN values
#                     precip_record[col] = row[col]
            
#             # DEBUG: Print what's being added
#             if len(daily_precipitation) < 3:  # Print first 3 records for debugging
#                 data_keys = [k for k in precip_record.keys() if k not in ['date', 'datetime']]
#                 print(f"  📝 Record {len(daily_precipitation)+1}: {len(data_keys)} data columns: {data_keys[:5]}...")
            
#             daily_precipitation.append(precip_record)
        
#         print(f"✅ Extracted {len(daily_precipitation)} daily precipitation records")
        
#         # Additional debug: Show structure of first record
#         if daily_precipitation:
#             first_record = daily_precipitation[0]
#             all_keys = list(first_record.keys())
#             data_keys = [k for k in all_keys if k not in ['date', 'datetime']]
#             print(f"🔍 First precipitation record contains {len(data_keys)} data fields")
#             if data_keys:
#                 print(f"  Sample data fields: {data_keys[:3]}")
#                 for key in data_keys[:3]:
#                     print(f"    {key}: {first_record[key]}")
        
#     except Exception as e:
#         print(f"❌ Error loading precipitation data: {e}")
#         import traceback
#         traceback.print_exc()
#         daily_precipitation = []
    
#     # === STEP 6: Compile comprehensive results ===
#     print(f"\n--- STEP 6: COMPILING RESULTS ---")
    
#     # Create comprehensive result
#     result = {
#         'metadata': {
#             'target_date': target_date_str,
#             'past_days': past_days,
#             'start_datetime': start_datetime,
#             'end_datetime': end_datetime,
#             'extraction_timestamp': datetime.now()
#         },
#         'hourly_data': {
#             'raw_data': hourly_filtered,
#             'total_records': len(hourly_filtered),
#             'date_range': {
#                 'start': hourly_filtered['Data masurarii'].min() if len(hourly_filtered) > 0 else None,
#                 'end': hourly_filtered['Data masurarii'].max() if len(hourly_filtered) > 0 else None
#             }
#         },
#         'wind_analysis': {
#             'mean_speed_ms': wind_speed_mean,
#             'total_measurements': len(wind_speeds) if 'wind_speeds' in locals() else 0
#         },
#         'nebulosity_analysis': {
#             'most_frequent_value': nebulosity_mode,
#             'occurrence_times': nebulosity_times,
#             'total_occurrences': len(nebulosity_times) if nebulosity_times else 0
#         },
#         'daily_temperatures': daily_temperatures,
#         'daily_precipitation': daily_precipitation,
#         'summary_stats': {
#             'hourly_records': len(hourly_filtered),
#             'temperature_days': len(daily_temperatures),
#             'precipitation_days': len(daily_precipitation),
#             'wind_data_available': wind_speed_mean is not None,
#             'nebulosity_data_available': nebulosity_mode is not None
#         }
#     }
    
#     # Print detailed summary
#     print(f"✅ Compilation complete!")
#     print(f"\nDETAILED SUMMARY:")
#     print(f"  Hourly records: {result['summary_stats']['hourly_records']}")
#     print(f"  Wind speed mean: {wind_speed_mean:.2f} m/s" if wind_speed_mean else "  Wind speed: Not available")
#     print(f"  Nebulosity mode: {nebulosity_mode}" if nebulosity_mode else "  Nebulosity: Not available")
#     print(f"  Temperature days: {result['summary_stats']['temperature_days']}")
#     print(f"  Precipitation days: {result['summary_stats']['precipitation_days']}")
    
#     # DEBUG: Final verification of data structure
#     print(f"\n🔍 FINAL DATA VERIFICATION:")
#     if daily_temperatures:
#         temp_sample = daily_temperatures[0]
#         temp_data_fields = [k for k in temp_sample.keys() if k not in ['date', 'datetime']]
#         print(f"  Temperature data fields per record: {len(temp_data_fields)}")
#         if temp_data_fields:
#             print(f"    Example fields: {temp_data_fields[:3]}")
    
#     if daily_precipitation:
#         precip_sample = daily_precipitation[0]
#         precip_data_fields = [k for k in precip_sample.keys() if k not in ['date', 'datetime']]
#         print(f"  Precipitation data fields per record: {len(precip_data_fields)}")
#         if precip_data_fields:
#             print(f"    Example fields: {precip_data_fields[:3]}")
    
#     return result





#################################################################
# ##################### extract_pdf_data.py #####################
#################################################################





# import pdfplumber
# import os
# import re
# import time
# import threading
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from datetime import datetime, timedelta
# from pathlib import Path
# from typing import Dict, List, Tuple, Optional

# def extract_forecast_from_single_pdf(pdf_path: str, target_date: str) -> Optional[Dict[str, str]]:
#     """
#     Extract meteorological forecast text from a single PDF file.
    
#     Args:
#         pdf_path (str): Path to the PDF file
#         target_date (str): Date string for identification
    
#     Returns:
#         Dict with 'interval' and 'forecast_text' or None if extraction fails
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
#                 print(f"⚠️  No text found in {pdf_path}")
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
#                 print(f"⚠️  No interval line found in {pdf_path}")
#                 return None
            
#             # Find BUCUREȘTI section
#             bucuresti_start_idx = -1
#             for i in range(interval_line_idx + 1, len(lines)):
#                 if 'BUCUREȘTI' in lines[i].upper():
#                     bucuresti_start_idx = i
#                     break
            
#             if bucuresti_start_idx == -1:
#                 print(f"⚠️  No BUCUREȘTI section found in {pdf_path}")
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
#                 print(f"⚠️  No forecast text extracted from {pdf_path}")
#                 return None
            
#             return {
#                 'interval': interval_line,
#                 'forecast_text': forecast_text,
#                 'file_path': pdf_path
#             }
            
#     except Exception as e:
#         print(f"❌ Error processing {pdf_path}: {e}")
#         return None

# def find_pdf_files_for_date_range(target_date_str: str, past_days: int, base_folder: str = "date/all_diagnosis_forecast_text") -> List[Tuple[str, str]]:
#     """
#     Find PDF files for the specified date range.
    
#     Args:
#         target_date_str (str): Target date in format "yyyy-mm-dd"
#         past_days (int): Number of past days to include
#         base_folder (str): Base folder containing date-organized PDFs
    
#     Returns:
#         List of tuples (date_str, pdf_path)
#     """
    
#     base_path = Path(base_folder)
#     target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    
#     pdf_files = []
    
#     # Generate date range (starting from target_date going backwards)
#     for i in range(past_days):
#         current_date = target_date - timedelta(days=i)
#         date_str = current_date.strftime("%Y-%m-%d")
        
#         # Construct path: date/all_diagnosis_forecast_text/YYYY/MM/DD
#         year = current_date.strftime("%Y")
#         month = current_date.strftime("%m")
#         day = current_date.strftime("%d")
        
#         date_folder = base_path / year / month / day
        
#         if date_folder.exists():
#             # Find PDF files in this folder
#             pdf_files_in_folder = list(date_folder.glob("*.pdf"))
            
#             if pdf_files_in_folder:
#                 # Take the first PDF file found (assuming one per day)
#                 pdf_path = str(pdf_files_in_folder[0])
#                 pdf_files.append((date_str, pdf_path))
#                 print(f"✓ Found PDF for {date_str}: {pdf_path}")
#             else:
#                 print(f"⚠️  No PDF files found in {date_folder}")
#         else:
#             print(f"⚠️  Folder not found: {date_folder}")
    
#     return pdf_files

# def extract_forecasts_sequential(target_date_str: str, past_days: int, base_folder: str = "date/all_diagnosis_forecast_text") -> Dict[str, Dict[str, str]]:
#     """
#     Sequential version: Extract meteorological forecasts from PDF files one by one.
    
#     Args:
#         target_date_str (str): Target date in format "yyyy-mm-dd"
#         past_days (int): Number of past days to process
#         base_folder (str): Base folder containing PDFs
    
#     Returns:
#         Dict[date_str, extracted_data]
#     """
    
#     print(f"=" * 70)
#     print(f"SEQUENTIAL PDF FORECAST EXTRACTION")
#     print(f"Target date: {target_date_str}")
#     print(f"Past days: {past_days}")
#     print(f"=" * 70)
    
#     start_time = time.time()
    
#     # Find PDF files
#     pdf_files = find_pdf_files_for_date_range(target_date_str, past_days, base_folder)
    
#     if not pdf_files:
#         print("❌ No PDF files found for the specified date range")
#         return {}
    
#     print(f"\n--- Processing {len(pdf_files)} PDF files sequentially ---")
    
#     results = {}
    
#     for i, (date_str, pdf_path) in enumerate(pdf_files):
#         print(f"\n[{i+1}/{len(pdf_files)}] Processing {date_str}: {Path(pdf_path).name}")
        
#         extracted_data = extract_forecast_from_single_pdf(pdf_path, date_str)
        
#         if extracted_data:
#             results[date_str] = extracted_data
#             print(f"✓ Successfully extracted forecast for {date_str}")
            
#             # Show preview of extracted text
#             preview_text = extracted_data['forecast_text'][:200] + "..." if len(extracted_data['forecast_text']) > 200 else extracted_data['forecast_text']
#             print(f"  Preview: {preview_text}")
#         else:
#             print(f"❌ Failed to extract forecast for {date_str}")
    
#     end_time = time.time()
#     processing_time = end_time - start_time
    
#     print(f"\n--- SEQUENTIAL PROCESSING COMPLETE ---")
#     print(f"Total time: {processing_time:.2f} seconds")
#     print(f"Successfully processed: {len(results)}/{len(pdf_files)} files")
#     print(f"Average time per file: {processing_time/len(pdf_files):.2f} seconds")
    
#     return results

# def extract_single_pdf_thread(pdf_info: Tuple[str, str]) -> Tuple[str, Optional[Dict[str, str]]]:
#     """
#     Thread worker function to extract data from a single PDF.
    
#     Args:
#         pdf_info: Tuple of (date_str, pdf_path)
    
#     Returns:
#         Tuple of (date_str, extracted_data)
#     """
#     date_str, pdf_path = pdf_info
    
#     print(f"🔄 Thread processing {date_str}: {Path(pdf_path).name}")
    
#     try:
#         extracted_data = extract_forecast_from_single_pdf(pdf_path, date_str)
        
#         if extracted_data:
#             print(f"✓ Thread completed {date_str}")
#         else:
#             print(f"❌ Thread failed {date_str}")
            
#         return date_str, extracted_data
        
#     except Exception as e:
#         print(f"❌ Thread error for {date_str}: {e}")
#         return date_str, None

# def extract_forecasts_multithreaded(target_date_str: str, past_days: int, base_folder: str = "date/all_diagnosis_forecast_text", max_workers: int = 4) -> Dict[str, Dict[str, str]]:
#     """
#     Multithreaded version: Extract meteorological forecasts from PDF files in parallel.
    
#     Args:
#         target_date_str (str): Target date in format "yyyy-mm-dd"
#         past_days (int): Number of past days to process
#         base_folder (str): Base folder containing PDFs
#         max_workers (int): Maximum number of threads
    
#     Returns:
#         Dict[date_str, extracted_data]
#     """
    
#     print(f"=" * 70)
#     print(f"MULTITHREADED PDF FORECAST EXTRACTION")
#     print(f"Target date: {target_date_str}")
#     print(f"Past days: {past_days}")
#     print(f"Max workers: {max_workers}")
#     print(f"=" * 70)
    
#     start_time = time.time()
    
#     # Find PDF files
#     pdf_files = find_pdf_files_for_date_range(target_date_str, past_days, base_folder)
    
#     if not pdf_files:
#         print("❌ No PDF files found for the specified date range")
#         return {}
    
#     print(f"\n--- Processing {len(pdf_files)} PDF files with {max_workers} threads ---")
    
#     results = {}
    
#     # Use ThreadPoolExecutor for parallel processing
#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         # Submit all tasks
#         future_to_date = {executor.submit(extract_single_pdf_thread, pdf_info): pdf_info[0] 
#                          for pdf_info in pdf_files}
        
#         # Collect results as they complete
#         for future in as_completed(future_to_date):
#             date_str = future_to_date[future]
            
#             try:
#                 result_date, extracted_data = future.result()
                
#                 if extracted_data:
#                     results[result_date] = extracted_data
#                     print(f"✓ Completed {result_date}")
                    
#                     # Show preview
#                     preview_text = extracted_data['forecast_text'][:200] + "..." if len(extracted_data['forecast_text']) > 200 else extracted_data['forecast_text']
#                     print(f"  Preview: {preview_text}")
#                 else:
#                     print(f"❌ Failed {result_date}")
                    
#             except Exception as e:
#                 print(f"❌ Exception for {date_str}: {e}")
    
#     end_time = time.time()
#     processing_time = end_time - start_time
    
#     print(f"\n--- MULTITHREADED PROCESSING COMPLETE ---")
#     print(f"Total time: {processing_time:.2f} seconds")
#     print(f"Successfully processed: {len(results)}/{len(pdf_files)} files")
#     print(f"Average time per file: {processing_time/len(pdf_files):.2f} seconds")
    
#     return results

# def compare_extraction_performance(target_date_str: str, past_days: int, base_folder: str = "date/all_diagnosis_forecast_text", max_workers: int = 4) -> Dict[str, any]:
#     """
#     Compare performance between sequential and multithreaded PDF extraction.
    
#     Args:
#         target_date_str (str): Target date in format "yyyy-mm-dd"
#         past_days (int): Number of past days to process
#         base_folder (str): Base folder containing PDFs
#         max_workers (int): Maximum number of threads for parallel version
    
#     Returns:
#         Dict with performance comparison results
#     """
    
#     print(f"=" * 80)
#     print(f"PERFORMANCE COMPARISON: SEQUENTIAL vs MULTITHREADED")
#     print(f"Target date: {target_date_str}, Past days: {past_days}")
#     print(f"=" * 80)
    
#     # Run sequential version
#     print(f"\n🔄 RUNNING SEQUENTIAL VERSION...")
#     sequential_start = time.time()
#     sequential_results = extract_forecasts_sequential(target_date_str, past_days, base_folder)
#     sequential_time = time.time() - sequential_start
    
#     print(f"\n" + "⏱️ " * 20)
#     print(f"SEQUENTIAL COMPLETED: {sequential_time:.2f} seconds")
#     print(f"Successfully processed: {len(sequential_results)} files")
    
#     # Small delay between tests
#     time.sleep(1)
    
#     # Run multithreaded version
#     print(f"\n🔄 RUNNING MULTITHREADED VERSION...")
#     multithreaded_start = time.time()
#     multithreaded_results = extract_forecasts_multithreaded(target_date_str, past_days, base_folder, max_workers)
#     multithreaded_time = time.time() - multithreaded_start
    
#     print(f"\n" + "⏱️ " * 20)
#     print(f"MULTITHREADED COMPLETED: {multithreaded_time:.2f} seconds")
#     print(f"Successfully processed: {len(multithreaded_results)} files")
    
#     # Calculate performance improvement
#     if sequential_time > 0:
#         speed_improvement = ((sequential_time - multithreaded_time) / sequential_time) * 100
#         speedup_factor = sequential_time / multithreaded_time if multithreaded_time > 0 else float('inf')
#     else:
#         speed_improvement = 0
#         speedup_factor = 1
    
#     # Compile comparison results
#     comparison_results = {
#         'sequential': {
#             'time_seconds': sequential_time,
#             'files_processed': len(sequential_results),
#             'avg_time_per_file': sequential_time / max(len(sequential_results), 1)
#         },
#         'multithreaded': {
#             'time_seconds': multithreaded_time,
#             'files_processed': len(multithreaded_results),
#             'avg_time_per_file': multithreaded_time / max(len(multithreaded_results), 1),
#             'max_workers': max_workers
#         },
#         'performance': {
#             'speed_improvement_percentage': speed_improvement,
#             'speedup_factor': speedup_factor,
#             'time_saved_seconds': sequential_time - multithreaded_time
#         },
#         'data_consistency': len(sequential_results) == len(multithreaded_results)
#     }
    
#     # Print detailed comparison
#     print(f"\n" + "=" * 80)
#     print(f"DETAILED PERFORMANCE COMPARISON")
#     print(f"=" * 80)
#     print(f"Sequential Processing:")
#     print(f"  ⏱️  Total time: {sequential_time:.2f} seconds")
#     print(f"  📁 Files processed: {len(sequential_results)}")
#     print(f"  📊 Avg time per file: {sequential_time / max(len(sequential_results), 1):.2f} seconds")
    
#     print(f"\nMultithreaded Processing ({max_workers} workers):")
#     print(f"  ⏱️  Total time: {multithreaded_time:.2f} seconds")
#     print(f"  📁 Files processed: {len(multithreaded_results)}")
#     print(f"  📊 Avg time per file: {multithreaded_time / max(len(multithreaded_results), 1):.2f} seconds")
    
#     print(f"\nPerformance Improvement:")
#     if speed_improvement > 0:
#         print(f"  🚀 Speed improvement: {speed_improvement:.1f}% faster")
#         print(f"  ⚡ Speedup factor: {speedup_factor:.2f}x")
#         print(f"  ⏰ Time saved: {sequential_time - multithreaded_time:.2f} seconds")
#     else:
#         print(f"  📉 Multithreaded was {abs(speed_improvement):.1f}% slower")
    
#     print(f"  ✅ Data consistency: {'PASS' if comparison_results['data_consistency'] else 'FAIL'}")
    
#     return comparison_results

# # def save_extracted_forecasts(forecasts: Dict[str, Dict[str, str]], output_file: str = "extracted_forecasts.txt"):
# #     """
# #     Save extracted forecasts to a text file.
    
# #     Args:
# #         forecasts: Dictionary of extracted forecast data
# #         output_file: Output file path
# #     """
    
# #     try:
# #         with open(output_file, 'w', encoding='utf-8') as f:
# #             f.write("EXTRACTED METEOROLOGICAL FORECASTS\n")
# #             f.write("=" * 50 + "\n\n")
            
# #             for date_str in sorted(forecasts.keys()):
# #                 forecast_data = forecasts[date_str]
                
# #                 f.write(f"DATE: {date_str}\n")
# #                 f.write("-" * 30 + "\n")
# #                 f.write(f"INTERVAL: {forecast_data['interval']}\n\n")
# #                 f.write("FORECAST:\n")
# #                 f.write(forecast_data['forecast_text'])
# #                 f.write("\n\n" + "=" * 50 + "\n\n")
        
# #         print(f"✓ Forecasts saved to: {output_file}")
        
# #     except Exception as e:
# #         print(f"❌ Error saving forecasts: {e}")




"""
Input extraction for the meteorological prompting pipeline.

This module loads the two kinds of inputs every downstream entry point needs
for a given (target_date, past_days) window:

    extract_comprehensive_weather_data -> station CSV measurements
        (hourly wind/nebulosity/phenomena, daily Tmax/Tmin per station,
         daily precipitation per station)

    extract_forecasts_sequential       -> ANM diagnosis PDFs
        (the Bucharest section of each day's meteorological report)

Both public functions have unchanged signatures and return shapes relative
to the previous extract_data_from_tables.py / extract_pdf_data.py modules.
"""

import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pdfplumber


# ---------------------------------------------------------------------------
# Station CSV extraction
# ---------------------------------------------------------------------------

_BUCURESTI_FOLDER = Path("date/bucuresti")
_CSV_FILES = {
    "hourly": "SirDate_1748514797752_Bucuresti.csv",
    "temp": "DateZilniceTemp_1748520589580_Bucuresti.csv",
    "precip": "DateZilnicePrecip_1748521941631_Bucuresti.csv",
}


def extract_comprehensive_weather_data(
    target_date_str: str,
    past_days: int,
) -> Optional[dict]:
    """
    Extract hourly measurements, daily temperatures, and daily precipitation
    for Bucharest from the three station CSV files.

    Args:
        target_date_str: Target date in "yyyy-mm-dd" format.
        past_days: Number of past meteorological days to include.

    Returns:
        A dict with the keys:
            'metadata', 'hourly_data', 'wind_analysis',
            'nebulosity_analysis', 'daily_temperatures',
            'daily_precipitation', 'summary_stats'
        or None if the inputs can't be loaded.
    """

    # Validate that all three CSVs exist before parsing anything
    for file_type, filename in _CSV_FILES.items():
        file_path = _BUCURESTI_FOLDER / filename
        if not file_path.exists():
            print(f"ERROR: {file_type} file not found: {file_path}")
            return None

    # Parse target date
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"ERROR: invalid target date format '{target_date_str}', expected yyyy-mm-dd")
        return None

    # Meteorological window for hourly data:
    #   start = (target_date - past_days) at 08:30
    #   end   = target_date at 06:30
    start_date = target_date - timedelta(days=past_days)
    start_datetime = datetime.combine(start_date, datetime.min.time().replace(hour=8, minute=30))
    end_datetime = datetime.combine(target_date, datetime.min.time().replace(hour=6, minute=30))

    # --- Hourly data (wind, nebulosity, phenomena) ---
    try:
        hourly_df = pd.read_csv(_BUCURESTI_FOLDER / _CSV_FILES["hourly"], encoding="utf-8")
        print(f"Loaded hourly CSV: {hourly_df.shape[0]} rows")
        hourly_df["Data masurarii"] = pd.to_datetime(hourly_df["Data masurarii"])
        hourly_mask = (hourly_df["Data masurarii"] >= start_datetime) & (
            hourly_df["Data masurarii"] <= end_datetime
        )
        hourly_filtered = hourly_df[hourly_mask].copy()
    except Exception as e:
        print(f"ERROR loading hourly data: {e}")
        return None

    # Wind speed (Rff1) — initialize to empty so downstream size checks always work,
    # regardless of whether the column exists.
    wind_speeds: pd.Series = pd.Series(dtype=float)
    wind_speed_mean: Optional[float] = None
    if "Rff1" not in hourly_filtered.columns:
        print("WARNING: 'Rff1' column missing from hourly data; wind stats unavailable")
    else:
        wind_speeds = hourly_filtered["Rff1"].dropna()
        if len(wind_speeds) > 0:
            wind_speed_mean = float(wind_speeds.mean())
            print(
                f"Wind (Rff1): n={len(wind_speeds)}, "
                f"mean={wind_speed_mean:.2f} m/s, "
                f"min={wind_speeds.min():.2f}, max={wind_speeds.max():.2f}"
            )
        else:
            print("WARNING: no valid Rff1 values in the window; wind stats unavailable")

    # Nebulosity (Nop)
    nebulosity_mode = None
    nebulosity_times: list = []
    if "Nop" not in hourly_filtered.columns:
        print("WARNING: 'Nop' column missing from hourly data; nebulosity stats unavailable")
    else:
        nebulosity_data = hourly_filtered[["Data masurarii", "Nop"]].dropna()
        if len(nebulosity_data) == 0:
            print("WARNING: no valid Nop values in the window; nebulosity stats unavailable")
        else:
            nebulosity_counts = Counter(nebulosity_data["Nop"])
            nebulosity_mode, mode_frequency = nebulosity_counts.most_common(1)[0]
            mode_mask = nebulosity_data["Nop"] == nebulosity_mode
            nebulosity_times = nebulosity_data[mode_mask]["Data masurarii"].tolist()
            print(
                f"Nebulosity (Nop): n={len(nebulosity_data)}, "
                f"mode={nebulosity_mode}/8 ({mode_frequency} occurrences)"
            )

    # --- Daily temperature and precipitation ---
    # NOTE: the hourly window above runs 08:30 -> 06:30 across days, but the daily
    # temperature and precipitation tables are filtered on calendar date. The two
    # windows are therefore not strictly aligned. Whether this matches the ANM
    # convention for what calendar date is stamped on a 24h aggregate depends on
    # the export convention used for these CSVs; verify against ANM documentation
    # before changing the alignment, because any change will shift every reported
    # downstream metric.
    temp_start_date = target_date - timedelta(days=past_days)
    temp_end_date = target_date

    daily_temperatures = _load_daily_station_records(
        csv_path=_BUCURESTI_FOLDER / _CSV_FILES["temp"],
        label="temperature",
        start_date=temp_start_date,
        end_date=temp_end_date,
    )
    daily_precipitation = _load_daily_station_records(
        csv_path=_BUCURESTI_FOLDER / _CSV_FILES["precip"],
        label="precipitation",
        start_date=temp_start_date,
        end_date=temp_end_date,
    )

    result = {
        "metadata": {
            "target_date": target_date_str,
            "past_days": past_days,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "extraction_timestamp": datetime.now(),
        },
        "hourly_data": {
            "raw_data": hourly_filtered,
            "total_records": len(hourly_filtered),
            "date_range": {
                "start": hourly_filtered["Data masurarii"].min() if len(hourly_filtered) > 0 else None,
                "end": hourly_filtered["Data masurarii"].max() if len(hourly_filtered) > 0 else None,
            },
        },
        "wind_analysis": {
            "mean_speed_ms": wind_speed_mean,
            "total_measurements": len(wind_speeds),
        },
        "nebulosity_analysis": {
            "most_frequent_value": nebulosity_mode,
            "occurrence_times": nebulosity_times,
            "total_occurrences": len(nebulosity_times),
        },
        "daily_temperatures": daily_temperatures,
        "daily_precipitation": daily_precipitation,
        "summary_stats": {
            "hourly_records": len(hourly_filtered),
            "temperature_days": len(daily_temperatures),
            "precipitation_days": len(daily_precipitation),
            "wind_data_available": wind_speed_mean is not None,
            "nebulosity_data_available": nebulosity_mode is not None,
        },
    }

    print(
        f"Weather data for {target_date_str} (past_days={past_days}): "
        f"hourly={len(hourly_filtered)}, "
        f"temp_days={len(daily_temperatures)}, "
        f"precip_days={len(daily_precipitation)}"
    )
    return result


def _load_daily_station_records(
    csv_path: Path,
    label: str,
    start_date,
    end_date,
) -> List[Dict]:
    """
    Load a daily per-station CSV (temperature or precipitation), filter it by
    calendar date, and return one dict per row containing the station columns
    that are not NaN.
    """
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
        df["Data masurarii"] = pd.to_datetime(df["Data masurarii"])
        df["Date"] = df["Data masurarii"].dt.date

        mask = (df["Date"] >= start_date) & (df["Date"] <= end_date)
        df_filtered = df[mask].copy()
    except Exception as e:
        print(f"ERROR loading {label} data from {csv_path.name}: {e}")
        return []

    system_columns = {"Data masurarii", "Date"}
    data_columns = [c for c in df_filtered.columns if c not in system_columns]

    records: List[Dict] = []
    for _, row in df_filtered.iterrows():
        record = {
            "date": row["Date"],
            "datetime": row["Data masurarii"],
        }
        for col in data_columns:
            if pd.notna(row[col]):
                record[col] = row[col]
        records.append(record)

    print(f"Loaded {label} CSV: {len(df_filtered)} rows in window -> {len(records)} records")
    return records


# ---------------------------------------------------------------------------
# ANM diagnosis PDF extraction
# ---------------------------------------------------------------------------

_PDF_BASE_FOLDER_DEFAULT = "date/all_diagnosis_forecast_text"

# Primary end marker for the Bucharest diagnosis section. If absent, these
# are tried as fallbacks in order.
_SECTION_END_PRIMARY = "PROGNOZĂ"
_SECTION_END_FALLBACKS = ("OBSERVAȚII", "AVERTIZARE", "ATENȚIE")


def extract_forecasts_sequential(
    target_date_str: str,
    past_days: int,
    base_folder: str = _PDF_BASE_FOLDER_DEFAULT,
) -> Dict[str, Dict[str, str]]:
    """
    Extract the Bucharest diagnosis section from ANM PDFs for a (target_date,
    past_days) window. PDFs are processed sequentially.

    Args:
        target_date_str: Target date in "yyyy-mm-dd" format.
        past_days: Number of days (including the target day) to process,
            working backwards.
        base_folder: Root folder holding YYYY/MM/DD/*.pdf.

    Returns:
        {date_str: {'interval': <header line>, 'forecast_text': <section>}}
        Dates with missing or unparseable PDFs are omitted.
    """
    pdf_files = _find_pdf_files_for_date_range(target_date_str, past_days, base_folder)
    if not pdf_files:
        print(f"ERROR: no PDF files found for {target_date_str} (past_days={past_days})")
        return {}

    results: Dict[str, Dict[str, str]] = {}
    for date_str, pdf_path in pdf_files:
        extracted = _extract_forecast_from_single_pdf(pdf_path, date_str)
        if extracted is not None:
            results[date_str] = extracted

    print(
        f"PDF extraction for {target_date_str} (past_days={past_days}): "
        f"{len(results)}/{len(pdf_files)} PDFs parsed successfully"
    )
    return results


def _find_pdf_files_for_date_range(
    target_date_str: str,
    past_days: int,
    base_folder: str,
) -> List[Tuple[str, str]]:
    """
    Walk YYYY/MM/DD folders for each date in the window and collect one PDF
    per day. If a day folder contains more than one PDF, the alphabetically
    first one is used and a warning is printed.
    """
    base_path = Path(base_folder)
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()

    pdf_files: List[Tuple[str, str]] = []
    for i in range(past_days):
        current_date = target_date - timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        date_folder = (
            base_path
            / current_date.strftime("%Y")
            / current_date.strftime("%m")
            / current_date.strftime("%d")
        )

        if not date_folder.exists():
            print(f"WARNING: folder not found for {date_str}: {date_folder}")
            continue

        # Sort for deterministic selection across platforms.
        candidates = sorted(date_folder.glob("*.pdf"))
        if not candidates:
            print(f"WARNING: no PDF files in {date_folder}")
            continue

        if len(candidates) > 1:
            print(
                f"WARNING: {len(candidates)} PDFs in {date_folder}, "
                f"using '{candidates[0].name}'"
            )

        pdf_path = str(candidates[0])
        pdf_files.append((date_str, pdf_path))
        print(f"Found PDF for {date_str}: {pdf_path}")

    return pdf_files


def _extract_forecast_from_single_pdf(
    pdf_path: str,
    target_date: str,
) -> Optional[Dict[str, str]]:
    """
    Parse a single ANM diagnosis PDF and return the Bucharest section.

    Returns a dict with 'interval' (the header line containing the observation
    period) and 'forecast_text' (the Bucharest section content), or None on
    any failure.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join(
                (page.extract_text() or "") for page in pdf.pages
            )
    except Exception as e:
        print(f"ERROR reading {pdf_path}: {e}")
        return None

    if not full_text.strip():
        print(f"WARNING: no text extracted from {pdf_path}")
        return None

    lines = full_text.split("\n")

    # 1. Interval line
    interval_line: Optional[str] = None
    interval_idx = -1
    interval_pattern = re.compile(
        r"SITUAȚIA METEOROLOGICĂ PENTRU INTERVALUL.*ORA.*-.*ORA",
        re.IGNORECASE,
    )
    for i, line in enumerate(lines):
        if interval_pattern.search(line):
            interval_line = line.strip()
            interval_idx = i
            break

    if interval_line is None:
        print(f"WARNING: interval line not found in {pdf_path}")
        return None

    # 2. BUCUREȘTI section start
    bucuresti_start = -1
    for i in range(interval_idx + 1, len(lines)):
        if "BUCUREȘTI" in lines[i].upper():
            bucuresti_start = i
            break

    if bucuresti_start == -1:
        print(f"WARNING: BUCUREȘTI section not found in {pdf_path}")
        return None

    # 3. Section end — look for PROGNOZĂ first, then the fallbacks in order.
    section_end = _find_section_end(lines, bucuresti_start + 1)

    forecast_lines = [
        lines[i].strip()
        for i in range(bucuresti_start, section_end)
        if lines[i].strip()
    ]
    forecast_text = "\n".join(forecast_lines)

    if not forecast_text:
        print(f"WARNING: empty Bucharest section extracted from {pdf_path}")
        return None

    return {
        "interval": interval_line,
        "forecast_text": forecast_text,
    }


def _find_section_end(lines: List[str], search_from: int) -> int:
    """
    Return the index of the first line (at or after search_from) that marks
    the end of the Bucharest section. Falls through PROGNOZĂ, then the
    alternate markers, then the end of the document.
    """
    # Primary: PROGNOZĂ
    for i in range(search_from, len(lines)):
        if _SECTION_END_PRIMARY in lines[i].upper():
            return i

    # Fallbacks, in declared order
    for marker in _SECTION_END_FALLBACKS:
        for i in range(search_from, len(lines)):
            if marker in lines[i].upper():
                return i

    # No marker found: take everything to EOF
    return len(lines)

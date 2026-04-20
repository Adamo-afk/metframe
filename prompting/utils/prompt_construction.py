# #############################################################################
# ############################# create_prompts.py #############################
# #############################################################################





# import os
# from datetime import datetime, timedelta
# from typing import Dict, Tuple
# import pandas as pd
# from collections import Counter

# def create_meteorological_prompts(
#     current_date: str,
#     weather_data: Dict,
#     pdf_forecasts: Dict[str, Dict[str, str]],
#     past_days: int = 5  # Add past_days parameter here too
# ) -> Tuple[str, str]:
#     """
#     Create system and user prompts for LLM meteorological diagnosis in Romanian.
    
#     Args:
#         current_date (str): Current date for diagnosis (e.g., "2024-01-05")
#         weather_data (Dict): Comprehensive weather data from extract_comprehensive_weather_data
#         pdf_forecasts (Dict): PDF forecast data from extract_forecasts_*
#         past_days (int): Number of past days to include
    
#     Returns:
#         Tuple[str, str]: (system_prompt, user_prompt)
#     """
    
#     print(f"Creating LLM prompts for meteorological diagnosis")
#     print(f"Current date: {current_date}")
#     print(f"Past days: {past_days}")
    
#     # Create system prompt
#     system_prompt = create_system_prompt()
    
#     # Create user prompt
#     user_prompt = create_user_prompt(current_date, weather_data, pdf_forecasts, past_days)
    
#     return system_prompt, user_prompt

# def create_system_prompt() -> str:
#     """
#     Create the system prompt in Romanian for meteorological diagnosis.
    
#     Returns:
#         str: System prompt in Romanian
#     """
    
#     system_prompt = """Tu ești un meteorolog al Administrației Naționale de Meteorologie din România și trebuie să faci o diagnoză pe baza datelor pe care le primești de la stațiile meteo.

# STRUCTURA RĂSPUNSULUI:

# 1. PRIMA PROPOZIȚIE: Observații generale despre vremea din ziua curentă comparativ cu zilele precedente, pe baza temperaturilor maxime și minime înregistrate și a informațiilor din prognozele anterioare.

# 2. A DOUA PROPOZIȚIE: Descrierea stării cerului (senin sau acoperit de nori, pe baza valorii Nop care variază între 1-8, unde 1 = cer senin, 8 = complet acoperit) și a vântului (slab sau puternic, pe baza valorii Rff1 în m/s, unde sub 3 m/s = slab, peste 6 m/s = puternic).

# 3. A TREIA PROPOZIȚIE (OPȚIONALĂ): Această propoziție se include DOAR DACĂ un fenomen meteorologic specific s-a repetat în ultimele 24 de ore (de exemplu: ploi, ninsori, ceață, etc.). Dacă nu există fenomene repetate, se omite această propoziție.

# 4. A PATRA PROPOZIȚIE (sau a treia dacă nu există fenomene repetate): Informații despre temperatura maximă înregistrată la cele 3 stații meteo din București: Filaret, Băneasa și Afumați.

# 5. PROPOZIȚIA FINALĂ: Pe baza tuturor datelor analizate, o predicție pentru temperaturile de la ora 6:00 dimineața la cele 3 stații din București (Filaret, Băneasa, Afumați).

# IMPORTANT: 
# - Răspunsul trebuie să fie în limba română
# - Folosește termeni meteorologici profesioniști
# - Fii precis cu valorile numerice
# - Păstrează tonul profesional specific unui meteorolog ANM"""

#     return system_prompt

# def extract_raw_csv_data_by_day(weather_data: Dict, target_date_str: str, past_days: int, include_target_date: bool = False) -> Dict[str, Dict]:
#     """
#     Extract meteorological data organized by day, calculating means from the 3 Bucharest stations.
    
#     Args:
#         weather_data: The comprehensive weather data dictionary
#         target_date_str: Target date string
#         past_days: Number of past days
#         include_target_date: Whether to include the target date itself
    
#     Returns:
#         Dict with processed meteorological data organized by date
#     """
    
#     daily_data = {}
#     target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    
#     # Generate the date range we're interested in
#     start_range = 0 if include_target_date else 1
#     end_range = past_days + 1 if include_target_date else past_days + 1
    
#     for i in range(start_range, end_range):
#         current_date = target_date - timedelta(days=i)
#         date_str = current_date.strftime("%Y-%m-%d")
#         daily_data[date_str] = {
#             'date': current_date,
#             'temperature_max_mean': None,
#             'temperature_min_mean': None,
#             'precipitation_mean': None,
#             'hourly_summary': {},
#             'is_target_date': (i == 0)  # Flag to identify target date
#         }
    
#     print(f"\n🔍 DEBUG: Processing temperature data correctly...")
    
#     # Extract temperature data and calculate means per day for Tamax24 and Tamin24
#     if weather_data.get('daily_temperatures'):
#         print(f"📊 Found {len(weather_data['daily_temperatures'])} temperature records")
        
#         # Group temperature data by date
#         temp_by_date = {}
#         for temp_record in weather_data['daily_temperatures']:
#             record_date = temp_record['date']
#             if hasattr(record_date, 'strftime'):
#                 date_str = record_date.strftime("%Y-%m-%d")
#             else:
#                 date_str = str(record_date)
            
#             if date_str not in temp_by_date:
#                 temp_by_date[date_str] = {
#                     'tamax24_values': [],
#                     'tamin24_values': [],
#                     'stations': []
#                 }
            
#             # Extract specific temperature values
#             if 'Tamax24' in temp_record and temp_record['Tamax24'] is not None:
#                 try:
#                     temp_max = float(temp_record['Tamax24'])
#                     temp_by_date[date_str]['tamax24_values'].append(temp_max)
#                 except (ValueError, TypeError):
#                     pass
            
#             if 'Tamin24' in temp_record and temp_record['Tamin24'] is not None:
#                 try:
#                     temp_min = float(temp_record['Tamin24'])
#                     temp_by_date[date_str]['tamin24_values'].append(temp_min)
#                 except (ValueError, TypeError):
#                     pass
            
#             # Track station names for debugging
#             if 'Denumire' in temp_record:
#                 station_name = temp_record['Denumire']
#                 if station_name not in temp_by_date[date_str]['stations']:
#                     temp_by_date[date_str]['stations'].append(station_name)
        
#         # Calculate means for each date
#         for date_str, temp_data in temp_by_date.items():
#             if date_str in daily_data:
#                 # Calculate Tamax24 mean
#                 if temp_data['tamax24_values']:
#                     max_mean = sum(temp_data['tamax24_values']) / len(temp_data['tamax24_values'])
#                     daily_data[date_str]['temperature_max_mean'] = max_mean
#                     print(f"  🌡️ Tamax24 {date_str}: {max_mean:.1f}°C (from {len(temp_data['tamax24_values'])} stations: {temp_data['stations']})")
                
#                 # Calculate Tamin24 mean
#                 if temp_data['tamin24_values']:
#                     min_mean = sum(temp_data['tamin24_values']) / len(temp_data['tamin24_values'])
#                     daily_data[date_str]['temperature_min_mean'] = min_mean
#                     print(f"  🌡️ Tamin24 {date_str}: {min_mean:.1f}°C (from {len(temp_data['tamin24_values'])} stations)")
    
#     # Extract precipitation data and calculate means per day for R24
#     if weather_data.get('daily_precipitation'):
#         print(f"🌧️ Found {len(weather_data['daily_precipitation'])} precipitation records")
        
#         # Group precipitation data by date
#         precip_by_date = {}
#         processed_dates = set()
        
#         for precip_record in weather_data['daily_precipitation']:
#             record_date = precip_record['date']
#             if hasattr(record_date, 'strftime'):
#                 date_str = record_date.strftime("%Y-%m-%d")
#             else:
#                 date_str = str(record_date)
            
#             # Create unique key to avoid processing same station/date multiple times
#             station_name = precip_record.get('Denumire', 'Unknown')
#             unique_key = f"{date_str}_{station_name}"
#             if unique_key in processed_dates:
#                 continue
#             processed_dates.add(unique_key)
            
#             if date_str not in precip_by_date:
#                 precip_by_date[date_str] = {
#                     'r24_values': [],
#                     'stations': []
#                 }
            
#             # Extract R24 value
#             if 'R24' in precip_record and precip_record['R24'] is not None:
#                 try:
#                     precip_val = float(precip_record['R24'])
#                     precip_by_date[date_str]['r24_values'].append(precip_val)
#                     precip_by_date[date_str]['stations'].append(station_name)
#                 except (ValueError, TypeError):
#                     pass
        
#         # Calculate means for each date
#         for date_str, precip_data in precip_by_date.items():
#             if date_str in daily_data and precip_data['r24_values']:
#                 mean_precip = sum(precip_data['r24_values']) / len(precip_data['r24_values'])
#                 daily_data[date_str]['precipitation_mean'] = mean_precip
#                 print(f"  🌧️ R24 {date_str}: {mean_precip:.1f} l/m² (from {len(precip_data['r24_values'])} stations: {precip_data['stations']})")
    
#     # Extract hourly summary data (wind, nebulosity, phenomena) for each day
#     if weather_data.get('hourly_data', {}).get('raw_data') is not None:
#         hourly_df = weather_data['hourly_data']['raw_data']
        
#         for date_str in daily_data.keys():
#             date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
#             # Filter hourly data for this specific date
#             day_start = datetime.combine(date_obj, datetime.min.time())
#             day_end = datetime.combine(date_obj + timedelta(days=1), datetime.min.time())
            
#             day_mask = (hourly_df['Data masurarii'] >= day_start) & (hourly_df['Data masurarii'] < day_end)
#             day_hourly = hourly_df[day_mask]
            
#             # Wind statistics
#             if 'Rff1' in day_hourly.columns:
#                 wind_speeds = day_hourly['Rff1'].dropna()
#                 if len(wind_speeds) > 0:
#                     daily_data[date_str]['hourly_summary']['wind'] = {
#                         'mean': wind_speeds.mean(),
#                         'min': wind_speeds.min(),
#                         'max': wind_speeds.max()
#                     }
            
#             # Nebulosity statistics
#             if 'Nop' in day_hourly.columns:
#                 nebulosity_values = day_hourly['Nop'].dropna()
#                 if len(nebulosity_values) > 0:
#                     neb_counter = Counter(nebulosity_values)
#                     most_common = neb_counter.most_common(1)[0]
#                     daily_data[date_str]['hourly_summary']['nebulosity'] = {
#                         'most_frequent': most_common[0],
#                         'count': most_common[1]
#                     }
            
#             # Phenomena statistics
#             if 'Fenomen' in day_hourly.columns:
#                 phenomena = day_hourly['Fenomen'].dropna()
#                 phenomena_clean = phenomena[~phenomena.isin(['nan', 'Nu avem fenomen'])]
#                 if len(phenomena_clean) > 0:
#                     phenom_counter = Counter(phenomena_clean)
#                     daily_data[date_str]['hourly_summary']['phenomena'] = phenom_counter.most_common(3)
    
#     print(f"✅ Daily data processing complete!")
#     return daily_data

# def get_most_common_hours_for_nebulosity(weather_data: Dict, nop_value) -> list:
#     """
#     Get the 3 most common hours when a specific nebulosity value occurred.
    
#     Args:
#         weather_data: Weather data dictionary
#         nop_value: The nebulosity value to analyze
    
#     Returns:
#         List of the 3 most common hours
#     """
    
#     if not weather_data.get('nebulosity_analysis', {}).get('occurrence_times'):
#         return []
    
#     times = weather_data['nebulosity_analysis']['occurrence_times']
    
#     # Extract hours from timestamps
#     hours = []
#     for timestamp in times:
#         if hasattr(timestamp, 'hour'):
#             hours.append(timestamp.hour)
#         elif hasattr(timestamp, 'strftime'):
#             hours.append(int(timestamp.strftime("%H")))
    
#     if not hours:
#         return []
    
#     # Count hour frequencies
#     hour_counter = Counter(hours)
#     most_common_hours = hour_counter.most_common(3)
    
#     return [f"{hour:02d}:00" for hour, count in most_common_hours]

# def create_user_prompt(
#     current_date: str,
#     weather_data: Dict,
#     pdf_forecasts: Dict[str, Dict[str, str]],
#     past_days: int = 5  # Add past_days as parameter
# ) -> str:
#     """
#     Create the user prompt with raw CSV data and diagnosis context.
    
#     Args:
#         current_date (str): Current date for diagnosis
#         weather_data (Dict): Comprehensive weather data
#         pdf_forecasts (Dict): PDF forecast data
    
#     Returns:
#         str: User prompt in Romanian
#     """
    
#     # Start building the user prompt
#     user_prompt = "Analiza meteorologică pentru diagnoză:\n\n"
    
#     # Extract raw CSV data organized by day (including target date)
#     daily_raw_data = extract_raw_csv_data_by_day(weather_data, current_date, past_days, include_target_date=True)
    
#     # Get dates before and INCLUDING current_date for context (diagnosis data)
#     # We need current_date forecast to show diagnosis for the most recent historical day
#     current_date_obj = datetime.strptime(current_date, "%Y-%m-%d").date()
#     previous_forecasts = {}
    
#     for date_str, forecast_data in pdf_forecasts.items():
#         forecast_date = datetime.strptime(date_str, "%Y-%m-%d").date()
#         if forecast_date <= current_date_obj:  # FIXED: Include current date (<=) instead of (<)
#             previous_forecasts[date_str] = forecast_data
    
#     # Separate current day from historical days FIRST
#     historical_days = {}
#     current_day_data = None
    
#     for date_str, day_data in daily_raw_data.items():
#         if day_data.get('is_target_date', False):
#             current_day_data = (date_str, day_data)
#         else:
#             historical_days[date_str] = day_data
    
#     # DEBUG: Show what PDF forecasts are available
#     print(f"\n🔍 DEBUG: PDF Forecasts available:")
#     for date_str in sorted(pdf_forecasts.keys()):
#         print(f"  📄 PDF forecast for: {date_str}")
    
#     print(f"\n🔍 DEBUG: Previous forecasts filtered (before {current_date}):")
#     for date_str in sorted(previous_forecasts.keys()):
#         print(f"  📋 Forecast for: {date_str}")
    
#     print(f"\n🔍 DEBUG: Historical days being processed:")
#     for date_str in sorted(historical_days.keys()):
#         # FIXED: Look for forecast with key = historical_day + 1 day
#         historical_date = datetime.strptime(date_str, "%Y-%m-%d").date()
#         forecast_date = historical_date + timedelta(days=1)
#         forecast_key = forecast_date.strftime("%Y-%m-%d")
#         has_forecast = forecast_key in previous_forecasts
#         print(f"  📅 Historical day: {date_str} - Looking for forecast: {forecast_key} - Available: {'✅' if has_forecast else '❌'}")
    
#     print(f"\n🔍 DEBUG: Date mapping explanation:")
#     print(f"  Each forecast covers the PREVIOUS day:")
#     for forecast_key, forecast_data in sorted(previous_forecasts.items()):
#         interval = forecast_data.get('interval', 'Unknown interval')
#         print(f"  📋 Forecast {forecast_key}: {interval}")
#         # Extract the start date from interval to show which day it actually covers
#         if 'INTERVALUL' in interval:
#             try:
#                 import re
#                 date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', interval)
#                 if date_match:
#                     covered_date = date_match.group(1)
#                     print(f"    → This covers data for: {covered_date}")
#             except:
#                 pass
    
#     # FILTER: Only keep historical days that have corresponding PDF forecasts
#     filtered_historical_days = {}
#     for date_str, day_data in historical_days.items():
#         historical_date = datetime.strptime(date_str, "%Y-%m-%d").date()
#         forecast_date = historical_date + timedelta(days=1)
#         forecast_key = forecast_date.strftime("%Y-%m-%d")
        
#         if forecast_key in previous_forecasts:
#             filtered_historical_days[date_str] = day_data
#         else:
#             print(f"🚫 EXCLUDED: {date_str} (no PDF forecast available for key: {forecast_key})")
    
#     print(f"\n✅ FILTERED: Will show {len(filtered_historical_days)} historical days with forecasts:")
#     for date_str in sorted(filtered_historical_days.keys()):
#         historical_date = datetime.strptime(date_str, "%Y-%m-%d").date()
#         forecast_date = historical_date + timedelta(days=1)
#         forecast_key = forecast_date.strftime("%Y-%m-%d")
#         print(f"  📅 {date_str} → forecast {forecast_key}")
    
#     # Update historical_days to only include filtered ones
#     historical_days = filtered_historical_days
    
#     # Display historical days first (with diagnoses)
#     for date_str in sorted(historical_days.keys(), reverse=True):
#         day_data = historical_days[date_str]
#         user_prompt += f"📅 ZIUA {date_str}:\n"
        
#         # Display temperature maxima and minima means
#         if day_data['temperature_max_mean'] is not None:
#             user_prompt += f"🌡️ Temperatura medie maximă București: {day_data['temperature_max_mean']:.1f}°C\n"
        
#         if day_data['temperature_min_mean'] is not None:
#             user_prompt += f"🌡️ Temperatura medie minimă București: {day_data['temperature_min_mean']:.1f}°C\n"
        
#         # Display precipitation mean
#         if day_data['precipitation_mean'] is not None:
#             user_prompt += f"🌧️ Precipitații medii București: {day_data['precipitation_mean']:.1f} l/m²\n"
        
#         # Hourly summary data
#         if day_data['hourly_summary'].get('wind'):
#             wind = day_data['hourly_summary']['wind']
#             user_prompt += f"🌬️ Vânt: Media {wind['mean']:.1f} m/s (min: {wind['min']:.1f}, max: {wind['max']:.1f})\n"
        
#         if day_data['hourly_summary'].get('nebulosity'):
#             neb = day_data['hourly_summary']['nebulosity']
#             user_prompt += f"☁️ Nebulozitate: Cel mai frecvent {neb['most_frequent']}/8 ({neb['count']} măsurători)\n"
        
#         if day_data['hourly_summary'].get('phenomena'):
#             user_prompt += f"🌦️ Fenomene:\n"
#             for phenomenon, count in day_data['hourly_summary']['phenomena']:
#                 user_prompt += f"  - {phenomenon}: {count} observații\n"
        
#         # Add diagnosis - GUARANTEED to exist since we filtered
#         historical_date = datetime.strptime(date_str, "%Y-%m-%d").date()
#         forecast_date = historical_date + timedelta(days=1)
#         forecast_key = forecast_date.strftime("%Y-%m-%d")
        
#         forecast_data = previous_forecasts[forecast_key]  # No need to check, guaranteed to exist
#         user_prompt += f"📅 Diagnoza pentru {date_str}:\n"
#         user_prompt += f"Intervalul analizat: {forecast_data['interval']}\n\n"
        
#         # Extract full diagnosis starting from BUCUREȘTI
#         forecast_text = forecast_data['forecast_text']
#         bucuresti_index = forecast_text.find('BUCUREȘTI')
#         if bucuresti_index != -1:
#             diagnosis_text = forecast_text[bucuresti_index:].strip()
#             user_prompt += f'Diagnoza completă:\n"{diagnosis_text}"\n\n'
#         else:
#             user_prompt += f'Textul complet:\n"{forecast_text}"\n\n'
        
#         user_prompt += "---\n"
    
#     user_prompt += "\n"
    
#     # Add current weather data analysis (for the current diagnosis day)
#     user_prompt += f"DATELE METEOROLOGICE PENTRU DIAGNOZA CURENTĂ ({current_date}):\n\n"
    
#     # Add wind speed data with detailed analysis
#     if weather_data.get('wind_analysis', {}).get('mean_speed_ms') is not None:
#         wind_speed = weather_data['wind_analysis']['mean_speed_ms']
#         wind_measurements = weather_data['wind_analysis']['total_measurements']
#         user_prompt += f"🌬️ ANALIZA VÂNTULUI (Rff1):\n"
#         user_prompt += f"- Viteza medie înregistrată: {wind_speed:.1f} m/s\n"
#         user_prompt += f"- Numărul total de măsurători: {wind_measurements}\n"
        
#         # Add wind interpretation
#         if wind_speed < 3:
#             wind_desc = "slab"
#         elif wind_speed < 6:
#             wind_desc = "moderat"
#         else:
#             wind_desc = "puternic"
#         user_prompt += f"- Caracterizare: vânt {wind_desc}\n\n"
    
#     # Add nebulosity data with the 3 most common hours
#     if weather_data.get('nebulosity_analysis', {}).get('most_frequent_value') is not None:
#         nop_value = weather_data['nebulosity_analysis']['most_frequent_value']
#         nop_occurrences = weather_data['nebulosity_analysis']['total_occurrences']
        
#         user_prompt += f"☁️ ANALIZA NEBULOZITĂȚII (Nop):\n"
#         user_prompt += f"- Valoarea cea mai frecventă: {nop_value}/8 (pe scala 1-8)\n"
#         user_prompt += f"- Numărul de înregistrări cu această valoare: {nop_occurrences}\n"
        
#         # Add nebulosity interpretation
#         if int(nop_value) <= 2:
#             nop_desc = "cer senin sau puțin noros"
#         elif int(nop_value) <= 4:
#             nop_desc = "cer parțial noros"
#         elif int(nop_value) <= 6:
#             nop_desc = "cer predominant noros"
#         else:
#             nop_desc = "cer complet acoperit de nori"
#         user_prompt += f"- Caracterizare: {nop_desc}\n"
        
#         # Show only the 3 most common hours
#         common_hours = get_most_common_hours_for_nebulosity(weather_data, nop_value)
#         if common_hours:
#             user_prompt += f"- Cele mai frecvente ore de apariție: {', '.join(common_hours)}\n"
        
#         user_prompt += "\n"
    
#     # Add FIXED precipitation analysis (no more duplicates)
#     if weather_data.get('daily_precipitation'):
#         user_prompt += f"🌧️ ANALIZA PRECIPITAȚIILOR:\n"
        
#         # Use the extracted mean precipitation data (excluding current day)
#         total_precip = 0
#         rainy_days = 0
        
#         for date_str in sorted(historical_days.keys()):
#             date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
            
#             # Get precipitation mean for this day
#             daily_precip = historical_days[date_str]['precipitation_mean'] or 0.0
            
#             if daily_precip > 0:
#                 user_prompt += f"- {date_display}: {daily_precip:.1f} l/m² (zi cu precipitații)\n"
#                 total_precip += daily_precip
#                 rainy_days += 1
#             else:
#                 user_prompt += f"- {date_display}: {daily_precip:.1f} l/m² (zi fără precipitații)\n"
        
#         user_prompt += f"\nBilanțul precipitațiilor în perioada analizată:\n"
#         user_prompt += f"- Total precipitații: {total_precip:.1f} l/m²\n"
#         user_prompt += f"- Zile cu precipitații: {rainy_days} din {len(historical_days)}\n"
#         if len(historical_days) > 0:
#             user_prompt += f"- Media zilnică: {total_precip/len(historical_days):.1f} l/m²\n"
#         user_prompt += "\n"
    
#     # Add detailed hourly phenomena analysis
#     if weather_data.get('hourly_data', {}).get('raw_data') is not None:
#         hourly_df = weather_data['hourly_data']['raw_data']
        
#         if 'Fenomen' in hourly_df.columns:
#             # Get phenomena and their frequencies
#             phenomena = hourly_df['Fenomen'].dropna()
#             phenomena_clean = phenomena[~phenomena.isin(['nan', 'Nu avem fenomen'])]
            
#             if not phenomena_clean.empty:
#                 user_prompt += f"🌦️ FENOMENE METEOROLOGICE ÎNREGISTRATE:\n"
                
#                 # Count occurrences of each phenomenon
#                 phenomena_counts = phenomena_clean.value_counts()
                
#                 user_prompt += f"Inventarul complet al fenomenelor observate:\n"
#                 for phenomenon, count in phenomena_counts.items():
#                     percentage = (count / len(phenomena)) * 100
#                     user_prompt += f"- {phenomenon}\n"
#                     user_prompt += f"  Frecvența: {count} apariții ({percentage:.1f}% din timpul observat)\n"
                
#                 # Identify repeated phenomena (key for sentence 3 in diagnosis)
#                 repeated_phenomena = phenomena_counts[phenomena_counts > 1]
#                 if not repeated_phenomena.empty:
#                     user_prompt += f"\n⚠️ FENOMENE REPETATE (importante pentru propoziția 3):\n"
#                     for phenomenon, count in repeated_phenomena.items():
#                         user_prompt += f"- {phenomenon}: {count} apariții în ultimele 24h\n"
                
#                 user_prompt += "\n"
    
#     # Add current day raw data (WITHOUT diagnosis - this is what LLM needs to generate)
#     if current_day_data:
#         date_str, day_data = current_day_data
#         user_prompt += f"📅 ZIUA CURENTĂ {date_str} (pentru care se generează diagnoza):\n"
        
#         # Display temperature maxima and minima means
#         if day_data['temperature_max_mean'] is not None:
#             user_prompt += f"🌡️ Temperatura medie maximă București: {day_data['temperature_max_mean']:.1f}°C\n"
        
#         if day_data['temperature_min_mean'] is not None:
#             user_prompt += f"🌡️ Temperatura medie minimă București: {day_data['temperature_min_mean']:.1f}°C\n"
        
#         # Display precipitation mean
#         if day_data['precipitation_mean'] is not None:
#             user_prompt += f"🌧️ Precipitații medii București: {day_data['precipitation_mean']:.1f} l/m²\n"
        
#         # Hourly summary data
#         if day_data['hourly_summary'].get('wind'):
#             wind = day_data['hourly_summary']['wind']
#             user_prompt += f"🌬️ Vânt: Media {wind['mean']:.1f} m/s (min: {wind['min']:.1f}, max: {wind['max']:.1f})\n"
        
#         if day_data['hourly_summary'].get('nebulosity'):
#             neb = day_data['hourly_summary']['nebulosity']
#             user_prompt += f"☁️ Nebulozitate: Cel mai frecvent {neb['most_frequent']}/8 ({neb['count']} măsurători)\n"
        
#         if day_data['hourly_summary'].get('phenomena'):
#             user_prompt += f"🌦️ Fenomene:\n"
#             for phenomenon, count in day_data['hourly_summary']['phenomena']:
#                 user_prompt += f"  - {phenomenon}: {count} observații\n"
        
#         # NO DIAGNOSIS TEXT HERE - this is what the LLM needs to generate
#         user_prompt += "\n---\n\n"
    
#     # Add temperature means summary for all days (both max and min)
#     user_prompt += f"📊 MEDIA TEMPERATURILOR PENTRU TOATE ZILELE:\n"
#     all_temp_max_means = []
#     all_temp_min_means = []
    
#     for date_str in sorted(daily_raw_data.keys()):
#         day_data = daily_raw_data[date_str]
#         date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m")
        
#         if day_data['temperature_max_mean'] is not None:
#             all_temp_max_means.append(day_data['temperature_max_mean'])
#             user_prompt += f"- {date_display} Tmax: {day_data['temperature_max_mean']:.1f}°C"
            
#             if day_data['temperature_min_mean'] is not None:
#                 all_temp_min_means.append(day_data['temperature_min_mean'])
#                 user_prompt += f", Tmin: {day_data['temperature_min_mean']:.1f}°C\n"
#             else:
#                 user_prompt += "\n"
#         elif day_data['temperature_min_mean'] is not None:
#             all_temp_min_means.append(day_data['temperature_min_mean'])
#             user_prompt += f"- {date_display} Tmin: {day_data['temperature_min_mean']:.1f}°C\n"
    
#     if all_temp_max_means:
#         overall_temp_max_mean = sum(all_temp_max_means) / len(all_temp_max_means)
#         user_prompt += f"🌡️ Temperatura maximă medie generală: {overall_temp_max_mean:.1f}°C\n"
    
#     if all_temp_min_means:
#         overall_temp_min_mean = sum(all_temp_min_means) / len(all_temp_min_means)
#         user_prompt += f"🌡️ Temperatura minimă medie generală: {overall_temp_min_mean:.1f}°C\n"
    
#     user_prompt += "\n"
    
#     # Add final instructions for current diagnosis
#     user_prompt += f"🎯 SARCINA ACTUALĂ:\n\n"
#     user_prompt += f"Pe baza tuturor datelor prezentate mai sus, elaborează o diagnoză meteorologică profesională pentru ziua de {current_date} pentru București.\n\n"
    
#     user_prompt += f"ELEMENTE CHEIE DE ANALIZAT:\n"
#     if weather_data.get('wind_analysis', {}).get('mean_speed_ms') is not None:
#         user_prompt += f"✓ Viteza medie a vântului (Rff1): {weather_data['wind_analysis']['mean_speed_ms']:.1f} m/s\n"
#     if weather_data.get('nebulosity_analysis', {}).get('most_frequent_value') is not None:
#         user_prompt += f"✓ Nebulozitatea dominantă (Nop): {weather_data['nebulosity_analysis']['most_frequent_value']}/8\n"
#         user_prompt += f"✓ Momentele specifice când s-a înregistrat această nebulozitate\n"
#     user_prompt += f"✓ Fenomenele meteorologice repetate (pentru propoziția opțională 3)\n"
#     user_prompt += f"✓ Temperaturile maxime la cele 3 stații din București (Filaret, Băneasa, Afumați)\n"
#     user_prompt += f"✓ Comparația cu condițiile din zilele precedente (pe baza diagnozelor anterioare)\n\n"
    
#     user_prompt += f"IMPORTANT: Diagnoza trebuie să înceapă cu 'BUCUREȘTI' și să respecte exact structura din instrucțiunile de sistem (5 propoziții, conform ANM România)."
    
#     return user_prompt

# def test_prompt_generation(
#     current_date,
#     weather_data,
#     pdf_forecasts,
#     saving_past_days,
#     past_days=5
# ):
#     """
#     Test the prompt generation with example data.
#     """
    
#     # Generate prompts
#     system_prompt, user_prompt = create_meteorological_prompts(
#         current_date=current_date,
#         weather_data=weather_data,
#         pdf_forecasts=pdf_forecasts,
#         past_days=past_days
#     )
    
#     # Display results
#     print("=" * 80)
#     print("SYSTEM PROMPT:")
#     print("=" * 80)
#     print(system_prompt)
    
#     print("\n" + "=" * 80)
#     print("USER PROMPT:")
#     print("=" * 80)
#     print(user_prompt)

#     prompts_path = f"prompts\\{current_date}\\{saving_past_days}_past_days"

#     # Create a folder called 'prompts' if it doesn't exist
#     if not os.path.exists(prompts_path):
#         os.makedirs(prompts_path, exist_ok=True)

#     system_prompt_path = f"{prompts_path}\\system_prompt_{current_date}.txt"
#     # Ensure prompts are saved in the 'prompts' folder
#     if not os.path.exists(system_prompt_path):
#         # Save system prompt
#         with open(system_prompt_path, "w", encoding="utf-8") as f:
#             f.write(system_prompt)

#     user_prompt_path = f"{prompts_path}\\user_prompt_{current_date}_{saving_past_days}_past_days.txt"
#     # Save user prompt
#     with open(user_prompt_path, "w", encoding="utf-8") as f:
#         f.write(user_prompt)

#     print(f"\n✅ Prompts saved to {system_prompt_path} and {user_prompt_path}")

#     # return system_prompt, user_prompt





# #################################################################################
# ############################# create_prompts_gpt.py #############################
# #################################################################################





# import os
# import json
# from datetime import datetime, timedelta
# from typing import Dict, Tuple, List
# import pandas as pd
# from collections import Counter
# import openai
# import os

# # Set default API key if not provided
# DEFAULT_OPENAI_API_KEY = ...

# def create_meteorological_prompts(
#     current_date: str,
#     weather_data: Dict,
#     past_days: int = 5,
#     openai_api_key: str = None
# ) -> Tuple[str, str]:
#     """
#     Create system and user prompts for LLM meteorological diagnosis in Romanian.
    
#     Args:
#         current_date (str): Current date for diagnosis (e.g., "2024-01-05")
#         weather_data (Dict): Comprehensive weather data from extract_comprehensive_weather_data
#         past_days (int): Number of past days to include
#         openai_api_key (str): OpenAI API key for GPT calls
    
#     Returns:
#         Tuple[str, str]: (system_prompt, user_prompt)
#     """
    
#     print(f"Creating LLM prompts for meteorological diagnosis")
#     print(f"Current date: {current_date}")
#     print(f"Past days: {past_days}")
    
#     # Create system prompt
#     system_prompt = create_system_prompt()
    
#     # Create user prompt
#     user_prompt = create_user_prompt(current_date, weather_data, past_days, openai_api_key)
    
#     return system_prompt, user_prompt

# def create_system_prompt() -> str:
#     """
#     Create the system prompt in Romanian for meteorological diagnosis.
    
#     Returns:
#         str: System prompt in Romanian
#     """
    
#     system_prompt = """Tu ești un meteorolog al Administrației Naționale de Meteorologie din România și trebuie să faci o diagnoză pe baza datelor pe care le primești de la stațiile meteo.

# Trebuie să gândești pas cu pas pentru toate propozițiile, respectând astfel structura răspunsului definită mai jos.

# STRUCTURA RĂSPUNSULUI:

# 1. PRIMA PROPOZIȚIE: Observații generale despre vremea din ziua curentă comparativ cu zilele precedente, pe baza temperaturilor maxime și minime înregistrate și a informațiilor din prognozele anterioare.

# 2. A DOUA PROPOZIȚIE: Descrierea stării cerului (senin sau acoperit de nori, pe baza valorii Nop care variază între 1-8, unde 1 = cer senin, 8 = complet acoperit) și a vântului (slab sau puternic, pe baza valorii Rff1 în m/s, unde sub 3 m/s = slab, peste 6 m/s = puternic).

# 3. A TREIA PROPOZIȚIE (OPȚIONALĂ): Această propoziție se include DOAR DACĂ un fenomen meteorologic specific s-a repetat în ultimele 24 de ore (de exemplu: ploi, ninsori, ceață, etc.). Dacă nu există fenomene repetate, se omite această propoziție.

# 4. A PATRA PROPOZIȚIE (sau a treia dacă nu există fenomene repetate): Informații despre temperatura maximă înregistrată la cele 3 stații meteo din București: Filaret, Băneasa și Afumați.

# 5. PROPOZIȚIA FINALĂ: Pe baza tuturor datelor analizate, o predicție pentru temperaturile de la ora 6:00 dimineața la cele 3 stații din București (Filaret, Băneasa, Afumați).

# IMPORTANT: 
# - Răspunsul trebuie să fie în limba română
# - Folosește termeni meteorologici profesioniști
# - Fii precis cu valorile numerice
# - Păstrează tonul profesional specific unui meteorolog ANM"""

#     return system_prompt

# def create_system_prompt_for_gpt() -> str:
#     """
#     Create the system prompt for GPT-5-mini that includes step-by-step thinking instructions.
    
#     Returns:
#         str: System prompt for GPT with thinking instructions
#     """
    
#     system_prompt = """Tu ești un meteorolog al Administrației Naționale de Meteorologie din România și trebuie să faci o diagnoză pe baza datelor pe care le primești de la stațiile meteo.

# FOARTE IMPORTANT: Pentru fiecare propoziție din diagnoza ta, trebuie să explici mai întâi procesul de gândire pas cu pas, apoi să formulezi propoziția finală.

# Structura răspunsului tău trebuie să fie:
# ...explicația ta pas cu pas pentru prima propoziție...
# Prin urmare, PRIMA PROPOZIȚIE: [propoziția finală]

# ...explicația ta pas cu pas pentru a doua propoziție...
# Prin urmare, A DOUA PROPOZIȚIE: [propoziția finală]

# ...și așa mai departe pentru toate propozițiile...

# STRUCTURA RĂSPUNSULUI:

# 1. PRIMA PROPOZIȚIE: Observații generale despre vremea din ziua curentă comparativ cu zilele precedente, pe baza temperaturilor maxime și minime înregistrate și a informațiilor din prognozele anterioare.

# 2. A DOUA PROPOZIȚIE: Descrierea stării cerului (senin sau acoperit de nori, pe baza valorii Nop care variază între 1-8, unde 1 = cer senin, 8 = complet acoperit) și a vântului (slab sau puternic, pe baza valorii Rff1 în m/s, unde sub 3 m/s = slab, peste 6 m/s = puternic).

# 3. A TREIA PROPOZIȚIE (OPȚIONALĂ): Această propoziție se include DOAR DACĂ un fenomen meteorologic specific s-a repetat în ultimele 24 de ore (de exemplu: ploi, ninsori, ceață, etc.). Dacă nu există fenomene repetate, se omite această propoziție.

# 4. A PATRA PROPOZIȚIE (sau a treia dacă nu există fenomene repetate): Informații despre temperatura maximă înregistrată la cele 3 stații meteo din București: Filaret, Băneasa și Afumați.

# 5. PROPOZIȚIA FINALĂ: Pe baza tuturor datelor analizate, o predicție pentru temperaturile de la ora 6:00 dimineața la cele 3 stații din București (Filaret, Băneasa, Afumați).

# IMPORTANT: 
# - Răspunsul trebuie să fie în limba română
# - Folosește termeni meteorologici profesioniști
# - Fii precis cu valorile numerice
# - Păstrează tonul profesional specific unui meteorolog ANM
# - ARATĂ ÎNTOTDEAUNA procesul de gândire înaintea fiecărei propoziții"""

#     return system_prompt

# def load_formatted_diagnoses(year: int) -> Dict:
#     """
#     Load formatted diagnoses from JSON file for the specified year.
    
#     Args:
#         year (int): Year to load diagnoses for
    
#     Returns:
#         Dict: Formatted diagnoses data
#     """
    
#     file_path = f"formatted_diagnoses_{year}\\formatted_diagnoses_{year}.json"
    
#     try:
#         with open(file_path, 'r', encoding='utf-8') as f:
#             data = json.load(f)
#         print(f"✅ Loaded formatted diagnoses from {file_path}")
#         return data
#     except FileNotFoundError:
#         print(f"❌ Could not find formatted diagnoses file: {file_path}")
#         return {}
#     except Exception as e:
#         print(f"❌ Error loading formatted diagnoses: {str(e)}")
#         return {}

# def extract_raw_csv_data_by_day(weather_data: Dict, target_date_str: str, past_days: int, include_target_date: bool = False) -> Dict[str, Dict]:
#     """
#     Extract meteorological data organized by day, calculating means from the 3 Bucharest stations.
    
#     Args:
#         weather_data: The comprehensive weather data dictionary
#         target_date_str: Target date string
#         past_days: Number of past days
#         include_target_date: Whether to include the target date itself
    
#     Returns:
#         Dict with processed meteorological data organized by date
#     """
    
#     daily_data = {}
#     target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    
#     # Generate the date range we're interested in
#     start_range = 0 if include_target_date else 1
#     end_range = past_days + 1 if include_target_date else past_days + 1
    
#     for i in range(start_range, end_range):
#         current_date = target_date - timedelta(days=i)
#         date_str = current_date.strftime("%Y-%m-%d")
#         daily_data[date_str] = {
#             'date': current_date,
#             'temperature_max_mean': None,
#             'temperature_min_mean': None,
#             'precipitation_mean': None,
#             'hourly_summary': {},
#             'is_target_date': (i == 0)  # Flag to identify target date
#         }
    
#     # Extract temperature data and calculate means per day for Tamax24 and Tamin24
#     if weather_data.get('daily_temperatures'):
#         # Group temperature data by date
#         temp_by_date = {}
#         for temp_record in weather_data['daily_temperatures']:
#             record_date = temp_record['date']
#             if hasattr(record_date, 'strftime'):
#                 date_str = record_date.strftime("%Y-%m-%d")
#             else:
#                 date_str = str(record_date)
            
#             if date_str not in temp_by_date:
#                 temp_by_date[date_str] = {
#                     'tamax24_values': [],
#                     'tamin24_values': [],
#                     'stations': []
#                 }
            
#             # Extract specific temperature values
#             if 'Tamax24' in temp_record and temp_record['Tamax24'] is not None:
#                 try:
#                     temp_max = float(temp_record['Tamax24'])
#                     temp_by_date[date_str]['tamax24_values'].append(temp_max)
#                 except (ValueError, TypeError):
#                     pass
            
#             if 'Tamin24' in temp_record and temp_record['Tamin24'] is not None:
#                 try:
#                     temp_min = float(temp_record['Tamin24'])
#                     temp_by_date[date_str]['tamin24_values'].append(temp_min)
#                 except (ValueError, TypeError):
#                     pass
            
#             # Track station names for debugging
#             if 'Denumire' in temp_record:
#                 station_name = temp_record['Denumire']
#                 if station_name not in temp_by_date[date_str]['stations']:
#                     temp_by_date[date_str]['stations'].append(station_name)
        
#         # Calculate means for each date
#         for date_str, temp_data in temp_by_date.items():
#             if date_str in daily_data:
#                 # Calculate Tamax24 mean
#                 if temp_data['tamax24_values']:
#                     max_mean = sum(temp_data['tamax24_values']) / len(temp_data['tamax24_values'])
#                     daily_data[date_str]['temperature_max_mean'] = max_mean
                
#                 # Calculate Tamin24 mean
#                 if temp_data['tamin24_values']:
#                     min_mean = sum(temp_data['tamin24_values']) / len(temp_data['tamin24_values'])
#                     daily_data[date_str]['temperature_min_mean'] = min_mean
    
#     # Extract precipitation data and calculate means per day for R24
#     if weather_data.get('daily_precipitation'):
#         # Group precipitation data by date
#         precip_by_date = {}
#         processed_dates = set()
        
#         for precip_record in weather_data['daily_precipitation']:
#             record_date = precip_record['date']
#             if hasattr(record_date, 'strftime'):
#                 date_str = record_date.strftime("%Y-%m-%d")
#             else:
#                 date_str = str(record_date)
            
#             # Create unique key to avoid processing same station/date multiple times
#             station_name = precip_record.get('Denumire', 'Unknown')
#             unique_key = f"{date_str}_{station_name}"
#             if unique_key in processed_dates:
#                 continue
#             processed_dates.add(unique_key)
            
#             if date_str not in precip_by_date:
#                 precip_by_date[date_str] = {
#                     'r24_values': [],
#                     'stations': []
#                 }
            
#             # Extract R24 value
#             if 'R24' in precip_record and precip_record['R24'] is not None:
#                 try:
#                     precip_val = float(precip_record['R24'])
#                     precip_by_date[date_str]['r24_values'].append(precip_val)
#                     precip_by_date[date_str]['stations'].append(station_name)
#                 except (ValueError, TypeError):
#                     pass
        
#         # Calculate means for each date
#         for date_str, precip_data in precip_by_date.items():
#             if date_str in daily_data and precip_data['r24_values']:
#                 mean_precip = sum(precip_data['r24_values']) / len(precip_data['r24_values'])
#                 daily_data[date_str]['precipitation_mean'] = mean_precip
    
#     # Extract hourly summary data (wind, nebulosity, phenomena) for each day
#     if weather_data.get('hourly_data', {}).get('raw_data') is not None:
#         hourly_df = weather_data['hourly_data']['raw_data']
        
#         for date_str in daily_data.keys():
#             date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
#             # Filter hourly data for this specific date
#             day_start = datetime.combine(date_obj, datetime.min.time())
#             day_end = datetime.combine(date_obj + timedelta(days=1), datetime.min.time())
            
#             day_mask = (hourly_df['Data masurarii'] >= day_start) & (hourly_df['Data masurarii'] < day_end)
#             day_hourly = hourly_df[day_mask]
            
#             # Wind statistics
#             if 'Rff1' in day_hourly.columns:
#                 wind_speeds = day_hourly['Rff1'].dropna()
#                 if len(wind_speeds) > 0:
#                     daily_data[date_str]['hourly_summary']['wind'] = {
#                         'mean': wind_speeds.mean(),
#                         'min': wind_speeds.min(),
#                         'max': wind_speeds.max()
#                     }
            
#             # Nebulosity statistics
#             if 'Nop' in day_hourly.columns:
#                 nebulosity_values = day_hourly['Nop'].dropna()
#                 if len(nebulosity_values) > 0:
#                     neb_counter = Counter(nebulosity_values)
#                     most_common = neb_counter.most_common(1)[0]
#                     daily_data[date_str]['hourly_summary']['nebulosity'] = {
#                         'most_frequent': most_common[0],
#                         'count': most_common[1]
#                     }
            
#             # Phenomena statistics
#             if 'Fenomen' in day_hourly.columns:
#                 phenomena = day_hourly['Fenomen'].dropna()
#                 phenomena_clean = phenomena[~phenomena.isin(['nan', 'Nu avem fenomen'])]
#                 if len(phenomena_clean) > 0:
#                     phenom_counter = Counter(phenomena_clean)
#                     daily_data[date_str]['hourly_summary']['phenomena'] = phenom_counter.most_common(3)
    
#     return daily_data

# def get_most_common_hours_for_nebulosity(weather_data: Dict, nop_value) -> list:
#     """
#     Get the 3 most common hours when a specific nebulosity value occurred.
    
#     Args:
#         weather_data: Weather data dictionary
#         nop_value: The nebulosity value to analyze
    
#     Returns:
#         List of the 3 most common hours
#     """
    
#     if not weather_data.get('nebulosity_analysis', {}).get('occurrence_times'):
#         return []
    
#     times = weather_data['nebulosity_analysis']['occurrence_times']
    
#     # Extract hours from timestamps
#     hours = []
#     for timestamp in times:
#         if hasattr(timestamp, 'hour'):
#             hours.append(timestamp.hour)
#         elif hasattr(timestamp, 'strftime'):
#             hours.append(int(timestamp.strftime("%H")))
    
#     if not hours:
#         return []
    
#     # Count hour frequencies
#     hour_counter = Counter(hours)
#     most_common_hours = hour_counter.most_common(3)
    
#     return [f"{hour:02d}:00" for hour, count in most_common_hours]

# def create_prompt_for_gpt(date_str: str, day_data: Dict, formatted_diagnosis: str, openai_api_key: str = None) -> Tuple[str, str]:
#     """
#     Create a prompt for GPT-5-mini with both meteorological data and formatted diagnosis example.
    
#     Args:
#         date_str: Date string for the day
#         day_data: Daily meteorological data
#         formatted_diagnosis: Formatted diagnosis text from JSON file
#         openai_api_key: OpenAI API key (optional, can be set as environment variable)
    
#     Returns:
#         Tuple[str, str]: (prompt_sent_to_gpt, gpt_response)
#     """
    
#     # Create prompt with both meteorological data and formatted diagnosis example
#     prompt = f"📅 ZIUA {date_str}:\n"
    
#     # Display temperature maxima and minima means
#     if day_data['temperature_max_mean'] is not None:
#         prompt += f"🌡️ Temperatura medie maximă București: {day_data['temperature_max_mean']:.1f}°C\n"
    
#     if day_data['temperature_min_mean'] is not None:
#         prompt += f"🌡️ Temperatura medie minimă București: {day_data['temperature_min_mean']:.1f}°C\n"
    
#     # Display precipitation mean
#     if day_data['precipitation_mean'] is not None:
#         prompt += f"🌧️ Precipitații medii București: {day_data['precipitation_mean']:.1f} l/m²\n"
    
#     # Hourly summary data
#     if day_data['hourly_summary'].get('wind'):
#         wind = day_data['hourly_summary']['wind']
#         prompt += f"🌬️ Vânt: Media {wind['mean']:.1f} m/s (min: {wind['min']:.1f}, max: {wind['max']:.1f})\n"
    
#     if day_data['hourly_summary'].get('nebulosity'):
#         neb = day_data['hourly_summary']['nebulosity']
#         prompt += f"☁️ Nebulozitate: Cel mai frecvent {neb['most_frequent']}/8 ({neb['count']} măsurători)\n"
    
#     if day_data['hourly_summary'].get('phenomena'):
#         prompt += f"🌦️ Fenomene:\n"
#         for phenomenon, count in day_data['hourly_summary']['phenomena']:
#             prompt += f"  - {phenomenon}: {count} observații\n"
    
#     # Add the formatted diagnosis example
#     prompt += f"\n📋 EXEMPLU DE DIAGNOZA STRUCTURATĂ:\n"
#     prompt += f'"{formatted_diagnosis}"\n\n'
#     prompt += "Pe baza acestor date și urmând exemplul de structurare de mai sus, generează o diagnoză meteorologică completă pentru această zi. FOARTE IMPORTANT: Arată procesul tău de gândire pas cu pas înaintea fiecărei propoziții!"
    
#     # Call OpenAI API
#     gpt_response = ""
#     try:
#         # Set up OpenAI client
#         api_key = openai_api_key or DEFAULT_OPENAI_API_KEY
#         client = openai.OpenAI(api_key=api_key)
        
#         # if openai_api_key:
#         #     client = openai.OpenAI(api_key=openai_api_key)
#         # else:
#         #     # Try to use environment variable
#         #     client = openai.OpenAI()
        
#         # Create system prompt for GPT with thinking instructions
#         system_prompt = create_system_prompt_for_gpt()
        
#         # Call GPT-5-mini using the new API
#         response = client.responses.create(
#             model='gpt-5-mini',
#             reasoning={"effort": "minimal"},
#             instructions=system_prompt,
#             input=prompt,
#             max_output_tokens=10000
#         )
        
#         gpt_response = response.output_text
#         print(f"✅ GPT-5-mini response generated for {date_str}")
        
#     except Exception as e:
#         print(f"❌ Error calling OpenAI API for {date_str}: {str(e)}")
#         gpt_response = f"Error generating GPT response: {str(e)}"
    
#     return prompt, gpt_response

# # THIS WOULD BE THE MAIN USER PROMPT W/ STEP-BY-STEP EXPLANATIONS FROM GPT
# # THAT WHERE GIVEN DAY DATA AND FORMATTED DIAGNOSIS
# def generate_gpt_responses_for_past_days(
#     daily_raw_data: Dict,
#     formatted_diagnoses: Dict,
#     current_date: str,
#     past_days: int,
#     openai_api_key: str = None
# ) -> List[str]:
#     """
#     Generate GPT responses for specified number of past days.
    
#     Args:
#         daily_raw_data: Daily meteorological data
#         formatted_diagnoses: Formatted diagnoses from JSON file
#         current_date: Current date string
#         past_days: Number of past days to process
#         openai_api_key: OpenAI API key
    
#     Returns:
#         List of GPT responses for past days
#     """
    
#     gpt_responses = []
    
#     # Get past days (excluding current date) limited to past_days count
#     past_days_list = []
#     for date_str, day_data in daily_raw_data.items():
#         if not day_data.get('is_target_date', False):
#             past_days_list.append(date_str)
    
#     # Sort past days in reverse chronological order and limit to past_days count
#     past_days_list.sort(reverse=True)
#     past_days_list = past_days_list[:past_days]
    
#     print(f"🔄 Generating GPT responses for {len(past_days_list)} past days: {past_days_list}")
    
#     for date_str in past_days_list:
#         day_data = daily_raw_data[date_str]
        
#         # Get formatted diagnosis for this date
#         if date_str in formatted_diagnoses:
#             formatted_diagnosis_data = formatted_diagnoses[date_str]
            
#             if 'formatted_diagnosis' in formatted_diagnosis_data and 'PRIMA_PROPOZITIE' in formatted_diagnosis_data['formatted_diagnosis']:
#                 formatted_diagnosis_text = formatted_diagnosis_data['formatted_diagnosis']['PRIMA_PROPOZITIE']
                
#                 # Generate GPT response
#                 gpt_prompt, gpt_response = create_prompt_for_gpt(
#                     date_str, 
#                     day_data, 
#                     formatted_diagnosis_text, 
#                     openai_api_key
#                 )
                
#                 # Create entry for this day
#                 day_entry = f"📅 ZIUA {date_str}:\n"
                
#                 # Add meteorological data
#                 if day_data['temperature_max_mean'] is not None:
#                     day_entry += f"🌡️ Temperatura medie maximă București: {day_data['temperature_max_mean']:.1f}°C\n"
                
#                 if day_data['temperature_min_mean'] is not None:
#                     day_entry += f"🌡️ Temperatura medie minimă București: {day_data['temperature_min_mean']:.1f}°C\n"
                
#                 if day_data['precipitation_mean'] is not None:
#                     day_entry += f"🌧️ Precipitații medii București: {day_data['precipitation_mean']:.1f} l/m²\n"
                
#                 if day_data['hourly_summary'].get('wind'):
#                     wind = day_data['hourly_summary']['wind']
#                     day_entry += f"🌬️ Vânt: Media {wind['mean']:.1f} m/s (min: {wind['min']:.1f}, max: {wind['max']:.1f})\n"
                
#                 if day_data['hourly_summary'].get('nebulosity'):
#                     neb = day_data['hourly_summary']['nebulosity']
#                     day_entry += f"☁️ Nebulozitate: Cel mai frecvent {neb['most_frequent']}/8 ({neb['count']} măsurători)\n"
                
#                 if day_data['hourly_summary'].get('phenomena'):
#                     day_entry += f"🌦️ Fenomene:\n"
#                     for phenomenon, count in day_data['hourly_summary']['phenomena']:
#                         day_entry += f"  - {phenomenon}: {count} observații\n"
                
#                 # Add diagnosis
#                 day_entry += f"📅 Diagnoza pentru {date_str}:\n"
#                 if gpt_response and not gpt_response.startswith("Error"):
#                     day_entry += f'Diagnoza GPT-5-mini:\n"{gpt_response}"\n\n'
#                 else:
#                     # Fallback to formatted diagnosis
#                     day_entry += f'Diagnoza structurată:\n"{formatted_diagnosis_text}"\n\n'
                
#                 day_entry += "---\n"
#                 gpt_responses.append(day_entry)
                
#             else:
#                 print(f"⚠️ No formatted diagnosis found for {date_str}")
#         else:
#             print(f"⚠️ No data found in formatted diagnoses for {date_str}")
    
#     print(f"✅ Generated {len(gpt_responses)} GPT responses")
#     return gpt_responses

# def create_user_prompt(
#     current_date: str,
#     weather_data: Dict,
#     past_days: int = 5,
#     openai_api_key: str = None
# ) -> str:
#     """
#     Create the user prompt with raw CSV data and diagnosis context.
    
#     Args:
#         current_date (str): Current date for diagnosis
#         weather_data (Dict): Comprehensive weather data
#         past_days (int): Number of past days to include
#         openai_api_key (str): OpenAI API key for GPT calls
    
#     Returns:
#         str: User prompt in Romanian
#     """
    
#     # Start building the user prompt
#     user_prompt = "Analiza meteorologică pentru diagnoză:\n\n"
    
#     # Add step-by-step instruction at the beginning
#     user_prompt += "INSTRUCȚIUNI PENTRU GÂNDIRE PAS CU PAS:\n"
#     user_prompt += "Pentru fiecare propoziție din diagnoza meteorologică, gândește-te pas cu pas:\n"
#     user_prompt += "1. Ce informații specifice sunt necesare pentru această propoziție?\n"
#     user_prompt += "2. Ce date concrete din tabelele de mai jos susțin aceste informații?\n"
#     user_prompt += "3. Cum se compară aceste date cu zilele precedente?\n"
#     user_prompt += "4. Care este concluzia logică pe baza acestor comparații?\n"
#     user_prompt += "5. Cum formulezi această concluzie într-un mod profesional, specific ANM?\n\n"
#     user_prompt += "---\n\n"
    
#     # Extract year from current_date and load formatted diagnoses
#     year = int(current_date.split('-')[0])
#     formatted_diagnoses = load_formatted_diagnoses(year)
    
#     # Extract raw CSV data organized by day (including target date)
#     daily_raw_data = extract_raw_csv_data_by_day(weather_data, current_date, past_days, include_target_date=True)
    
#     # Generate GPT responses for specified number of past days
#     gpt_responses = generate_gpt_responses_for_past_days(
#         daily_raw_data, 
#         formatted_diagnoses, 
#         current_date, 
#         past_days,
#         openai_api_key
#     )
    
#     # Add all GPT responses to the user prompt
#     user_prompt += "EXEMPLE DE ANALIZE METEOROLOGICE ANTERIOARE:\n\n"
#     for response in gpt_responses:
#         user_prompt += response
    
#     user_prompt += "\n"
    
#     # Add current weather data analysis (for the current diagnosis day)
#     user_prompt += f"DATELE METEOROLOGICE PENTRU DIAGNOZA CURENTĂ ({current_date}):\n\n"
    
#     # Add wind speed data with detailed analysis
#     if weather_data.get('wind_analysis', {}).get('mean_speed_ms') is not None:
#         wind_speed = weather_data['wind_analysis']['mean_speed_ms']
#         wind_measurements = weather_data['wind_analysis']['total_measurements']
#         user_prompt += f"🌬️ ANALIZA VÂNTULUI (Rff1):\n"
#         user_prompt += f"- Viteza medie înregistrată: {wind_speed:.1f} m/s\n"
#         user_prompt += f"- Numărul total de măsurători: {wind_measurements}\n"
        
#         # Add wind interpretation
#         if wind_speed < 3:
#             wind_desc = "slab"
#         elif wind_speed < 6:
#             wind_desc = "moderat"
#         else:
#             wind_desc = "puternic"
#         user_prompt += f"- Caracterizare: vânt {wind_desc}\n\n"
    
#     # Add nebulosity data with the 3 most common hours
#     if weather_data.get('nebulosity_analysis', {}).get('most_frequent_value') is not None:
#         nop_value = weather_data['nebulosity_analysis']['most_frequent_value']
#         nop_occurrences = weather_data['nebulosity_analysis']['total_occurrences']
        
#         user_prompt += f"☁️ ANALIZA NEBULOZITĂȚII (Nop):\n"
#         user_prompt += f"- Valoarea cea mai frecventă: {nop_value}/8 (pe scala 1-8)\n"
#         user_prompt += f"- Numărul de înregistrări cu această valoare: {nop_occurrences}\n"
        
#         # Add nebulosity interpretation
#         if int(nop_value) <= 2:
#             nop_desc = "cer senin sau puțin noros"
#         elif int(nop_value) <= 4:
#             nop_desc = "cer parțial noros"
#         elif int(nop_value) <= 6:
#             nop_desc = "cer predominant noros"
#         else:
#             nop_desc = "cer complet acoperit de nori"
#         user_prompt += f"- Caracterizare: {nop_desc}\n"
        
#         # Show only the 3 most common hours
#         common_hours = get_most_common_hours_for_nebulosity(weather_data, nop_value)
#         if common_hours:
#             user_prompt += f"- Cele mai frecvente ore de apariție: {', '.join(common_hours)}\n"
        
#         user_prompt += "\n"
    
#     # Add precipitation analysis
#     if weather_data.get('daily_precipitation'):
#         user_prompt += f"🌧️ ANALIZA PRECIPITAȚIILOR:\n"
        
#         # Get historical days data (excluding current day)
#         historical_days = {k: v for k, v in daily_raw_data.items() if not v.get('is_target_date', False)}
        
#         total_precip = 0
#         rainy_days = 0
        
#         for date_str in sorted(historical_days.keys()):
#             date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
            
#             # Get precipitation mean for this day
#             daily_precip = historical_days[date_str]['precipitation_mean'] or 0.0
            
#             if daily_precip > 0:
#                 user_prompt += f"- {date_display}: {daily_precip:.1f} l/m² (zi cu precipitații)\n"
#                 total_precip += daily_precip
#                 rainy_days += 1
#             else:
#                 user_prompt += f"- {date_display}: {daily_precip:.1f} l/m² (zi fără precipitații)\n"
        
#         user_prompt += f"\nBilanțul precipitațiilor în perioada analizată:\n"
#         user_prompt += f"- Total precipitații: {total_precip:.1f} l/m²\n"
#         user_prompt += f"- Zile cu precipitații: {rainy_days} din {len(historical_days)}\n"
#         if len(historical_days) > 0:
#             user_prompt += f"- Media zilnică: {total_precip/len(historical_days):.1f} l/m²\n"
#         user_prompt += "\n"
    
#     # Add detailed hourly phenomena analysis
#     if weather_data.get('hourly_data', {}).get('raw_data') is not None:
#         hourly_df = weather_data['hourly_data']['raw_data']
        
#         if 'Fenomen' in hourly_df.columns:
#             # Get phenomena and their frequencies
#             phenomena = hourly_df['Fenomen'].dropna()
#             phenomena_clean = phenomena[~phenomena.isin(['nan', 'Nu avem fenomen'])]
            
#             if not phenomena_clean.empty:
#                 user_prompt += f"🌦️ FENOMENE METEOROLOGICE ÎNREGISTRATE:\n"
                
#                 # Count occurrences of each phenomenon
#                 phenomena_counts = phenomena_clean.value_counts()
                
#                 user_prompt += f"Inventarul complet al fenomenelor observate:\n"
#                 for phenomenon, count in phenomena_counts.items():
#                     percentage = (count / len(phenomena)) * 100
#                     user_prompt += f"- {phenomenon}\n"
#                     user_prompt += f"  Frecvența: {count} apariții ({percentage:.1f}% din timpul observat)\n"
                
#                 # Identify repeated phenomena (key for sentence 3 in diagnosis)
#                 repeated_phenomena = phenomena_counts[phenomena_counts > 1]
#                 if not repeated_phenomena.empty:
#                     user_prompt += f"\n⚠️ FENOMENE REPETATE (importante pentru propoziția 3):\n"
#                     for phenomenon, count in repeated_phenomena.items():
#                         user_prompt += f"- {phenomenon}: {count} apariții în ultimele 24h\n"
                
#                 user_prompt += "\n"
    
#     # Add current day raw data (WITHOUT diagnosis - this is what LLM needs to generate)
#     current_day_data = None
#     for date_str, day_data in daily_raw_data.items():
#         if day_data.get('is_target_date', False):
#             current_day_data = (date_str, day_data)
#             break
    
#     if current_day_data:
#         date_str, day_data = current_day_data
#         user_prompt += f"📅 ZIUA CURENTĂ {date_str} (pentru care se generează diagnoza):\n"
        
#         # Display temperature maxima and minima means
#         if day_data['temperature_max_mean'] is not None:
#             user_prompt += f"🌡️ Temperatura medie maximă București: {day_data['temperature_max_mean']:.1f}°C\n"
        
#         if day_data['temperature_min_mean'] is not None:
#             user_prompt += f"🌡️ Temperatura medie minimă București: {day_data['temperature_min_mean']:.1f}°C\n"
        
#         # Display precipitation mean
#         if day_data['precipitation_mean'] is not None:
#             user_prompt += f"🌧️ Precipitații medii București: {day_data['precipitation_mean']:.1f} l/m²\n"
        
#         # Hourly summary data
#         if day_data['hourly_summary'].get('wind'):
#             wind = day_data['hourly_summary']['wind']
#             user_prompt += f"🌬️ Vânt: Media {wind['mean']:.1f} m/s (min: {wind['min']:.1f}, max: {wind['max']:.1f})\n"
        
#         if day_data['hourly_summary'].get('nebulosity'):
#             neb = day_data['hourly_summary']['nebulosity']
#             user_prompt += f"☁️ Nebulozitate: Cel mai frecvent {neb['most_frequent']}/8 ({neb['count']} măsurători)\n"
        
#         if day_data['hourly_summary'].get('phenomena'):
#             user_prompt += f"🌦️ Fenomene:\n"
#             for phenomenon, count in day_data['hourly_summary']['phenomena']:
#                 user_prompt += f"  - {phenomenon}: {count} observații\n"
        
#         # NO DIAGNOSIS TEXT HERE - this is what the LLM needs to generate
#         user_prompt += "\n---\n\n"
    
#     # Add temperature means summary for all days (both max and min)
#     user_prompt += f"📊 MEDIA TEMPERATURILOR PENTRU TOATE ZILELE:\n"
#     all_temp_max_means = []
#     all_temp_min_means = []
    
#     for date_str in sorted(daily_raw_data.keys()):
#         day_data = daily_raw_data[date_str]
#         date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m")
        
#         if day_data['temperature_max_mean'] is not None:
#             all_temp_max_means.append(day_data['temperature_max_mean'])
#             user_prompt += f"- {date_display} Tmax: {day_data['temperature_max_mean']:.1f}°C"
            
#             if day_data['temperature_min_mean'] is not None:
#                 all_temp_min_means.append(day_data['temperature_min_mean'])
#                 user_prompt += f", Tmin: {day_data['temperature_min_mean']:.1f}°C\n"
#             else:
#                 user_prompt += "\n"
#         elif day_data['temperature_min_mean'] is not None:
#             all_temp_min_means.append(day_data['temperature_min_mean'])
#             user_prompt += f"- {date_display} Tmin: {day_data['temperature_min_mean']:.1f}°C\n"
    
#     if all_temp_max_means:
#         overall_temp_max_mean = sum(all_temp_max_means) / len(all_temp_max_means)
#         user_prompt += f"🌡️ Temperatura maximă medie generală: {overall_temp_max_mean:.1f}°C\n"
    
#     if all_temp_min_means:
#         overall_temp_min_mean = sum(all_temp_min_means) / len(all_temp_min_means)
#         user_prompt += f"🌡️ Temperatura minimă medie generală: {overall_temp_min_mean:.1f}°C\n"
    
#     user_prompt += "\n"
    
#     # Add final instructions for current diagnosis
#     user_prompt += f"🎯 SARCINA ACTUALĂ:\n\n"
#     user_prompt += f"Pe baza tuturor datelor prezentate mai sus, elaborează o diagnoză meteorologică profesională pentru ziua de {current_date} pentru București.\n\n"
    
#     user_prompt += f"ELEMENTE CHEIE DE ANALIZAT:\n"
#     if weather_data.get('wind_analysis', {}).get('mean_speed_ms') is not None:
#         user_prompt += f"✓ Viteza medie a vântului (Rff1): {weather_data['wind_analysis']['mean_speed_ms']:.1f} m/s\n"
#     if weather_data.get('nebulosity_analysis', {}).get('most_frequent_value') is not None:
#         user_prompt += f"✓ Nebulozitatea dominantă (Nop): {weather_data['nebulosity_analysis']['most_frequent_value']}/8\n"
#         user_prompt += f"✓ Momentele specifice când s-a înregistrat această nebulozitate\n"
#     user_prompt += f"✓ Fenomenele meteorologice repetate (pentru propoziția opțională 3)\n"
#     user_prompt += f"✓ Temperaturile maxime la cele 3 stații din București (Filaret, Băneasa, Afumați)\n"
#     user_prompt += f"✓ Comparația cu condițiile din zilele precedente (pe baza diagnozelor anterioare)\n\n"
    
#     user_prompt += f"IMPORTANT: Diagnoza trebuie să înceapă cu 'BUCUREȘTI' și să respecte exact structura din instrucțiunile de sistem (5 propoziții, conform ANM România)."
    
#     return user_prompt

# def test_prompt_generation_gpt(
#     current_date,
#     weather_data,
#     saving_past_days,
#     past_days=5,
#     openai_api_key=None
# ):
#     """
#     Test the prompt generation with example data. Maintains original function signature.
#     """
    
#     # Generate prompts
#     system_prompt, user_prompt = create_meteorological_prompts(
#         current_date=current_date,
#         weather_data=weather_data,
#         past_days=past_days,
#         openai_api_key=openai_api_key
#     )
    
#     # Display results
#     print("=" * 80)
#     print(f"SYSTEM PROMPT FOR {past_days} PAST DAYS:")
#     print("=" * 80)
#     print(system_prompt)
    
#     print("\n" + "=" * 80)
#     print(f"USER PROMPT FOR {past_days} PAST DAYS:")
#     print("=" * 80)
#     print(user_prompt)

#     prompts_path = f"prompts\\{current_date}\\{saving_past_days}_past_days"

#     # Create a folder called 'prompts' if it doesn't exist
#     if not os.path.exists(prompts_path):
#         os.makedirs(prompts_path, exist_ok=True)

#     system_prompt_path = f"{prompts_path}\\system_prompt_{current_date}.txt"
#     # Ensure prompts are saved in the 'prompts' folder
#     if not os.path.exists(system_prompt_path):
#         # Save system prompt
#         with open(system_prompt_path, "w", encoding="utf-8") as f:
#             f.write(system_prompt)

#     user_prompt_path = f"{prompts_path}\\user_prompt_{current_date}_{past_days}_past_days.txt"
#     # Save user prompt for this configuration
#     with open(user_prompt_path, "w", encoding="utf-8") as f:
#         f.write(user_prompt)

#     print(f"\n✅ Prompts for {past_days} past days saved to {system_prompt_path} and {user_prompt_path}")

#     # return system_prompt, user_prompt

"""
Prompt construction for the meteorological diagnosis pipeline.

Provides two prompting tracks for building (system, user) prompt pairs:

  PDF-context track (older):
    Embeds raw ANM PDF diagnoses for past days as in-context examples.
    Used by main.py --timestamp.

  GPT-CoT track:
    Generates step-by-step reasoning chains for past days via gpt-5-mini
    and embeds them as in-context examples.
    Used by main.py --get_test_time_interval and by the dataset generators
    (create_train_test_datasets.py, create_zero_shot_test_dataset.py,
     generate_training_data.py).

Public API (signatures unchanged from the previous create_prompts.py and
create_prompts_gpt.py modules):

    extract_raw_csv_data_by_day      reorganize weather data by day
    create_meteorological_prompts    build (system, user) prompt pair
                                     for the GPT-CoT track
    create_prompt_for_gpt            build a single prompt + reply pair
                                     for one past day via gpt-5-mini
    test_prompt_generation           PDF-context track entry point
    test_prompt_generation_gpt       GPT-CoT track entry point
"""

import json
import os
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import openai
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROMPTS_OUTPUT_BASE = Path("prompts")
_FORMATTED_DIAGNOSES_TEMPLATE = "formatted_diagnoses_{year}/formatted_diagnoses_{year}.json"

_OPENAI_EXEMPLAR_MODEL = "gpt-5-mini"
_OPENAI_EXEMPLAR_REASONING_EFFORT = "minimal"
_OPENAI_EXEMPLAR_MAX_OUTPUT_TOKENS = 10000

_PHENOMENA_NULL_VALUES = ("nan", "Nu avem fenomen")


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

def _create_test_model_system_prompt() -> str:
    """
    System prompt for local test models (Ollama) and the SFT messages format.

    Includes the explicit current-day-only instruction (the VITAL block) so
    that small models do not regenerate diagnoses for the past days that
    appear as in-context examples. This was previously injected post-hoc
    by update_test_prompts.py.
    """
    return """VITAL: Tu ești un meteorolog ANM și trebuie să faci DOAR diagnoza pentru ziua curentă specificată în prompt. NU repeta sau reformulezi informațiile din prompt. Concentrează-te EXCLUSIV pe ziua pentru care se cere diagnoza.

Tu ești un meteorolog al Administrației Naționale de Meteorologie din România și trebuie să faci o diagnoză pe baza datelor pe care le primești de la stațiile meteo.

STRUCTURA RĂSPUNSULUI:

1. PRIMA PROPOZIȚIE: Observații generale despre vremea din ziua curentă comparativ cu zilele precedente, pe baza temperaturilor maxime și minime înregistrate.

2. A DOUA PROPOZIȚIE: Descrierea stării cerului (senin sau acoperit de nori, pe baza valorii Nop care variază între 1-8, unde 1 = cer senin, 8 = complet acoperit) și a vântului (slab sau puternic, pe baza valorii Rff1 în m/s, unde sub 3 m/s = slab, peste 6 m/s = puternic).

3. A TREIA PROPOZIȚIE (OPȚIONALĂ): Această propoziție se include DOAR DACĂ un fenomen meteorologic specific s-a repetat în ultimele 24 de ore (de exemplu: ploi, ninsori, ceață, etc.). Dacă nu există fenomene repetate, se omite această propoziție.

4. A PATRA PROPOZIȚIE (sau a treia dacă nu există fenomene repetate): Informații despre temperatura maximă înregistrată la cele 3 stații meteo din București: Filaret, Băneasa și Afumați.

5. PROPOZIȚIA FINALĂ: Pe baza tuturor datelor analizate, o predicție pentru temperaturile de la ora 6:00 dimineața la cele 3 stații din București (Filaret, Băneasa, Afumați).

REGULI ABSOLUTE:
- Răspunsul trebuie să fie CONCIS și DIRECT
- NU include explicații pas cu pas în răspuns
- NU repeta sau reformulezi datele din prompt
- NU menționezi procesul de analiză
- Folosește termeni meteorologici profesioniști
- Fii precis cu valorile numerice
- RĂSPUNDE DOAR CU DIAGNOZA PENTRU ZIUA CURENTĂ SPECIFICATĂ

IMPORTANT: Răspunsul trebuie să înceapă direct cu 'PRIMA PROPOZIȚIE:' și să fie strict conform structurii de mai sus."""


def _create_gpt_exemplar_system_prompt() -> str:
    """
    System prompt for gpt-5-mini when it generates step-by-step reasoning
    chains used as past-day exemplars in the GPT-CoT track.

    This is intentionally distinct from the test-model system prompt: gpt-5-mini
    is asked to ALWAYS show its reasoning so the resulting chain can be embedded
    as an in-context example, whereas the test models are explicitly told NOT to.
    """
    return """Tu ești un meteorolog al Administrației Naționale de Meteorologie din România și trebuie să faci o diagnoză pe baza datelor pe care le primești de la stațiile meteo.

FOARTE IMPORTANT: Pentru fiecare propoziție din diagnoza ta, trebuie să explici mai întâi procesul de gândire pas cu pas, apoi să formulezi propoziția finală.

Structura răspunsului tău trebuie să fie:
...explicația ta pas cu pas pentru prima propoziție...
Prin urmare, PRIMA PROPOZIȚIE: [propoziția finală]

...explicația ta pas cu pas pentru a doua propoziție...
Prin urmare, A DOUA PROPOZIȚIE: [propoziția finală]

...și așa mai departe pentru toate propozițiile...

STRUCTURA RĂSPUNSULUI:

1. PRIMA PROPOZIȚIE: Observații generale despre vremea din ziua curentă comparativ cu zilele precedente, pe baza temperaturilor maxime și minime înregistrate și a informațiilor din prognozele anterioare.

2. A DOUA PROPOZIȚIE: Descrierea stării cerului (senin sau acoperit de nori, pe baza valorii Nop care variază între 1-8, unde 1 = cer senin, 8 = complet acoperit) și a vântului (slab sau puternic, pe baza valorii Rff1 în m/s, unde sub 3 m/s = slab, peste 6 m/s = puternic).

3. A TREIA PROPOZIȚIE (OPȚIONALĂ): Această propoziție se include DOAR DACĂ un fenomen meteorologic specific s-a repetat în ultimele 24 de ore (de exemplu: ploi, ninsori, ceață, etc.). Dacă nu există fenomene repetate, se omite această propoziție.

4. A PATRA PROPOZIȚIE (sau a treia dacă nu există fenomene repetate): Informații despre temperatura maximă înregistrată la cele 3 stații meteo din București: Filaret, Băneasa și Afumați.

5. PROPOZIȚIA FINALĂ: Pe baza tuturor datelor analizate, o predicție pentru temperaturile de la ora 6:00 dimineața la cele 3 stații din București (Filaret, Băneasa, Afumați).

IMPORTANT:
- Răspunsul trebuie să fie în limba română
- Folosește termeni meteorologici profesioniști
- Fii precis cu valorile numerice
- Păstrează tonul profesional specific unui meteorolog ANM
- ARATĂ ÎNTOTDEAUNA procesul de gândire înaintea fiecărei propoziții"""


# ---------------------------------------------------------------------------
# Daily aggregation
# ---------------------------------------------------------------------------

def extract_raw_csv_data_by_day(
    weather_data: Dict,
    target_date_str: str,
    past_days: int,
    include_target_date: bool = False,
) -> Dict[str, Dict]:
    """
    Reorganize the comprehensive weather data dict by day, computing per-day
    means across the three Bucharest stations.

    Args:
        weather_data: Dict from extract_comprehensive_weather_data.
        target_date_str: Target date as 'yyyy-mm-dd'.
        past_days: Number of past days to include.
        include_target_date: If True, the returned dict also contains an
            entry for the target date itself, marked with is_target_date=True.

    NOTE on aggregation: temperature values are summed across the daily
    temperature CSV rows without any (date, station) deduplication, while
    precipitation values ARE deduplicated by (date, station) in the loop
    below. This is inconsistent. Verify against the actual CSV row counts
    whether duplicates can occur in either table and pick one rule for
    both. Both behaviors are preserved here unchanged so as not to silently
    shift any reported metrics.
    """
    daily_data: Dict[str, Dict] = {}
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()

    # When include_target_date=True we cover [target-past_days .. target] (past_days+1 days).
    # When include_target_date=False we cover [target-past_days .. target-1] (past_days days).
    start_offset = 0 if include_target_date else 1
    for i in range(start_offset, past_days + 1):
        d = target_date - timedelta(days=i)
        daily_data[d.strftime("%Y-%m-%d")] = {
            "date": d,
            "temperature_max_mean": None,
            "temperature_min_mean": None,
            "precipitation_mean": None,
            "hourly_summary": {},
            "is_target_date": (i == 0),
        }

    _populate_temperature_means(weather_data, daily_data)
    _populate_precipitation_means(weather_data, daily_data)
    _populate_hourly_summary(weather_data, daily_data)

    return daily_data


def _populate_temperature_means(weather_data: Dict, daily_data: Dict) -> None:
    """Aggregate Tamax24 / Tamin24 across stations for each day."""
    records = weather_data.get("daily_temperatures") or []
    by_date: Dict[str, Dict[str, list]] = {}

    for rec in records:
        date_str = _record_date_str(rec.get("date"))
        if date_str is None:
            continue
        bucket = by_date.setdefault(date_str, {"tmax": [], "tmin": []})

        tmax = rec.get("Tamax24")
        if pd.notna(tmax):
            try:
                bucket["tmax"].append(float(tmax))
            except (TypeError, ValueError):
                pass

        tmin = rec.get("Tamin24")
        if pd.notna(tmin):
            try:
                bucket["tmin"].append(float(tmin))
            except (TypeError, ValueError):
                pass

    for date_str, bucket in by_date.items():
        if date_str not in daily_data:
            continue
        if bucket["tmax"]:
            daily_data[date_str]["temperature_max_mean"] = sum(bucket["tmax"]) / len(bucket["tmax"])
        if bucket["tmin"]:
            daily_data[date_str]["temperature_min_mean"] = sum(bucket["tmin"]) / len(bucket["tmin"])


def _populate_precipitation_means(weather_data: Dict, daily_data: Dict) -> None:
    """Aggregate R24 across stations for each day, deduplicated by (date, station)."""
    records = weather_data.get("daily_precipitation") or []
    by_date: Dict[str, list] = {}
    seen: set = set()

    for rec in records:
        date_str = _record_date_str(rec.get("date"))
        if date_str is None:
            continue
        station = rec.get("Denumire", "Unknown")
        key = (date_str, station)
        if key in seen:
            continue
        seen.add(key)

        r24 = rec.get("R24")
        if pd.notna(r24):
            try:
                by_date.setdefault(date_str, []).append(float(r24))
            except (TypeError, ValueError):
                pass

    for date_str, values in by_date.items():
        if date_str in daily_data and values:
            daily_data[date_str]["precipitation_mean"] = sum(values) / len(values)


def _populate_hourly_summary(weather_data: Dict, daily_data: Dict) -> None:
    """Per-day wind / nebulosity / phenomena stats from the hourly DataFrame."""
    hourly_df = weather_data.get("hourly_data", {}).get("raw_data")
    if hourly_df is None:
        return

    has_rff1 = "Rff1" in hourly_df.columns
    has_nop = "Nop" in hourly_df.columns
    has_phen = "Fenomen" in hourly_df.columns

    for date_str in daily_data.keys():
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_start = datetime.combine(date_obj, datetime.min.time())
        day_end = datetime.combine(date_obj + timedelta(days=1), datetime.min.time())
        mask = (hourly_df["Data masurarii"] >= day_start) & (hourly_df["Data masurarii"] < day_end)
        day_df = hourly_df[mask]

        summary = daily_data[date_str]["hourly_summary"]

        if has_rff1:
            wind = day_df["Rff1"].dropna()
            if len(wind) > 0:
                summary["wind"] = {
                    "mean": float(wind.mean()),
                    "min": float(wind.min()),
                    "max": float(wind.max()),
                }

        if has_nop:
            neb = day_df["Nop"].dropna()
            if len(neb) > 0:
                value, count = Counter(neb).most_common(1)[0]
                summary["nebulosity"] = {"most_frequent": value, "count": count}

        if has_phen:
            phen = day_df["Fenomen"].dropna()
            phen = phen[~phen.isin(_PHENOMENA_NULL_VALUES)]
            if len(phen) > 0:
                summary["phenomena"] = Counter(phen).most_common(3)


def _record_date_str(record_date) -> Optional[str]:
    """Format a record's date field as 'YYYY-MM-DD'."""
    if record_date is None:
        return None
    if hasattr(record_date, "strftime"):
        return record_date.strftime("%Y-%m-%d")
    return str(record_date)


def _get_most_common_hours_for_nebulosity(weather_data: Dict) -> List[str]:
    """
    Return the three most common hours of day at which the dominant nebulosity
    value was observed, formatted as 'HH:00'.
    """
    times = weather_data.get("nebulosity_analysis", {}).get("occurrence_times") or []
    hours: List[int] = []
    for ts in times:
        if hasattr(ts, "hour"):
            hours.append(ts.hour)
        elif hasattr(ts, "strftime"):
            hours.append(int(ts.strftime("%H")))
    if not hours:
        return []
    return [f"{h:02d}:00" for h, _ in Counter(hours).most_common(3)]


# ---------------------------------------------------------------------------
# Shared user-prompt body builders
# ---------------------------------------------------------------------------

def _format_day_data_block(date_str: str, day_data: Dict) -> str:
    """
    One-day weather data block, used in both tracks for past-day exemplars
    and as the gpt-5-mini exemplar generation payload.
    """
    out = f"ZIUA {date_str}:\n"
    if day_data["temperature_max_mean"] is not None:
        out += f"Temperatura medie maximă București: {day_data['temperature_max_mean']:.1f}°C\n"
    if day_data["temperature_min_mean"] is not None:
        out += f"Temperatura medie minimă București: {day_data['temperature_min_mean']:.1f}°C\n"
    if day_data["precipitation_mean"] is not None:
        out += f"Precipitații medii București: {day_data['precipitation_mean']:.1f} l/m²\n"
    summary = day_data["hourly_summary"]
    if summary.get("wind"):
        w = summary["wind"]
        out += f"Vânt: Media {w['mean']:.1f} m/s (min: {w['min']:.1f}, max: {w['max']:.1f})\n"
    if summary.get("nebulosity"):
        nb = summary["nebulosity"]
        out += f"Nebulozitate: Cel mai frecvent {nb['most_frequent']}/8 ({nb['count']} măsurători)\n"
    if summary.get("phenomena"):
        out += "Fenomene:\n"
        for phenomenon, count in summary["phenomena"]:
            out += f"  - {phenomenon}: {count} observații\n"
    return out


def _build_wind_block(weather_data: Dict) -> str:
    wind = weather_data.get("wind_analysis", {})
    speed = wind.get("mean_speed_ms")
    if speed is None:
        return ""
    measurements = wind.get("total_measurements", 0)
    if speed < 3:
        desc = "slab"
    elif speed < 6:
        desc = "moderat"
    else:
        desc = "puternic"
    return (
        "ANALIZA VÂNTULUI (Rff1):\n"
        f"- Viteza medie înregistrată: {speed:.1f} m/s\n"
        f"- Numărul total de măsurători: {measurements}\n"
        f"- Caracterizare: vânt {desc}\n\n"
    )


def _build_nebulosity_block(weather_data: Dict) -> str:
    neb = weather_data.get("nebulosity_analysis", {})
    nop = neb.get("most_frequent_value")
    if nop is None:
        return ""
    occurrences = neb.get("total_occurrences", 0)
    n = int(nop)
    if n <= 2:
        desc = "cer senin sau puțin noros"
    elif n <= 4:
        desc = "cer parțial noros"
    elif n <= 6:
        desc = "cer predominant noros"
    else:
        desc = "cer complet acoperit de nori"

    out = (
        "ANALIZA NEBULOZITĂȚII (Nop):\n"
        f"- Valoarea cea mai frecventă: {nop}/8 (pe scala 1-8)\n"
        f"- Numărul de înregistrări cu această valoare: {occurrences}\n"
        f"- Caracterizare: {desc}\n"
    )
    common = _get_most_common_hours_for_nebulosity(weather_data)
    if common:
        out += f"- Cele mai frecvente ore de apariție: {', '.join(common)}\n"
    return out + "\n"


def _build_precipitation_block(weather_data: Dict, historical_days: Dict) -> str:
    if not weather_data.get("daily_precipitation"):
        return ""

    out = "ANALIZA PRECIPITAȚIILOR:\n"
    total_precip = 0.0
    rainy_days = 0
    for date_str in sorted(historical_days.keys()):
        date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
        daily_precip = historical_days[date_str]["precipitation_mean"] or 0.0
        if daily_precip > 0:
            out += f"- {date_display}: {daily_precip:.1f} l/m² (zi cu precipitații)\n"
            total_precip += daily_precip
            rainy_days += 1
        else:
            out += f"- {date_display}: {daily_precip:.1f} l/m² (zi fără precipitații)\n"

    n = len(historical_days)
    out += "\nBilanțul precipitațiilor în perioada analizată:\n"
    out += f"- Total precipitații: {total_precip:.1f} l/m²\n"
    out += f"- Zile cu precipitații: {rainy_days} din {n}\n"
    if n > 0:
        out += f"- Media zilnică: {total_precip / n:.1f} l/m²\n"
    return out + "\n"


def _build_phenomena_block(weather_data: Dict) -> str:
    hourly_df = weather_data.get("hourly_data", {}).get("raw_data")
    if hourly_df is None or "Fenomen" not in hourly_df.columns:
        return ""

    phen = hourly_df["Fenomen"].dropna()
    cleaned = phen[~phen.isin(_PHENOMENA_NULL_VALUES)]
    if cleaned.empty:
        return ""

    counts = cleaned.value_counts()
    out = "FENOMENE METEOROLOGICE ÎNREGISTRATE:\n"
    out += "Inventarul complet al fenomenelor observate:\n"
    for phenomenon, count in counts.items():
        percentage = (count / len(phen)) * 100
        out += f"- {phenomenon}\n"
        out += f"  Frecvența: {count} apariții ({percentage:.1f}% din timpul observat)\n"

    repeated = counts[counts > 1]
    if not repeated.empty:
        out += "\nFENOMENE REPETATE (importante pentru propoziția 3):\n"
        for phenomenon, count in repeated.items():
            out += f"- {phenomenon}: {count} apariții în ultimele 24h\n"

    return out + "\n"


def _build_current_day_block(current_day_data: Tuple[str, Dict]) -> str:
    date_str, day = current_day_data
    out = f"ZIUA CURENTĂ {date_str} (pentru care se generează diagnoza):\n"
    if day["temperature_max_mean"] is not None:
        out += f"Temperatura medie maximă București: {day['temperature_max_mean']:.1f}°C\n"
    if day["temperature_min_mean"] is not None:
        out += f"Temperatura medie minimă București: {day['temperature_min_mean']:.1f}°C\n"
    if day["precipitation_mean"] is not None:
        out += f"Precipitații medii București: {day['precipitation_mean']:.1f} l/m²\n"
    summary = day["hourly_summary"]
    if summary.get("wind"):
        w = summary["wind"]
        out += f"Vânt: Media {w['mean']:.1f} m/s (min: {w['min']:.1f}, max: {w['max']:.1f})\n"
    if summary.get("nebulosity"):
        nb = summary["nebulosity"]
        out += f"Nebulozitate: Cel mai frecvent {nb['most_frequent']}/8 ({nb['count']} măsurători)\n"
    if summary.get("phenomena"):
        out += "Fenomene:\n"
        for phenomenon, count in summary["phenomena"]:
            out += f"  - {phenomenon}: {count} observații\n"
    return out + "\n---\n\n"


def _build_temperature_summary_block(daily_raw_data: Dict) -> str:
    out = "MEDIA TEMPERATURILOR PENTRU TOATE ZILELE:\n"
    max_means: List[float] = []
    min_means: List[float] = []
    for date_str in sorted(daily_raw_data.keys()):
        day = daily_raw_data[date_str]
        date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m")
        if day["temperature_max_mean"] is not None:
            max_means.append(day["temperature_max_mean"])
            line = f"- {date_display} Tmax: {day['temperature_max_mean']:.1f}°C"
            if day["temperature_min_mean"] is not None:
                min_means.append(day["temperature_min_mean"])
                line += f", Tmin: {day['temperature_min_mean']:.1f}°C"
            out += line + "\n"
        elif day["temperature_min_mean"] is not None:
            min_means.append(day["temperature_min_mean"])
            out += f"- {date_display} Tmin: {day['temperature_min_mean']:.1f}°C\n"

    if max_means:
        out += f"Temperatura maximă medie generală: {sum(max_means) / len(max_means):.1f}°C\n"
    if min_means:
        out += f"Temperatura minimă medie generală: {sum(min_means) / len(min_means):.1f}°C\n"
    return out + "\n"


def _build_task_block(current_date: str, weather_data: Dict) -> str:
    out = "SARCINA ACTUALĂ:\n\n"
    out += (
        "Pe baza tuturor datelor prezentate mai sus, elaborează o diagnoză "
        f"meteorologică profesională pentru ziua de {current_date} pentru București.\n\n"
    )
    out += "ELEMENTE CHEIE DE ANALIZAT:\n"
    wind_speed = weather_data.get("wind_analysis", {}).get("mean_speed_ms")
    if wind_speed is not None:
        out += f"- Viteza medie a vântului (Rff1): {wind_speed:.1f} m/s\n"
    nop = weather_data.get("nebulosity_analysis", {}).get("most_frequent_value")
    if nop is not None:
        out += f"- Nebulozitatea dominantă (Nop): {nop}/8\n"
        out += "- Momentele specifice când s-a înregistrat această nebulozitate\n"
    out += "- Fenomenele meteorologice repetate (pentru propoziția opțională 3)\n"
    out += "- Temperaturile maxime la cele 3 stații din București (Filaret, Băneasa, Afumați)\n"
    out += "- Comparația cu condițiile din zilele precedente (pe baza diagnozelor anterioare)\n\n"
    out += (
        "IMPORTANT: Diagnoza trebuie să înceapă cu 'BUCUREȘTI' și să respecte "
        "exact structura din instrucțiunile de sistem (5 propoziții, conform ANM România)."
    )
    return out


def _wrap_user_prompt_with_target_day_focus(body: str, current_date: str) -> str:
    """
    Bake in the target-day disambiguation header and footer that update_test_prompts.py
    used to apply post-hoc. Both wrappers refer explicitly to the target date so
    small models cannot confuse it with the historical exemplars.
    """
    header = (
        f"ATENȚIE: Creează diagnoza meteorologică DOAR pentru ziua {current_date}. "
        "NU repeta informațiile din prompt.\n\n"
    )
    footer = (
        f"\n\nIMPORTANT: Generează diagnoza meteorologică CONCISĂ pentru ziua "
        f"{current_date} folosind DOAR datele meteorologice prezentate mai sus. "
        "NU include explicații despre procesul de analiză. Răspunde direct cu "
        "diagnoza structurată conform instrucțiunilor."
    )
    return header + body + footer


# ---------------------------------------------------------------------------
# OpenAI exemplar generation (GPT-CoT track)
# ---------------------------------------------------------------------------

def _get_openai_api_key(provided: Optional[str]) -> str:
    """
    Resolve the OpenAI API key. Prefers an explicitly passed key, otherwise
    falls back to the OPENAI_API_KEY environment variable. Raises if neither
    is set.
    """
    if provided:
        return provided
    env = os.environ.get("OPENAI_API_KEY")
    if env:
        return env
    raise RuntimeError(
        "OpenAI API key not provided. Pass openai_api_key explicitly "
        "or set the OPENAI_API_KEY environment variable."
    )


def create_prompt_for_gpt(
    date_str: str,
    day_data: Dict,
    formatted_diagnosis: str,
    openai_api_key: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Build a single-day prompt for gpt-5-mini and call the API to obtain a
    step-by-step reasoning chain that ends in a structured diagnosis.

    Returns (prompt_sent, gpt_response). On API failure, gpt_response is a
    string starting with 'Error generating GPT response:' so callers can
    detect the failure and fall back gracefully.
    """
    prompt = _format_day_data_block(date_str, day_data)
    prompt += "\nEXEMPLU DE DIAGNOZA STRUCTURATĂ:\n"
    prompt += f'"{formatted_diagnosis}"\n\n'
    prompt += (
        "Pe baza acestor date și urmând exemplul de structurare de mai sus, "
        "generează o diagnoză meteorologică completă pentru această zi. "
        "FOARTE IMPORTANT: Arată procesul tău de gândire pas cu pas înaintea fiecărei propoziții!"
    )

    try:
        client = openai.OpenAI(api_key=_get_openai_api_key(openai_api_key))
        response = client.responses.create(
            model=_OPENAI_EXEMPLAR_MODEL,
            reasoning={"effort": _OPENAI_EXEMPLAR_REASONING_EFFORT},
            instructions=_create_gpt_exemplar_system_prompt(),
            input=prompt,
            max_output_tokens=_OPENAI_EXEMPLAR_MAX_OUTPUT_TOKENS,
        )
        return prompt, response.output_text
    except Exception as e:
        print(f"ERROR calling OpenAI API for {date_str}: {e}")
        return prompt, f"Error generating GPT response: {e}"


def _load_formatted_diagnoses(year: int) -> Dict:
    """Load the formatted_diagnoses_{year}.json file produced by create_dataset.py."""
    path = Path(_FORMATTED_DIAGNOSES_TEMPLATE.format(year=year))
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded formatted diagnoses for {year}: {len(data)} dates")
        return data
    except FileNotFoundError:
        print(f"ERROR: formatted diagnoses file not found: {path}")
        return {}
    except Exception as e:
        print(f"ERROR loading formatted diagnoses from {path}: {e}")
        return {}


def _generate_gpt_responses_for_past_days(
    daily_raw_data: Dict,
    formatted_diagnoses: Dict,
    past_days: int,
    openai_api_key: Optional[str],
) -> List[str]:
    """
    For each of the most recent past_days historical days that have a formatted
    reference diagnosis, call gpt-5-mini to generate a reasoning-chain exemplar
    and return the rendered exemplar block as a string.

    Days for which the API call fails fall back to embedding the formatted
    reference diagnosis directly (visibly labeled as a fallback) so the
    historical context block is never silently empty.
    """
    historical_dates = sorted(
        (d for d, dd in daily_raw_data.items() if not dd.get("is_target_date", False)),
        reverse=True,
    )[:past_days]

    blocks: List[str] = []
    successes = 0
    fallbacks = 0
    skipped = 0

    for date_str in historical_dates:
        day_data = daily_raw_data[date_str]
        diag_entry = formatted_diagnoses.get(date_str)
        if not diag_entry or "formatted_diagnosis" not in diag_entry:
            skipped += 1
            continue
        formatted_text = diag_entry["formatted_diagnosis"].get("PRIMA_PROPOZITIE")
        if not formatted_text:
            skipped += 1
            continue

        _, gpt_response = create_prompt_for_gpt(
            date_str, day_data, formatted_text, openai_api_key
        )

        block = _format_day_data_block(date_str, day_data)
        block += f"Diagnoza pentru {date_str}:\n"
        if gpt_response and not gpt_response.startswith("Error"):
            block += f'Diagnoza GPT-5-mini:\n"{gpt_response}"\n\n'
            successes += 1
        else:
            block += f'Diagnoza structurată:\n"{formatted_text}"\n\n'
            fallbacks += 1
        block += "---\n"
        blocks.append(block)

    print(
        f"GPT exemplars for past days: "
        f"{successes} ok, {fallbacks} fallback, {skipped} skipped"
    )
    return blocks


# ---------------------------------------------------------------------------
# User prompt: GPT-CoT track
# ---------------------------------------------------------------------------

def _create_user_prompt_gpt_track(
    current_date: str,
    weather_data: Dict,
    past_days: int,
    openai_api_key: Optional[str],
) -> str:
    """
    Build the user prompt for the GPT-CoT track. Past-day exemplars come from
    live gpt-5-mini reasoning chains generated against the formatted reference
    diagnoses.
    """
    body = "Analiza meteorologică pentru diagnoză:\n\n"
    body += "INSTRUCȚIUNI PENTRU GÂNDIRE PAS CU PAS:\n"
    body += "Pentru fiecare propoziție din diagnoza meteorologică, gândește-te pas cu pas:\n"
    body += "1. Ce informații specifice sunt necesare pentru această propoziție?\n"
    body += "2. Ce date concrete din tabelele de mai jos susțin aceste informații?\n"
    body += "3. Cum se compară aceste date cu zilele precedente?\n"
    body += "4. Care este concluzia logică pe baza acestor comparații?\n"
    body += "5. Cum formulezi această concluzie într-un mod profesional, specific ANM?\n\n"
    body += "---\n\n"

    year = int(current_date.split("-")[0])
    formatted_diagnoses = _load_formatted_diagnoses(year)

    daily_raw_data = extract_raw_csv_data_by_day(
        weather_data, current_date, past_days, include_target_date=True
    )

    exemplars = _generate_gpt_responses_for_past_days(
        daily_raw_data, formatted_diagnoses, past_days, openai_api_key
    )

    body += "EXEMPLE DE ANALIZE METEOROLOGICE ANTERIOARE:\n\n"
    for ex in exemplars:
        body += ex
    body += "\n"

    body += f"DATELE METEOROLOGICE PENTRU DIAGNOZA CURENTĂ ({current_date}):\n\n"
    body += _build_wind_block(weather_data)
    body += _build_nebulosity_block(weather_data)

    historical_days = {
        d: dd for d, dd in daily_raw_data.items() if not dd.get("is_target_date", False)
    }
    body += _build_precipitation_block(weather_data, historical_days)
    body += _build_phenomena_block(weather_data)

    current_day_data = next(
        ((d, dd) for d, dd in daily_raw_data.items() if dd.get("is_target_date", False)),
        None,
    )
    if current_day_data is not None:
        body += _build_current_day_block(current_day_data)

    body += _build_temperature_summary_block(daily_raw_data)
    body += _build_task_block(current_date, weather_data)

    return _wrap_user_prompt_with_target_day_focus(body, current_date)


# ---------------------------------------------------------------------------
# User prompt: PDF-context track
# ---------------------------------------------------------------------------

def _create_user_prompt_pdf_track(
    current_date: str,
    weather_data: Dict,
    pdf_forecasts: Dict[str, Dict[str, str]],
    past_days: int,
) -> str:
    """
    Build the user prompt for the PDF-context track. Past-day exemplars come
    from raw ANM PDF diagnoses; historical days without a corresponding PDF
    are filtered out so the prompt only contains days with verifiable context.
    """
    body = "Analiza meteorologică pentru diagnoză:\n\n"

    daily_raw_data = extract_raw_csv_data_by_day(
        weather_data, current_date, past_days, include_target_date=True
    )

    # The forecast PDF for date D+1 contains the diagnosis covering day D, so
    # we restrict to forecasts at or before current_date.
    current_date_obj = datetime.strptime(current_date, "%Y-%m-%d").date()
    previous_forecasts = {
        k: v
        for k, v in pdf_forecasts.items()
        if datetime.strptime(k, "%Y-%m-%d").date() <= current_date_obj
    }

    historical_days_all = {
        d: dd for d, dd in daily_raw_data.items() if not dd.get("is_target_date", False)
    }
    current_day_data = next(
        ((d, dd) for d, dd in daily_raw_data.items() if dd.get("is_target_date", False)),
        None,
    )

    # Pair each historical day D with the forecast keyed at D+1.
    historical_days: Dict[str, Dict] = {}
    for date_str, day_data in historical_days_all.items():
        next_day = (
            datetime.strptime(date_str, "%Y-%m-%d").date() + timedelta(days=1)
        ).strftime("%Y-%m-%d")
        if next_day in previous_forecasts:
            historical_days[date_str] = day_data

    if not historical_days:
        print(f"WARNING: no historical days with matching PDF forecasts for {current_date}")

    # Render historical days in reverse chronological order, each with its
    # paired diagnosis text.
    for date_str in sorted(historical_days.keys(), reverse=True):
        day_data = historical_days[date_str]
        body += _format_day_data_block(date_str, day_data)

        next_day = (
            datetime.strptime(date_str, "%Y-%m-%d").date() + timedelta(days=1)
        ).strftime("%Y-%m-%d")
        forecast_data = previous_forecasts[next_day]
        body += f"Diagnoza pentru {date_str}:\n"
        body += f"Intervalul analizat: {forecast_data['interval']}\n\n"
        forecast_text = forecast_data["forecast_text"]
        bucuresti_index = forecast_text.find("BUCUREȘTI")
        if bucuresti_index != -1:
            body += f'Diagnoza completă:\n"{forecast_text[bucuresti_index:].strip()}"\n\n'
        else:
            body += f'Textul complet:\n"{forecast_text}"\n\n'
        body += "---\n"

    body += "\n"
    body += f"DATELE METEOROLOGICE PENTRU DIAGNOZA CURENTĂ ({current_date}):\n\n"
    body += _build_wind_block(weather_data)
    body += _build_nebulosity_block(weather_data)
    body += _build_precipitation_block(weather_data, historical_days)
    body += _build_phenomena_block(weather_data)
    if current_day_data is not None:
        body += _build_current_day_block(current_day_data)
    body += _build_temperature_summary_block(daily_raw_data)
    body += _build_task_block(current_date, weather_data)

    return _wrap_user_prompt_with_target_day_focus(body, current_date)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def create_meteorological_prompts(
    current_date: str,
    weather_data: Dict,
    past_days: int = 5,
    openai_api_key: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Build the (system, user) prompt pair for the GPT-CoT track.
    Returns (system_prompt, user_prompt).
    """
    system_prompt = _create_test_model_system_prompt()
    user_prompt = _create_user_prompt_gpt_track(
        current_date, weather_data, past_days, openai_api_key
    )
    return system_prompt, user_prompt


def _save_prompts_to_disk(
    system_prompt: str,
    user_prompt: str,
    current_date: str,
    saving_past_days: int,
    user_prompt_past_days: int,
) -> None:
    """
    Save prompts to prompts/{current_date}/{saving_past_days}_past_days/.

    The system prompt is always overwritten so that any update to its body
    propagates to disk on the next run. The user prompt filename includes
    its own past_days count so multiple configurations can coexist.
    """
    out_dir = _PROMPTS_OUTPUT_BASE / current_date / f"{saving_past_days}_past_days"
    out_dir.mkdir(parents=True, exist_ok=True)

    system_path = out_dir / f"system_prompt_{current_date}.txt"
    system_path.write_text(system_prompt, encoding="utf-8")

    user_path = out_dir / f"user_prompt_{current_date}_{user_prompt_past_days}_past_days.txt"
    user_path.write_text(user_prompt, encoding="utf-8")

    print(f"Saved prompts for {current_date} (past_days={user_prompt_past_days}) to {out_dir}")


def test_prompt_generation(
    current_date: str,
    weather_data: Dict,
    pdf_forecasts: Dict[str, Dict[str, str]],
    saving_past_days: int,
    past_days: int = 5,
) -> None:
    """Build and save prompts for the PDF-context track."""
    print(f"Building PDF-context prompts for {current_date} (past_days={past_days})")
    system_prompt = _create_test_model_system_prompt()
    user_prompt = _create_user_prompt_pdf_track(
        current_date, weather_data, pdf_forecasts, past_days
    )
    _save_prompts_to_disk(
        system_prompt, user_prompt, current_date, saving_past_days, past_days
    )


def test_prompt_generation_gpt(
    current_date: str,
    weather_data: Dict,
    saving_past_days: int,
    past_days: int = 5,
    openai_api_key: Optional[str] = None,
) -> None:
    """Build and save prompts for the GPT-CoT track."""
    print(f"Building GPT-CoT prompts for {current_date} (past_days={past_days})")
    system_prompt, user_prompt = create_meteorological_prompts(
        current_date=current_date,
        weather_data=weather_data,
        past_days=past_days,
        openai_api_key=openai_api_key,
    )
    _save_prompts_to_disk(
        system_prompt, user_prompt, current_date, saving_past_days, past_days
    )
    
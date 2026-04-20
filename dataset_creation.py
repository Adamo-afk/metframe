# #########################################################################
# ####################### generate_training_data.py #######################
# #########################################################################





# #!/usr/bin/env python3
# """
# Script to generate train_data.json in the correct format for fine-tuning.
# Converts daily_raw_data to proper system/user/assistant message format.
# """

# import json
# import os
# from pathlib import Path
# from typing import Dict, List, Any
# import logging
# from datetime import datetime, date

# # Import existing functions
# from prompting.utils.check_data_availability import check_data_availability
# from prompting.utils.extract_data_from_tables import extract_comprehensive_weather_data
# from prompting.utils.create_prompts_gpt import extract_raw_csv_data_by_day
# from prompting.utils.config import get_training_date_ranges

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# def json_serializer(obj: Any) -> Any:
#     """Custom JSON serializer to handle date/datetime objects."""
#     if isinstance(obj, (datetime, date)):
#         return obj.isoformat()
#     raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# class TrainingDataGenerator:
#     def __init__(self, year: int = 2024, past_days: int = 5):
#         self.year = year
#         self.past_days = past_days
        
#         # Load formatted diagnoses
#         self.formatted_diagnoses = self.load_formatted_diagnoses()
        
#         # Get training dates
#         self.training_dates = get_training_date_ranges(year)
        
#         logger.info(f"Initialized TrainingDataGenerator for {year}")
#         logger.info(f"Training dates: {len(self.training_dates)}")

#     def load_formatted_diagnoses(self) -> Dict:
#         """Load formatted diagnoses from JSON file."""
#         file_path = f"formatted_diagnoses_{self.year}/formatted_diagnoses_{self.year}.json"
        
#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 data = json.load(f)
#             logger.info(f"Loaded {len(data)} formatted diagnoses from {file_path}")
#             return data
#         except FileNotFoundError:
#             logger.error(f"Could not find file: {file_path}")
#             return {}
#         except Exception as e:
#             logger.error(f"Error loading formatted diagnoses: {str(e)}")
#             return {}

#     def weather_data_extractor(self, date: str, past_days: int):
#         """Extract weather data for a given date."""
#         try:
#             result = check_data_availability(date, past_days)
#             if not result.get('sufficient_data', False):
#                 logger.warning(f"Insufficient data for {date}")
#                 return None
            
#             all_table_data = extract_comprehensive_weather_data(date, past_days)
#             return all_table_data
            
#         except Exception as e:
#             logger.error(f"Error extracting weather data for {date}: {str(e)}")
#             return None

#     def create_system_prompt(self) -> str:
#         """Create the system prompt for training."""
#         return """IMPORTANT: Tu ești un meteorolog ANM și trebuie să faci DOAR diagnoza pentru ziua curentă specificată în prompt. NU repeta informațiile din zilele precedente. Concentrează-te EXCLUSIV pe ziua pentru care se cere diagnoza.

#     Tu ești un meteorolog al Administrației Naționale de Meteorologie din România și trebuie să faci o diagnoză pe baza datelor pe care le primești de la stațiile meteo.

#     STRUCTURA RĂSPUNSULUI:

#     1. PRIMA PROPOZIȚIE: Observații generale despre vremea din ziua curentă comparativ cu zilele precedente, pe baza temperaturilor maxime și minime înregistrate.

#     2. A DOUA PROPOZIȚIE: Descrierea stării cerului (senin sau acoperit de nori, pe baza valorii Nop care variază între 1-8, unde 1 = cer senin, 8 = complet acoperit) și a vântului (slab sau puternic, pe baza valorii Rff1 în m/s, unde sub 3 m/s = slab, peste 6 m/s = puternic).

#     3. A TREIA PROPOZIȚIE (OPȚIONALĂ): Această propoziție se include DOAR DACĂ un fenomen meteorologic specific s-a repetat în ultimele 24 de ore (de exemplu: ploi, ninsori, ceață, etc.). Dacă nu există fenomene repetate, se omite această propoziție.

#     4. A PATRA PROPOZIȚIE (sau a treia dacă nu există fenomene repetate): Informații despre temperatura maximă înregistrată la cele 3 stații meteo din București: Filaret, Băneasa și Afumați.

#     5. PROPOZIȚIA FINALĂ: Pe baza tuturor datelor analizate, o predicție pentru temperaturile de la ora 6:00 dimineața la cele 3 stații din București (Filaret, Băneasa, Afumați).

#     REGULI CRITICE:
#     - Răspunsul trebuie să fie CONCIS și DIRECT
#     - NU include explicații pas cu pas
#     - NU repeta datele din prompt  
#     - Folosește termeni meteorologici profesioniști
#     - Fii precis cu valorile numerice
#     - CONCENTREAZĂ-TE DOAR PE ZIUA CURENTĂ SPECIFICATĂ ÎN PROMPT"""

#     def create_user_prompt_from_daily_data(self, daily_raw_data: Dict, current_date: str) -> str:
#         """Create user prompt from daily raw data."""
        
#         user_prompt = f"DIAGNOZĂ METEOROLOGICĂ PENTRU ZIUA {current_date}:\n\n"
        
#         # Get current day data
#         current_day_data = None
#         for date_str, day_data in daily_raw_data.items():
#             if day_data.get('is_target_date', False):
#                 current_day_data = (date_str, day_data)
#                 break
        
#         if current_day_data:
#             date_str, day_data = current_day_data
            
#             user_prompt += f"DATELE PENTRU ZIUA {date_str}:\n"
            
#             # Temperature data
#             if day_data['temperature_max_mean'] is not None:
#                 user_prompt += f"Temperatura maximă: {day_data['temperature_max_mean']:.1f}°C\n"
            
#             if day_data['temperature_min_mean'] is not None:
#                 user_prompt += f"Temperatura minimă: {day_data['temperature_min_mean']:.1f}°C\n"
            
#             # Wind data
#             if day_data['hourly_summary'].get('wind'):
#                 wind = day_data['hourly_summary']['wind']
#                 user_prompt += f"Vânt: {wind['mean']:.1f} m/s\n"
            
#             # Nebulosity data
#             if day_data['hourly_summary'].get('nebulosity'):
#                 neb = day_data['hourly_summary']['nebulosity']
#                 user_prompt += f"Nebulozitate: {neb['most_frequent']}/8\n"
            
#             # Phenomena data
#             if day_data['hourly_summary'].get('phenomena'):
#                 user_prompt += f"Fenomene:\n"
#                 for phenomenon, count in day_data['hourly_summary']['phenomena'][:3]:  # Limit to top 3
#                     user_prompt += f"- {phenomenon}: {count} observații\n"
        
#         # Add brief historical context (simplified)
#         user_prompt += f"\nCONTEXT ISTORIC (pentru comparație):\n"
        
#         historical_days = {k: v for k, v in daily_raw_data.items() if not v.get('is_target_date', False)}
        
#         for date_str in sorted(historical_days.keys(), reverse=True)[:3]:  # Only last 3 days
#             day_data = historical_days[date_str]
#             date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m")
            
#             if day_data['temperature_max_mean'] is not None:
#                 user_prompt += f"{date_display}: Tmax {day_data['temperature_max_mean']:.1f}°C\n"
        
#         user_prompt += f"\nCREEAZĂ DIAGNOZA METEOROLOGICĂ PENTRU ZIUA {current_date} FOLOSIND DOAR DATELE DE MAI SUS."
        
#         return user_prompt

#     def generate_training_data(self) -> List[Dict]:
#         """Generate training data in messages format."""
        
#         logger.info("Generating training data in messages format...")
#         training_data = []
        
#         # Create system prompt once
#         system_prompt = self.create_system_prompt()
        
#         for i, date in enumerate(self.training_dates):
#             try:
#                 # Check if date exists in formatted diagnoses
#                 if date not in self.formatted_diagnoses:
#                     logger.warning(f"No formatted diagnosis for {date}")
#                     continue
                
#                 # Extract weather data
#                 weather_data = self.weather_data_extractor(date, self.past_days)
#                 if not weather_data:
#                     logger.warning(f"No weather data for {date}")
#                     continue
                
#                 # Extract day data composition
#                 daily_raw_data = extract_raw_csv_data_by_day(
#                     weather_data, date, self.past_days, include_target_date=True
#                 )
                
#                 # Get ground truth diagnosis
#                 gt_data = self.formatted_diagnoses[date]
#                 if 'formatted_diagnosis' in gt_data and 'PRIMA_PROPOZITIE' in gt_data['formatted_diagnosis']:
#                     target_diagnosis = gt_data['formatted_diagnosis']['PRIMA_PROPOZITIE']
#                 else:
#                     target_diagnosis = gt_data.get('original_diagnosis', '')
                
#                 if not target_diagnosis:
#                     logger.warning(f"No target diagnosis for {date}")
#                     continue
                
#                 # Create user prompt from daily data
#                 user_prompt = self.create_user_prompt_from_daily_data(daily_raw_data, date)
                
#                 # Create training example in messages format
#                 training_example = {
#                     "messages": [
#                         {"role": "system", "content": system_prompt},
#                         {"role": "user", "content": user_prompt},
#                         {"role": "assistant", "content": target_diagnosis}
#                     ],
#                     "date": date,
#                 }
                
#                 training_data.append(training_example)
                
#                 if (i + 1) % 50 == 0:
#                     logger.info(f"Processed {i + 1}/{len(self.training_dates)} training dates")
                
#             except Exception as e:
#                 logger.error(f"Error processing training date {date}: {str(e)}")
#                 continue
        
#         logger.info(f"Generated {len(training_data)} training examples")
#         return training_data

#     def save_training_data(self, training_data: List[Dict]):
#         """Save training data to JSON file."""
        
#         train_file = "train_data.json"
#         with open(train_file, 'w', encoding='utf-8') as f:
#             json.dump(training_data, f, indent=2, ensure_ascii=False, default=json_serializer)
#         logger.info(f"Saved {len(training_data)} training examples to {train_file}")
        
#         # Create summary
#         summary = {
#             "created_at": datetime.now().isoformat(),
#             "format": "messages",
#             "year": self.year,
#             "past_days": self.past_days,
#             "training_data": {
#                 "file": train_file,
#                 "count": len(training_data),
#                 "date_range": f"{self.training_dates[0]} to {self.training_dates[-1]}" if training_data else "No data"
#             }
#         }
        
#         summary_file = "training_data_summary.json"
#         with open(summary_file, 'w', encoding='utf-8') as f:
#             json.dump(summary, f, indent=2, ensure_ascii=False, default=json_serializer)
#         logger.info(f"Saved training data summary to {summary_file}")

#     def generate_and_save(self):
#         """Main method to generate and save training data."""
        
#         if not self.formatted_diagnoses:
#             logger.error("No formatted diagnoses loaded. Cannot create training data.")
#             return False
        
#         logger.info("Starting training data generation...")
        
#         # Generate training data
#         training_data = self.generate_training_data()
        
#         if not training_data:
#             logger.error("No training data generated.")
#             return False
        
#         # Save training data
#         self.save_training_data(training_data)
        
#         # Print summary
#         print("\n" + "="*60)
#         print("TRAINING DATA GENERATION SUMMARY")
#         print("="*60)
#         print(f"Format: Messages (system/user/assistant)")
#         print(f"Year: {self.year}")
#         print(f"Past days: {self.past_days}")
#         print(f"Training examples: {len(training_data)}")
#         print(f"File created: train_data.json")
#         print("="*60)
        
#         return True

# def validate_training_data():
#     """Validate the generated training data."""
    
#     logger.info("Validating training data...")
    
#     if not Path("train_data.json").exists():
#         logger.error("File not found: train_data.json")
#         return False
    
#     try:
#         with open("train_data.json", 'r', encoding='utf-8') as f:
#             train_data = json.load(f)
        
#         if not train_data:
#             logger.error("Training data is empty")
#             return False
        
#         # Check first example structure
#         # DON'T NEED past_days FIELD
#         example = train_data[0]
#         required_fields = ["messages", "date"]
#         for field in required_fields:
#             if field not in example:
#                 logger.error(f"Missing field in training data: {field}")
#                 return False
        
#         # Check messages structure
#         messages = example["messages"]
#         if len(messages) != 3:
#             logger.error(f"Expected 3 messages, got {len(messages)}")
#             return False
        
#         expected_roles = ["system", "user", "assistant"]
#         for i, message in enumerate(messages):
#             if message.get("role") != expected_roles[i]:
#                 logger.error(f"Expected role '{expected_roles[i]}', got '{message.get('role')}'")
#                 return False
            
#             if not message.get("content"):
#                 logger.error(f"Empty content for role '{expected_roles[i]}'")
#                 return False
        
#         logger.info(f"Training data validation passed ({len(train_data)} examples)")
#         return True
        
#     except Exception as e:
#         logger.error(f"Error validating training data: {e}")
#         return False

# def inspect_training_example():
#     """Inspect a training example to show structure."""
#     try:
#         with open("train_data.json", 'r', encoding='utf-8') as f:
#             train_data = json.load(f)
        
#         if train_data:
#             print("\n" + "="*60)
#             print("TRAINING DATA EXAMPLE")
#             print("="*60)
#             example = train_data[0]
#             print(f"Date: {example['date']}")
#             print(f"Past days: {example['past_days']}")
#             print(f"Messages: {len(example['messages'])}")
            
#             for i, message in enumerate(example['messages']):
#                 print(f"\nMessage {i+1} ({message['role']}):")
#                 content = message['content']
#                 if len(content) > 200:
#                     print(f"  Content: {content[:200]}...")
#                     print(f"  Length: {len(content)} characters")
#                 else:
#                     print(f"  Content: {content}")
#             print("="*60)
#     except Exception as e:
#         print(f"Error inspecting training data: {e}")

# def main():
#     """Main function to generate training data."""
    
#     print("Training Data Generator (Messages Format)")
#     print("="*50)
    
#     # Generate training data
#     generator = TrainingDataGenerator(year=2024, past_days=5)
#     success = generator.generate_and_save()
    
#     if success:
#         # Validate training data
#         validation_success = validate_training_data()
        
#         if validation_success:
#             # Show example
#             inspect_training_example()
            
#             print("\nTraining data generation completed successfully!")
#             print("File created: train_data.json")
#             print("Format: Messages (system/user/assistant)")
#             print("Ready for fine-tuning!")
#         else:
#             print("\nTraining data validation failed!")
#     else:
#         print("\nTraining data generation failed!")

# if __name__ == "__main__":
#     main()





# #############################################################################
# ####################### create_train_test_datasets.py #######################
# #############################################################################





# #!/usr/bin/env python3
# """
# Script to create train_data.json and test_data.json from formatted_diagnoses_2024.json
# """

# import json
# import os
# from pathlib import Path
# from typing import Dict, List, Any
# import logging
# from datetime import datetime, date

# # Import existing functions
# from prompting.utils.check_data_availability import check_data_availability
# from prompting.utils.extract_data_from_tables import extract_comprehensive_weather_data
# from prompting.utils.create_prompts_gpt import (
#     extract_raw_csv_data_by_day, 
#     create_meteorological_prompts,
#     create_prompt_for_gpt
# )
# from prompting.utils.config import get_testing_dates, get_training_date_ranges

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# def json_serializer(obj: Any) -> Any:
#     """Custom JSON serializer to handle date/datetime objects."""
#     if isinstance(obj, (datetime, date)):
#         return obj.isoformat()
#     raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# class DatasetCreator:
#     def __init__(self, year: int = 2024, past_days: int = 5):
#         self.year = year
#         self.past_days = past_days
        
#         # OpenAI API key
#         self.openai_api_key = ...
        
#         # Load formatted diagnoses
#         self.formatted_diagnoses = self.load_formatted_diagnoses()
        
#         # Get date splits
#         self.training_dates = get_training_date_ranges(year)
#         self.testing_dates = get_testing_dates(year)
        
#         logger.info(f"Initialized DatasetCreator for {year}")
#         logger.info(f"Training dates: {len(self.training_dates)}")
#         logger.info(f"Testing dates: {len(self.testing_dates)} - {self.testing_dates}")

#     def load_formatted_diagnoses(self) -> Dict:
#         """Load formatted diagnoses from JSON file."""
#         file_path = f"formatted_diagnoses_{self.year}/formatted_diagnoses_{self.year}.json"
        
#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 data = json.load(f)
#             logger.info(f"Loaded {len(data)} formatted diagnoses from {file_path}")
#             return data
#         except FileNotFoundError:
#             logger.error(f"Could not find file: {file_path}")
#             return {}
#         except Exception as e:
#             logger.error(f"Error loading formatted diagnoses: {str(e)}")
#             return {}

#     def weather_data_extractor(self, date: str, past_days: int):
#         """Extract weather data for a given date."""
#         try:
#             result = check_data_availability(date, past_days)
#             if not result.get('sufficient_data', False):
#                 logger.warning(f"Insufficient data for {date}")
#                 return None
            
#             all_table_data = extract_comprehensive_weather_data(date, past_days)
#             return all_table_data
            
#         except Exception as e:
#             logger.error(f"Error extracting weather data for {date}: {str(e)}")
#             return None

#     def create_training_data(self) -> List[Dict]:
#         """Create training dataset with day data composition only."""
        
#         logger.info("Creating training dataset...")
#         training_data = []
        
#         for i, date in enumerate(self.training_dates):
#             try:
#                 # Check if date exists in formatted diagnoses
#                 if date not in self.formatted_diagnoses:
#                     logger.warning(f"No formatted diagnosis for {date}")
#                     continue
                
#                 # Extract weather data
#                 weather_data = self.weather_data_extractor(date, self.past_days)
#                 if not weather_data:
#                     logger.warning(f"No weather data for {date}")
#                     continue
                
#                 # Extract day data composition
#                 daily_raw_data = extract_raw_csv_data_by_day(
#                     weather_data, date, self.past_days, include_target_date=True
#                 )
                
#                 # Get ground truth diagnosis
#                 gt_data = self.formatted_diagnoses[date]
#                 if 'formatted_diagnosis' in gt_data and 'PRIMA_PROPOZITIE' in gt_data['formatted_diagnosis']:
#                     target_diagnosis = gt_data['formatted_diagnosis']['PRIMA_PROPOZITIE']
#                 else:
#                     target_diagnosis = gt_data.get('original_diagnosis', '')
                
#                 if not target_diagnosis:
#                     logger.warning(f"No target diagnosis for {date}")
#                     continue
                
#                 # Create training example with day data composition
#                 training_example = {
#                     "date": date,
#                     "past_days": self.past_days,
#                     "daily_raw_data": daily_raw_data,
#                     "target_diagnosis": target_diagnosis,
#                     "weather_data_summary": {
#                         "wind_speed_ms": weather_data.get('wind_analysis', {}).get('mean_speed_ms'),
#                         "nebulosity_frequent": weather_data.get('nebulosity_analysis', {}).get('most_frequent_value'),
#                         "temperature_records": len(weather_data.get('daily_temperatures', [])),
#                         "precipitation_records": len(weather_data.get('daily_precipitation', []))
#                     }
#                 }
                
#                 training_data.append(training_example)
                
#                 if (i + 1) % 50 == 0:
#                     logger.info(f"Processed {i + 1}/{len(self.training_dates)} training dates")
                
#             except Exception as e:
#                 logger.error(f"Error processing training date {date}: {str(e)}")
#                 continue
        
#         logger.info(f"Created {len(training_data)} training examples")
#         return training_data

#     def create_testing_data(self) -> List[Dict]:
#         """Create testing dataset with system and user prompts, calling GPT API."""
        
#         logger.info("Creating testing dataset...")
#         testing_data = []
        
#         for date in self.testing_dates:
#             try:
#                 logger.info(f"Processing testing date: {date}")
                
#                 # Extract weather data
#                 weather_data = self.weather_data_extractor(date, self.past_days)
#                 if not weather_data:
#                     logger.warning(f"No weather data for {date}")
#                     continue
                
#                 # Create system and user prompts
#                 system_prompt, user_prompt = create_meteorological_prompts(
#                     current_date=date,
#                     weather_data=weather_data,
#                     past_days=self.past_days,
#                     openai_api_key=self.openai_api_key
#                 )
                
#                 # Get day data composition for reference
#                 daily_raw_data = extract_raw_csv_data_by_day(
#                     weather_data, date, self.past_days, include_target_date=True
#                 )
                
#                 # Get reference diagnosis if available
#                 reference_diagnosis = ""
#                 if date in self.formatted_diagnoses:
#                     gt_data = self.formatted_diagnoses[date]
#                     if 'formatted_diagnosis' in gt_data and 'PRIMA_PROPOZITIE' in gt_data['formatted_diagnosis']:
#                         reference_diagnosis = gt_data['formatted_diagnosis']['PRIMA_PROPOZITIE']
#                     else:
#                         reference_diagnosis = gt_data.get('original_diagnosis', '')
                
#                 # Create testing example
#                 testing_example = {
#                     "date": date,
#                     "past_days": self.past_days,
#                     "system_prompt": system_prompt,
#                     "user_prompt": user_prompt,
#                     "daily_raw_data": daily_raw_data,
#                     "reference_diagnosis": reference_diagnosis,
#                     "weather_data_summary": {
#                         "wind_speed_ms": weather_data.get('wind_analysis', {}).get('mean_speed_ms'),
#                         "nebulosity_frequent": weather_data.get('nebulosity_analysis', {}).get('most_frequent_value'),
#                         "temperature_records": len(weather_data.get('daily_temperatures', [])),
#                         "precipitation_records": len(weather_data.get('daily_precipitation', []))
#                     }
#                 }
                
#                 testing_data.append(testing_example)
#                 logger.info(f"Successfully processed testing date: {date}")
                
#             except Exception as e:
#                 logger.error(f"Error processing testing date {date}: {str(e)}")
#                 continue
        
#         logger.info(f"Created {len(testing_data)} testing examples")
#         return testing_data

#     def save_datasets(self, training_data: List[Dict], testing_data: List[Dict]):
#         """Save training and testing datasets to JSON files with proper serialization."""
        
#         # Save training data
#         train_file = "train_data.json"
#         with open(train_file, 'w', encoding='utf-8') as f:
#             json.dump(training_data, f, indent=2, ensure_ascii=False, default=json_serializer)
#         logger.info(f"Saved {len(training_data)} training examples to {train_file}")
        
#         # Save testing data
#         test_file = "test_data.json"
#         with open(test_file, 'w', encoding='utf-8') as f:
#             json.dump(testing_data, f, indent=2, ensure_ascii=False, default=json_serializer)
#         logger.info(f"Saved {len(testing_data)} testing examples to {test_file}")
        
#         # Create summary
#         summary = {
#             "created_at": datetime.now().isoformat(),
#             "year": self.year,
#             "past_days": self.past_days,
#             "training_data": {
#                 "file": train_file,
#                 "count": len(training_data),
#                 "date_range": f"{self.training_dates[0]} to {self.training_dates[-1]}" if training_data else "No data"
#             },
#             "testing_data": {
#                 "file": test_file,
#                 "count": len(testing_data),
#                 "dates": self.testing_dates
#             }
#         }
        
#         summary_file = "dataset_summary.json"
#         with open(summary_file, 'w', encoding='utf-8') as f:
#             json.dump(summary, f, indent=2, ensure_ascii=False, default=json_serializer)
#         logger.info(f"Saved dataset summary to {summary_file}")

#     def create_datasets(self):
#         """Main method to create both training and testing datasets."""
        
#         if not self.formatted_diagnoses:
#             logger.error("No formatted diagnoses loaded. Cannot create datasets.")
#             return False
        
#         logger.info("Starting dataset creation process...")
        
#         # Create training data
#         training_data = self.create_training_data()
        
#         # Create testing data  
#         testing_data = self.create_testing_data()
        
#         # Save datasets
#         self.save_datasets(training_data, testing_data)
        
#         # Print summary
#         print("\n" + "="*60)
#         print("DATASET CREATION SUMMARY")
#         print("="*60)
#         print(f"Year: {self.year}")
#         print(f"Past days: {self.past_days}")
#         print(f"Training examples: {len(training_data)}")
#         print(f"Testing examples: {len(testing_data)}")
#         print(f"Testing dates: {self.testing_dates}")
#         print(f"Files created:")
#         print(f"  - train_data.json ({len(training_data)} examples)")
#         print(f"  - test_data.json ({len(testing_data)} examples)")
#         print(f"  - dataset_summary.json (metadata)")
#         print("="*60)
        
#         return True

# def validate_datasets():
#     """Validate the created datasets."""
    
#     logger.info("Validating created datasets...")
    
#     # Check if files exist
#     files_to_check = ["train_data.json", "test_data.json", "dataset_summary.json"]
#     for file in files_to_check:
#         if not Path(file).exists():
#             logger.error(f"File not found: {file}")
#             return False
#         else:
#             logger.info(f"File exists: {file}")
    
#     # Validate training data structure
#     try:
#         with open("train_data.json", 'r', encoding='utf-8') as f:
#             train_data = json.load(f)
        
#         if train_data:
#             example = train_data[0]
#             required_fields = ["date", "past_days", "daily_raw_data", "target_diagnosis"]
#             for field in required_fields:
#                 if field not in example:
#                     logger.error(f"Missing field in training data: {field}")
#                     return False
#             logger.info(f"Training data validation passed ({len(train_data)} examples)")
        
#     except Exception as e:
#         logger.error(f"Error validating training data: {e}")
#         return False
    
#     # Validate testing data structure
#     try:
#         with open("test_data.json", 'r', encoding='utf-8') as f:
#             test_data = json.load(f)
        
#         if test_data:
#             example = test_data[0]
#             required_fields = ["date", "past_days", "system_prompt", "user_prompt"]
#             for field in required_fields:
#                 if field not in example:
#                     logger.error(f"Missing field in testing data: {field}")
#                     return False
#             logger.info(f"Testing data validation passed ({len(test_data)} examples)")
        
#     except Exception as e:
#         logger.error(f"Error validating testing data: {e}")
#         return False
    
#     logger.info("All datasets validated successfully!")
#     return True

# def inspect_training_example():
#     """Inspect a training example to show structure."""
#     try:
#         with open("train_data.json", 'r', encoding='utf-8') as f:
#             train_data = json.load(f)
        
#         if train_data:
#             print("\n" + "="*60)
#             print("TRAINING DATA EXAMPLE")
#             print("="*60)
#             example = train_data[0]
#             print(f"Date: {example['date']}")
#             print(f"Past days: {example['past_days']}")
#             print(f"Target diagnosis: {example['target_diagnosis'][:100]}...")
#             print(f"Daily raw data keys: {list(example['daily_raw_data'].keys())}")
#             print(f"Weather summary: {example['weather_data_summary']}")
#             print("="*60)
#     except Exception as e:
#         print(f"Error inspecting training data: {e}")

# def inspect_testing_example():
#     """Inspect a testing example to show structure."""
#     try:
#         with open("test_data.json", 'r', encoding='utf-8') as f:
#             test_data = json.load(f)
        
#         if test_data:
#             print("\n" + "="*60)
#             print("TESTING DATA EXAMPLE")
#             print("="*60)
#             example = test_data[0]
#             print(f"Date: {example['date']}")
#             print(f"Past days: {example['past_days']}")
#             print(f"System prompt length: {len(example['system_prompt'])} chars")
#             print(f"User prompt length: {len(example['user_prompt'])} chars")
#             print(f"Reference diagnosis: {example['reference_diagnosis'][:100]}...")
#             print(f"Weather summary: {example['weather_data_summary']}")
#             print("="*60)
#     except Exception as e:
#         print(f"Error inspecting testing data: {e}")

# def main():
#     """Main function to create datasets."""
    
#     print("Meteorological Dataset Creator")
#     print("="*50)
    
#     # Create datasets
#     creator = DatasetCreator(year=2024, past_days=4)
#     success = creator.create_datasets()
    
#     if success:
#         # Validate datasets
#         validation_success = validate_datasets()
        
#         if validation_success:
#             # Show examples
#             inspect_training_example()
#             inspect_testing_example()
            
#             print("\nDataset creation completed successfully!")
#             print("Files created:")
#             print("  - train_data.json (for fine-tuning)")
#             print("  - test_data.json (for evaluation)")
#             print("  - dataset_summary.json (metadata)")
#             print("\nYou can now use these files for fine-tuning your model.")
#         else:
#             print("\nDataset validation failed!")
#     else:
#         print("\nDataset creation failed!")

# if __name__ == "__main__":
#     main()





# ################################################################################
# ####################### create_zero_shot_test_dataset.py #######################
# ################################################################################





# #!/usr/bin/env python3
# """
# Script to create zero-shot test dataset (test_data_zero_shot.json) from formatted_diagnoses_2024.json
# This approach uses only day data without GPT API calls for creating user prompts.
# """

# import json
# import os
# from pathlib import Path
# from typing import Dict, List, Any
# import logging
# from datetime import datetime, date

# # Import existing functions
# from prompting.utils.check_data_availability import check_data_availability
# from prompting.utils.extract_data_from_tables import extract_comprehensive_weather_data
# from prompting.utils.create_prompts_gpt import extract_raw_csv_data_by_day
# from prompting.utils.config import get_testing_dates

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# def json_serializer(obj: Any) -> Any:
#     """Custom JSON serializer to handle date/datetime objects."""
#     if isinstance(obj, (datetime, date)):
#         return obj.isoformat()
#     raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# class ZeroShotDatasetCreator:
#     def __init__(self, year: int = 2024, past_days: int = 5):
#         self.year = year
#         self.past_days = past_days
        
#         # Load formatted diagnoses
#         self.formatted_diagnoses = self.load_formatted_diagnoses()
        
#         # Get testing dates only (6 specific dates)
#         self.testing_dates = get_testing_dates(year)
        
#         logger.info(f"Initialized ZeroShotDatasetCreator for {year}")
#         logger.info(f"Testing dates: {len(self.testing_dates)} - {self.testing_dates}")

#     def load_formatted_diagnoses(self) -> Dict:
#         """Load formatted diagnoses from JSON file."""
#         file_path = f"formatted_diagnoses_{self.year}/formatted_diagnoses_{self.year}.json"
        
#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 data = json.load(f)
#             logger.info(f"Loaded {len(data)} formatted diagnoses from {file_path}")
#             return data
#         except FileNotFoundError:
#             logger.error(f"Could not find file: {file_path}")
#             return {}
#         except Exception as e:
#             logger.error(f"Error loading formatted diagnoses: {str(e)}")
#             return {}

#     def weather_data_extractor(self, date: str, past_days: int):
#         """Extract weather data for a given date."""
#         try:
#             result = check_data_availability(date, past_days)
#             if not result.get('sufficient_data', False):
#                 logger.warning(f"Insufficient data for {date}")
#                 return None
            
#             all_table_data = extract_comprehensive_weather_data(date, past_days)
#             return all_table_data
            
#         except Exception as e:
#             logger.error(f"Error extracting weather data for {date}: {str(e)}")
#             return None

#     def create_zero_shot_system_prompt(self) -> str:
#         """Create a simple system prompt for zero-shot approach."""
#         return """Tu ești un meteorolog al Administrației Naționale de Meteorologie din România și trebuie să faci o diagnoză pe baza datelor pe care le primești de la stațiile meteo.

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

#     def create_zero_shot_user_prompt(self, daily_raw_data: Dict, current_date: str) -> str:
#         """Create a simple user prompt from day data for zero-shot approach."""
        
#         user_prompt = f"Analiza meteorologică pentru diagnoza din data de {current_date}:\n\n"
        
#         # Add current day data
#         current_day_data = None
#         for date_str, day_data in daily_raw_data.items():
#             if day_data.get('is_target_date', False):
#                 current_day_data = (date_str, day_data)
#                 break
        
#         if current_day_data:
#             date_str, day_data = current_day_data
#             user_prompt += f"ZIUA CURENTĂ {date_str} (pentru care se generează diagnoza):\n"
            
#             # Temperature data
#             if day_data['temperature_max_mean'] is not None:
#                 user_prompt += f"Temperatura medie maximă București: {day_data['temperature_max_mean']:.1f}°C\n"
            
#             if day_data['temperature_min_mean'] is not None:
#                 user_prompt += f"Temperatura medie minimă București: {day_data['temperature_min_mean']:.1f}°C\n"
            
#             # Precipitation data
#             if day_data['precipitation_mean'] is not None:
#                 user_prompt += f"Precipitații medii București: {day_data['precipitation_mean']:.1f} l/m²\n"
            
#             # Wind data
#             if day_data['hourly_summary'].get('wind'):
#                 wind = day_data['hourly_summary']['wind']
#                 user_prompt += f"Vânt: Media {wind['mean']:.1f} m/s (min: {wind['min']:.1f}, max: {wind['max']:.1f})\n"
            
#             # Nebulosity data
#             if day_data['hourly_summary'].get('nebulosity'):
#                 neb = day_data['hourly_summary']['nebulosity']
#                 user_prompt += f"Nebulozitate: Cel mai frecvent {neb['most_frequent']}/8 ({neb['count']} măsurători)\n"
            
#             # Phenomena data
#             if day_data['hourly_summary'].get('phenomena'):
#                 user_prompt += f"Fenomene:\n"
#                 for phenomenon, count in day_data['hourly_summary']['phenomena']:
#                     user_prompt += f"  - {phenomenon}: {count} observații\n"
        
#         # Add historical context from past days
#         user_prompt += f"\nDATELE ISTORICE DIN ZILELE PRECEDENTE:\n\n"
        
#         historical_days = {k: v for k, v in daily_raw_data.items() if not v.get('is_target_date', False)}
        
#         for date_str in sorted(historical_days.keys(), reverse=True):  # Most recent first
#             day_data = historical_days[date_str]
#             date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
            
#             user_prompt += f"Ziua {date_display}:\n"
            
#             if day_data['temperature_max_mean'] is not None:
#                 user_prompt += f"  - Tmax: {day_data['temperature_max_mean']:.1f}°C"
            
#             if day_data['temperature_min_mean'] is not None:
#                 user_prompt += f", Tmin: {day_data['temperature_min_mean']:.1f}°C"
            
#             if day_data['precipitation_mean'] is not None:
#                 user_prompt += f", Precipitații: {day_data['precipitation_mean']:.1f} l/m²"
            
#             user_prompt += "\n"
        
#         user_prompt += f"\nSARCINA: Pe baza datelor meteorologice prezentate mai sus, elaborează o diagnoză meteorologică profesională pentru ziua de {current_date} pentru București, respectând structura din instrucțiunile de sistem."
        
#         return user_prompt

#     def create_zero_shot_testing_data(self) -> List[Dict]:
#         """Create zero-shot testing dataset without GPT API calls."""
        
#         logger.info("Creating zero-shot testing dataset...")
#         testing_data = []
        
#         # Create system prompt once (same for all examples)
#         system_prompt = self.create_zero_shot_system_prompt()
        
#         for date in self.testing_dates:
#             try:
#                 logger.info(f"Processing testing date: {date}")
                
#                 # Extract weather data
#                 weather_data = self.weather_data_extractor(date, self.past_days)
#                 if not weather_data:
#                     logger.warning(f"No weather data for {date}")
#                     continue
                
#                 # Get day data composition
#                 daily_raw_data = extract_raw_csv_data_by_day(
#                     weather_data, date, self.past_days, include_target_date=True
#                 )
                
#                 # Create simple user prompt from day data (zero-shot approach)
#                 user_prompt = self.create_zero_shot_user_prompt(daily_raw_data, date)
                
#                 # Get reference diagnosis if available
#                 reference_diagnosis = ""
#                 if date in self.formatted_diagnoses:
#                     gt_data = self.formatted_diagnoses[date]
#                     if 'formatted_diagnosis' in gt_data and 'PRIMA_PROPOZITIE' in gt_data['formatted_diagnosis']:
#                         reference_diagnosis = gt_data['formatted_diagnosis']['PRIMA_PROPOZITIE']
#                     else:
#                         reference_diagnosis = gt_data.get('original_diagnosis', '')
                
#                 # Create zero-shot testing example
#                 testing_example = {
#                     "date": date,
#                     "past_days": self.past_days,
#                     "approach": "zero-shot",
#                     "system_prompt": system_prompt,
#                     "user_prompt": user_prompt,
#                     "daily_raw_data": daily_raw_data,
#                     "reference_diagnosis": reference_diagnosis,
#                     "weather_data_summary": {
#                         "wind_speed_ms": weather_data.get('wind_analysis', {}).get('mean_speed_ms'),
#                         "nebulosity_frequent": weather_data.get('nebulosity_analysis', {}).get('most_frequent_value'),
#                         "temperature_records": len(weather_data.get('daily_temperatures', [])),
#                         "precipitation_records": len(weather_data.get('daily_precipitation', []))
#                     }
#                 }
                
#                 testing_data.append(testing_example)
#                 logger.info(f"Successfully processed testing date: {date}")
                
#             except Exception as e:
#                 logger.error(f"Error processing testing date {date}: {str(e)}")
#                 continue
        
#         logger.info(f"Created {len(testing_data)} zero-shot testing examples")
#         return testing_data

#     def save_dataset(self, testing_data: List[Dict]):
#         """Save zero-shot testing dataset to JSON file."""
        
#         # Save zero-shot testing data
#         test_file = "test_data_zero_shot.json"
#         with open(test_file, 'w', encoding='utf-8') as f:
#             json.dump(testing_data, f, indent=2, ensure_ascii=False, default=json_serializer)
#         logger.info(f"Saved {len(testing_data)} zero-shot testing examples to {test_file}")
        
#         # Create summary
#         summary = {
#             "created_at": datetime.now().isoformat(),
#             "approach": "zero-shot",
#             "year": self.year,
#             "past_days": self.past_days,
#             "testing_data": {
#                 "file": test_file,
#                 "count": len(testing_data),
#                 "dates": self.testing_dates
#             },
#             "description": "Zero-shot testing dataset with simple day data prompts (no GPT API calls)"
#         }
        
#         summary_file = "zero_shot_dataset_summary.json"
#         with open(summary_file, 'w', encoding='utf-8') as f:
#             json.dump(summary, f, indent=2, ensure_ascii=False, default=json_serializer)
#         logger.info(f"Saved zero-shot dataset summary to {summary_file}")

#     def create_dataset(self):
#         """Main method to create zero-shot testing dataset."""
        
#         if not self.formatted_diagnoses:
#             logger.error("No formatted diagnoses loaded. Cannot create dataset.")
#             return False
        
#         logger.info("Starting zero-shot dataset creation process...")
        
#         # Create zero-shot testing data
#         testing_data = self.create_zero_shot_testing_data()
        
#         # Save dataset
#         self.save_dataset(testing_data)
        
#         # Print summary
#         print("\n" + "="*60)
#         print("ZERO-SHOT DATASET CREATION SUMMARY")
#         print("="*60)
#         print(f"Approach: Zero-shot (no GPT API calls)")
#         print(f"Year: {self.year}")
#         print(f"Past days: {self.past_days}")
#         print(f"Testing examples: {len(testing_data)}")
#         print(f"Testing dates: {self.testing_dates}")
#         print(f"Files created:")
#         print(f"  - test_data_zero_shot.json ({len(testing_data)} examples)")
#         print(f"  - zero_shot_dataset_summary.json (metadata)")
#         print("="*60)
        
#         return True

# def validate_zero_shot_dataset():
#     """Validate the created zero-shot dataset."""
    
#     logger.info("Validating zero-shot dataset...")
    
#     # Check if files exist
#     files_to_check = ["test_data_zero_shot.json", "zero_shot_dataset_summary.json"]
#     for file in files_to_check:
#         if not Path(file).exists():
#             logger.error(f"File not found: {file}")
#             return False
#         else:
#             logger.info(f"File exists: {file}")
    
#     # Validate testing data structure
#     try:
#         with open("test_data_zero_shot.json", 'r', encoding='utf-8') as f:
#             test_data = json.load(f)
        
#         if test_data:
#             example = test_data[0]
#             required_fields = ["date", "past_days", "approach", "system_prompt", "user_prompt"]
#             for field in required_fields:
#                 if field not in example:
#                     logger.error(f"Missing field in zero-shot testing data: {field}")
#                     return False
            
#             # Check approach field
#             if example.get("approach") != "zero-shot":
#                 logger.error(f"Invalid approach field: {example.get('approach')}")
#                 return False
            
#             logger.info(f"Zero-shot testing data validation passed ({len(test_data)} examples)")
        
#     except Exception as e:
#         logger.error(f"Error validating zero-shot testing data: {e}")
#         return False
    
#     logger.info("Zero-shot dataset validated successfully!")
#     return True

# def inspect_zero_shot_example():
#     """Inspect a zero-shot testing example to show structure."""
#     try:
#         with open("test_data_zero_shot.json", 'r', encoding='utf-8') as f:
#             test_data = json.load(f)
        
#         if test_data:
#             print("\n" + "="*60)
#             print("ZERO-SHOT TESTING DATA EXAMPLE")
#             print("="*60)
#             example = test_data[0]
#             print(f"Date: {example['date']}")
#             print(f"Approach: {example['approach']}")
#             print(f"Past days: {example['past_days']}")
#             print(f"System prompt length: {len(example['system_prompt'])} chars")
#             print(f"User prompt length: {len(example['user_prompt'])} chars")
#             print(f"Reference diagnosis: {example['reference_diagnosis'][:100]}...")
#             print(f"Weather summary: {example['weather_data_summary']}")
#             print("\nUser prompt preview:")
#             print(example['user_prompt'][:300] + "...")
#             print("="*60)
#     except Exception as e:
#         print(f"Error inspecting zero-shot testing data: {e}")

# def compare_approaches():
#     """Compare few-shot and zero-shot datasets if both exist."""
    
#     few_shot_file = "test_data.json"
#     zero_shot_file = "test_data_zero_shot.json"
    
#     if Path(few_shot_file).exists() and Path(zero_shot_file).exists():
#         try:
#             with open(few_shot_file, 'r', encoding='utf-8') as f:
#                 few_shot_data = json.load(f)
            
#             with open(zero_shot_file, 'r', encoding='utf-8') as f:
#                 zero_shot_data = json.load(f)
            
#             print("\n" + "="*60)
#             print("APPROACH COMPARISON")
#             print("="*60)
#             print(f"Few-shot CoT dataset: {len(few_shot_data)} examples")
#             print(f"Zero-shot dataset: {len(zero_shot_data)} examples")
            
#             if few_shot_data and zero_shot_data:
#                 fs_example = few_shot_data[0]
#                 zs_example = zero_shot_data[0]
                
#                 print(f"\nPrompt length comparison for {fs_example['date']}:")
#                 print(f"  Few-shot user prompt: {len(fs_example['user_prompt'])} chars")
#                 print(f"  Zero-shot user prompt: {len(zs_example['user_prompt'])} chars")
                
#                 print(f"\nSystem prompt comparison:")
#                 print(f"  Few-shot system prompt: {len(fs_example['system_prompt'])} chars")
#                 print(f"  Zero-shot system prompt: {len(zs_example['system_prompt'])} chars")
            
#             print("="*60)
#         except Exception as e:
#             print(f"Error comparing approaches: {e}")

# def main():
#     """Main function to create zero-shot dataset."""
    
#     print("Zero-Shot Meteorological Dataset Creator")
#     print("="*50)
    
#     # Create zero-shot dataset
#     creator = ZeroShotDatasetCreator(year=2024, past_days=5)
#     success = creator.create_dataset()
    
#     if success:
#         # Validate dataset
#         validation_success = validate_zero_shot_dataset()
        
#         if validation_success:
#             # Show example
#             inspect_zero_shot_example()
            
#             # Compare with few-shot if available
#             compare_approaches()
            
#             print("\nZero-shot dataset creation completed successfully!")
#             print("Files created:")
#             print("  - test_data_zero_shot.json (for zero-shot evaluation)")
#             print("  - zero_shot_dataset_summary.json (metadata)")
#             print("\nYou can now compare few-shot vs zero-shot performance.")
#         else:
#             print("\nZero-shot dataset validation failed!")
#     else:
#         print("\nZero-shot dataset creation failed!")

# if __name__ == "__main__":
#     main()






#!/usr/bin/env python3
"""
Dataset creation for the meteorological diagnosis fine-tuning pipeline.

Combines the three previously-separate dataset-prep scripts into one
module with three modes:

    python dataset_creation.py --mode training        -> train_data.json
    python dataset_creation.py --mode few_shot_test   -> test_data.json
    python dataset_creation.py --mode zero_shot_test  -> test_data_zero_shot.json
    python dataset_creation.py --mode all             -> all three in sequence

KEY DESIGN POINTS for downstream readers:

1. Training and few-shot test prompts are now produced by the SAME prompt
   builder (create_meteorological_prompts from prompt_construction.py).
   The previous scripts used different hand-rolled builders for each,
   producing a training-vs-test format mismatch. Under the previous
   setup, the fine-tuned model was trained on one prompt format and
   evaluated against a completely different one; the ROUGE-L 82%
   improvement cited in the report reflects the model learning to
   produce the output format, not learning from the historical context.
   This pass aligns both prompt formats, which will produce measurably
   different fine-tuning results - retraining is needed for valid numbers.

   Building matched training prompts requires gpt-5-mini calls for the
   in-context CoT exemplars, costing roughly $5-15 for a typical 300-date
   training set. OPENAI_API_KEY must be set.

2. train_data.json is now written ONLY by --mode training. The previous
   create_train_test_datasets.py silently overwrote train_data.json with
   a different schema (non-messages format) when run after
   generate_training_data.py. The cleaned script assigns exactly one
   writer per output file: training -> train_data.json, few_shot_test
   -> test_data.json, zero_shot_test -> test_data_zero_shot.json.

3. past_days is a single CLI parameter that applies consistently across
   all three datasets. Previously each script had its own default
   (training: 5, few-shot test: 4, zero-shot test: 5) which produced
   datasets with mismatched historical-context windows.

4. Validation is shared. All three modes validate output via the same
   _validate_json_file helper with per-schema required fields. Errors
   are accumulated across the full file (not just item 0) so malformed
   examples surface before fine-tuning starts.

5. Zero dead weight in test JSONs. The previous scripts embedded full
   daily_raw_data and weather_data_summary fields in every test example,
   bloating files 10x beyond what the consumer needs. The cleaned schema
   includes only the fields that finetuning_pipeline._load_testing_data_from_file
   actually reads.
"""

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from prompting.utils.check_data_availability import check_data_availability
from prompting.utils.input_extraction import extract_comprehensive_weather_data
from prompting.utils.prompt_construction import (
    create_meteorological_prompts,
    extract_raw_csv_data_by_day,
)
from prompting.utils.config import get_testing_dates, get_training_date_ranges


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_YEAR = 2024
_DEFAULT_PAST_DAYS = 4

_TRAIN_DATA_FILENAME = "train_data.json"
_FEW_SHOT_TEST_FILENAME = "test_data.json"
_ZERO_SHOT_TEST_FILENAME = "test_data_zero_shot.json"

_TRAIN_SUMMARY_FILENAME = "training_data_summary.json"
_FEW_SHOT_SUMMARY_FILENAME = "dataset_summary.json"
_ZERO_SHOT_SUMMARY_FILENAME = "zero_shot_dataset_summary.json"

_VALID_MODES = ("training", "few_shot_test", "zero_shot_test", "all")

_DIAGNOSIS_KEY_PRIMA = "PRIMA_PROPOZITIE"
_DIAGNOSIS_KEY_ORIGINAL = "original_diagnosis"

# Progress reporting cadence during bulk generation
_PROGRESS_REPORT_INTERVAL = 50


# ---------------------------------------------------------------------------
# Zero-shot system prompt
# ---------------------------------------------------------------------------

# Embedded verbatim from create_zero_shot_test_dataset.py. This is the
# simpler prompt used for zero-shot testing (no in-context CoT exemplars).
_ZERO_SHOT_SYSTEM_PROMPT = """Tu ești un meteorolog al Administrației Naționale de Meteorologie din România și trebuie să faci o diagnoză pe baza datelor pe care le primești de la stațiile meteo.

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
- Păstrează tonul profesional specific unui meteorolog ANM"""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _json_serializer(obj: Any) -> Any:
    """Serialize datetime/date to ISO format; raise for anything else unexpected."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def _load_formatted_diagnoses(year: int) -> Dict:
    """
    Load formatted diagnoses from formatted_diagnoses_{year}/formatted_diagnoses_{year}.json.

    Returns an empty dict on failure; the caller is responsible for checking
    and exiting cleanly.
    """
    file_path = Path(f"formatted_diagnoses_{year}") / f"formatted_diagnoses_{year}.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded {len(data)} formatted diagnoses from {file_path}")
        return data
    except FileNotFoundError:
        print(f"ERROR: formatted diagnoses file not found: {file_path}")
        return {}
    except Exception as e:
        print(f"ERROR loading formatted diagnoses from {file_path}: {e}")
        return {}


def _extract_weather_data(target_date: str, past_days: int) -> Optional[Dict]:
    """
    Extract comprehensive weather data for one target date. Returns None if
    data availability check fails or extraction errors out.
    """
    try:
        availability = check_data_availability(target_date, past_days)
        if not availability.get("sufficient_data", False):
            print(f"WARNING: insufficient data for {target_date} (past_days={past_days})")
            return None
        return extract_comprehensive_weather_data(target_date, past_days)
    except Exception as e:
        print(f"ERROR extracting weather data for {target_date}: {e}")
        return None


def _get_reference_diagnosis(gt_data: Dict) -> str:
    """
    Pull the reference diagnosis from a formatted_diagnoses entry. Prefers
    the PRIMA_PROPOZITIE field from the formatted breakdown; falls back to
    original_diagnosis if the formatted breakdown is missing.
    """
    formatted = gt_data.get("formatted_diagnosis", {})
    if _DIAGNOSIS_KEY_PRIMA in formatted:
        return formatted[_DIAGNOSIS_KEY_PRIMA]
    return gt_data.get(_DIAGNOSIS_KEY_ORIGINAL, "")


def _save_json(
    data: List[Dict],
    filename: str,
    summary_filename: str,
    summary_extra: Dict,
) -> None:
    """Write data and a companion summary JSON. Counts items and prints the path."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=_json_serializer)
    print(f"Saved {len(data)} examples to {filename}")

    summary = {
        "created_at": datetime.now().isoformat(),
        "count": len(data),
        "file": filename,
        **summary_extra,
    }
    with open(summary_filename, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=_json_serializer)


def _resolve_api_key(provided: Optional[str]) -> str:
    """
    Return an OpenAI API key. Prefers explicit argument, then OPENAI_API_KEY
    env var. Raises with a clear message if neither is set. Used by the
    training and few-shot test modes which both call gpt-5-mini via
    create_meteorological_prompts.
    """
    if provided:
        return provided
    env = os.environ.get("OPENAI_API_KEY")
    if env:
        return env
    raise RuntimeError(
        "OpenAI API key not provided. Pass --api_key explicitly or set the "
        "OPENAI_API_KEY environment variable. Required for training and "
        "few-shot test modes (which call gpt-5-mini for in-context CoT "
        "exemplars); zero-shot test mode does not need it."
    )


# ---------------------------------------------------------------------------
# Zero-shot user prompt builder
# ---------------------------------------------------------------------------

def _build_zero_shot_user_prompt(daily_raw_data: Dict, current_date: str) -> str:
    """
    Hand-crafted user prompt for zero-shot testing. Includes the target
    day's aggregated weather readings plus historical-day temperatures
    and precipitation, without any in-context CoT exemplars.
    """
    parts: List[str] = [f"Analiza meteorologică pentru diagnoza din data de {current_date}:\n"]

    # Current day
    current_day_data = None
    for date_str, day_data in daily_raw_data.items():
        if day_data.get("is_target_date", False):
            current_day_data = (date_str, day_data)
            break

    if current_day_data:
        date_str, day_data = current_day_data
        parts.append(f"ZIUA CURENTĂ {date_str} (pentru care se generează diagnoza):")

        if day_data.get("temperature_max_mean") is not None:
            parts.append(f"Temperatura medie maximă București: {day_data['temperature_max_mean']:.1f}°C")
        if day_data.get("temperature_min_mean") is not None:
            parts.append(f"Temperatura medie minimă București: {day_data['temperature_min_mean']:.1f}°C")
        if day_data.get("precipitation_mean") is not None:
            parts.append(f"Precipitații medii București: {day_data['precipitation_mean']:.1f} l/m²")

        hourly = day_data.get("hourly_summary", {})
        if hourly.get("wind"):
            wind = hourly["wind"]
            parts.append(
                f"Vânt: Media {wind['mean']:.1f} m/s "
                f"(min: {wind['min']:.1f}, max: {wind['max']:.1f})"
            )
        if hourly.get("nebulosity"):
            neb = hourly["nebulosity"]
            parts.append(f"Nebulozitate: Cel mai frecvent {neb['most_frequent']}/8 ({neb['count']} măsurători)")
        if hourly.get("phenomena"):
            parts.append("Fenomene:")
            for phenomenon, count in hourly["phenomena"]:
                parts.append(f"  - {phenomenon}: {count} observații")

    # Historical days (all available; sorted most-recent-first for readability)
    historical_days = {
        k: v for k, v in daily_raw_data.items() if not v.get("is_target_date", False)
    }
    if historical_days:
        parts.append("\nDATELE ISTORICE DIN ZILELE PRECEDENTE:\n")
        for date_str in sorted(historical_days.keys(), reverse=True):
            day_data = historical_days[date_str]
            date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
            line_parts = [f"Ziua {date_display}:"]
            if day_data.get("temperature_max_mean") is not None:
                line_parts.append(f"  - Tmax: {day_data['temperature_max_mean']:.1f}°C")
            if day_data.get("temperature_min_mean") is not None:
                line_parts[-1] += f", Tmin: {day_data['temperature_min_mean']:.1f}°C"
            if day_data.get("precipitation_mean") is not None:
                line_parts[-1] += f", Precipitații: {day_data['precipitation_mean']:.1f} l/m²"
            parts.extend(line_parts)

    parts.append(
        f"\nSARCINA: Pe baza datelor meteorologice prezentate mai sus, "
        f"elaborează o diagnoză meteorologică profesională pentru ziua de "
        f"{current_date} pentru București, respectând structura din "
        f"instrucțiunile de sistem."
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Mode: training
# ---------------------------------------------------------------------------

def _generate_training_data(
    year: int,
    past_days: int,
    api_key: str,
    formatted_diagnoses: Dict,
) -> List[Dict]:
    """
    Produce training data in messages format. Uses create_meteorological_prompts
    for the (system, user) prompt pair so training prompts are structurally
    identical to few-shot test prompts (prior to the cleanup, they used
    different hand-rolled builders and the formats diverged).
    """
    training_dates = get_training_date_ranges(year)
    print(f"Generating training data for {len(training_dates)} training dates")

    training_data: List[Dict] = []
    for i, target_date in enumerate(training_dates, start=1):
        if target_date not in formatted_diagnoses:
            print(f"WARNING: no formatted diagnosis for {target_date}; skipping")
            continue

        weather_data = _extract_weather_data(target_date, past_days)
        if weather_data is None:
            continue

        target_diagnosis = _get_reference_diagnosis(formatted_diagnoses[target_date])
        if not target_diagnosis:
            print(f"WARNING: no target diagnosis for {target_date}; skipping")
            continue

        # Use the SAME prompt builder as the few-shot test mode. This is the
        # matched-format fix; the previous pipeline had training and test
        # prompts in different formats, which corrupted the fine-tuning
        # signal.
        try:
            system_prompt, user_prompt = create_meteorological_prompts(
                current_date=target_date,
                weather_data=weather_data,
                past_days=past_days,
                openai_api_key=api_key,
            )
        except Exception as e:
            print(f"ERROR building prompts for {target_date}: {e}")
            continue

        training_data.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": target_diagnosis},
            ],
            "date": target_date,
        })

        if i % _PROGRESS_REPORT_INTERVAL == 0:
            print(f"Processed {i}/{len(training_dates)} training dates ({len(training_data)} valid so far)")

    print(f"Generated {len(training_data)} training examples")
    return training_data


def _run_training_mode(
    year: int,
    past_days: int,
    api_key: str,
    formatted_diagnoses: Dict,
) -> bool:
    """Run training dataset generation end-to-end. Returns True on success."""
    training_data = _generate_training_data(
        year=year,
        past_days=past_days,
        api_key=api_key,
        formatted_diagnoses=formatted_diagnoses,
    )
    if not training_data:
        print("ERROR: no training examples generated")
        return False

    dates = [item["date"] for item in training_data]
    summary_extra = {
        "mode": "training",
        "format": "messages",
        "year": year,
        "past_days": past_days,
        "date_range": f"{min(dates)} to {max(dates)}",
    }
    _save_json(training_data, _TRAIN_DATA_FILENAME, _TRAIN_SUMMARY_FILENAME, summary_extra)

    ok = _validate_json_file(
        _TRAIN_DATA_FILENAME,
        required_fields=["messages", "date"],
        schema_name="training (messages format)",
    )
    if ok:
        _inspect_example(_TRAIN_DATA_FILENAME, ["date", "messages"])
    return ok


# ---------------------------------------------------------------------------
# Mode: few_shot_test
# ---------------------------------------------------------------------------

def _generate_few_shot_test_data(
    year: int,
    past_days: int,
    api_key: str,
    formatted_diagnoses: Dict,
) -> List[Dict]:
    """
    Produce few-shot test data using create_meteorological_prompts
    (same builder used in training mode, matching prompt formats).

    Schema is intentionally minimal: {date, past_days, system_prompt,
    user_prompt, reference_diagnosis}. The previous scripts embedded
    daily_raw_data and weather_data_summary as additional fields, which
    the consumer (finetuning_pipeline) never reads.
    """
    testing_dates = get_testing_dates(year)
    print(f"Generating few-shot test data for {len(testing_dates)} testing dates")

    testing_data: List[Dict] = []
    for target_date in testing_dates:
        print(f"Processing {target_date}")
        weather_data = _extract_weather_data(target_date, past_days)
        if weather_data is None:
            continue

        try:
            system_prompt, user_prompt = create_meteorological_prompts(
                current_date=target_date,
                weather_data=weather_data,
                past_days=past_days,
                openai_api_key=api_key,
            )
        except Exception as e:
            print(f"ERROR building prompts for {target_date}: {e}")
            continue

        reference_diagnosis = ""
        if target_date in formatted_diagnoses:
            reference_diagnosis = _get_reference_diagnosis(formatted_diagnoses[target_date])

        testing_data.append({
            "date": target_date,
            "past_days": past_days,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "reference_diagnosis": reference_diagnosis,
        })

    print(f"Generated {len(testing_data)} few-shot test examples")
    return testing_data


def _run_few_shot_test_mode(
    year: int,
    past_days: int,
    api_key: str,
    formatted_diagnoses: Dict,
) -> bool:
    """Run few-shot test dataset generation end-to-end."""
    testing_data = _generate_few_shot_test_data(
        year=year,
        past_days=past_days,
        api_key=api_key,
        formatted_diagnoses=formatted_diagnoses,
    )
    if not testing_data:
        print("ERROR: no few-shot test examples generated")
        return False

    summary_extra = {
        "mode": "few_shot_test",
        "year": year,
        "past_days": past_days,
        "dates": sorted(item["date"] for item in testing_data),
    }
    _save_json(testing_data, _FEW_SHOT_TEST_FILENAME, _FEW_SHOT_SUMMARY_FILENAME, summary_extra)

    ok = _validate_json_file(
        _FEW_SHOT_TEST_FILENAME,
        required_fields=["date", "past_days", "system_prompt", "user_prompt", "reference_diagnosis"],
        schema_name="few-shot test",
    )
    if ok:
        _inspect_example(
            _FEW_SHOT_TEST_FILENAME,
            ["date", "past_days", "system_prompt", "user_prompt", "reference_diagnosis"],
        )
    return ok


# ---------------------------------------------------------------------------
# Mode: zero_shot_test
# ---------------------------------------------------------------------------

def _generate_zero_shot_test_data(
    year: int,
    past_days: int,
    formatted_diagnoses: Dict,
) -> List[Dict]:
    """
    Produce zero-shot test data. Does NOT call gpt-5-mini; uses a simple
    hand-crafted prompt with only weather data and historical context.
    """
    testing_dates = get_testing_dates(year)
    print(f"Generating zero-shot test data for {len(testing_dates)} testing dates")

    testing_data: List[Dict] = []
    for target_date in testing_dates:
        print(f"Processing {target_date}")
        weather_data = _extract_weather_data(target_date, past_days)
        if weather_data is None:
            continue

        daily_raw_data = extract_raw_csv_data_by_day(
            weather_data, target_date, past_days, include_target_date=True,
        )
        user_prompt = _build_zero_shot_user_prompt(daily_raw_data, target_date)

        reference_diagnosis = ""
        if target_date in formatted_diagnoses:
            reference_diagnosis = _get_reference_diagnosis(formatted_diagnoses[target_date])

        testing_data.append({
            "date": target_date,
            "past_days": past_days,
            "approach": "zero-shot",
            "system_prompt": _ZERO_SHOT_SYSTEM_PROMPT,
            "user_prompt": user_prompt,
            "reference_diagnosis": reference_diagnosis,
        })

    print(f"Generated {len(testing_data)} zero-shot test examples")
    return testing_data


def _run_zero_shot_test_mode(
    year: int,
    past_days: int,
    formatted_diagnoses: Dict,
) -> bool:
    """Run zero-shot test dataset generation end-to-end."""
    testing_data = _generate_zero_shot_test_data(
        year=year, past_days=past_days, formatted_diagnoses=formatted_diagnoses,
    )
    if not testing_data:
        print("ERROR: no zero-shot test examples generated")
        return False

    summary_extra = {
        "mode": "zero_shot_test",
        "approach": "zero-shot",
        "year": year,
        "past_days": past_days,
        "dates": sorted(item["date"] for item in testing_data),
    }
    _save_json(
        testing_data, _ZERO_SHOT_TEST_FILENAME, _ZERO_SHOT_SUMMARY_FILENAME, summary_extra,
    )

    ok = _validate_json_file(
        _ZERO_SHOT_TEST_FILENAME,
        required_fields=["date", "past_days", "approach", "system_prompt", "user_prompt"],
        schema_name="zero-shot test",
    )
    if ok:
        _inspect_example(
            _ZERO_SHOT_TEST_FILENAME,
            ["date", "past_days", "approach", "system_prompt", "user_prompt"],
        )
        _compare_approach_files()
    return ok


def _compare_approach_files() -> None:
    """
    If both few-shot and zero-shot test files exist, print a side-by-side
    prompt-length comparison. Runs after zero-shot generation as a
    convenience - the diagnostic from the original script, consolidated.
    """
    few_shot = Path(_FEW_SHOT_TEST_FILENAME)
    zero_shot = Path(_ZERO_SHOT_TEST_FILENAME)
    if not (few_shot.exists() and zero_shot.exists()):
        return

    try:
        with open(few_shot, "r", encoding="utf-8") as f:
            fs_data = json.load(f)
        with open(zero_shot, "r", encoding="utf-8") as f:
            zs_data = json.load(f)
    except Exception as e:
        print(f"WARNING: could not compare approach files: {e}")
        return

    if not fs_data or not zs_data:
        return

    fs, zs = fs_data[0], zs_data[0]
    print(f"Approach comparison for {fs['date']}:")
    print(f"  Few-shot user prompt:  {len(fs['user_prompt'])} chars")
    print(f"  Zero-shot user prompt: {len(zs['user_prompt'])} chars")
    print(f"  Few-shot system prompt:  {len(fs['system_prompt'])} chars")
    print(f"  Zero-shot system prompt: {len(zs['system_prompt'])} chars")


# ---------------------------------------------------------------------------
# Validation and inspection helpers
# ---------------------------------------------------------------------------

def _validate_json_file(
    path: str,
    required_fields: List[str],
    schema_name: str,
) -> bool:
    """
    Validate that a JSON file exists, parses, and every item has the
    required fields. Accumulates errors across the full file; prints up
    to 10 specific errors before reporting a count.
    """
    if not Path(path).exists():
        print(f"ERROR: {path} not found")
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR parsing {path}: {e}")
        return False

    if not data:
        print(f"ERROR: {path} is empty")
        return False

    errors: List[str] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"item {i}: not a dict")
            continue
        for field in required_fields:
            if field not in item:
                errors.append(f"item {i}: missing '{field}'")

    if errors:
        print(f"ERROR: {path} has {len(errors)} validation errors")
        for err in errors[:10]:
            print(f"  {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        return False

    print(f"{schema_name} validation passed ({len(data)} examples)")
    return True


def _inspect_example(path: str, preview_keys: List[str]) -> None:
    """
    Print a short preview of the first example in a dataset file. Caps
    long fields at 200 characters. Dev-tool diagnostic; skip if you don't
    want the extra output.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"WARNING: could not inspect {path}: {e}")
        return
    if not data:
        return

    example = data[0]
    print(f"First example from {path}:")
    for key in preview_keys:
        if key not in example:
            continue
        value = example[key]
        if isinstance(value, str):
            if len(value) > 200:
                print(f"  {key}: {value[:200]}... ({len(value)} chars total)")
            else:
                print(f"  {key}: {value}")
        elif isinstance(value, list):
            print(f"  {key}: list of {len(value)} items")
        else:
            print(f"  {key}: {value}")


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments. Mode is required."""
    parser = argparse.ArgumentParser(
        description="Create training and test datasets for the meteorological "
                    "diagnosis fine-tuning pipeline."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=_VALID_MODES,
        help="Which dataset to generate. 'all' runs training, few_shot_test, "
             "and zero_shot_test in sequence with the same year and past_days.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=_DEFAULT_YEAR,
        help=f"Year to generate data for. Default {_DEFAULT_YEAR}.",
    )
    parser.add_argument(
        "--past_days",
        type=int,
        default=_DEFAULT_PAST_DAYS,
        help=f"Number of past days of historical context. Default "
             f"{_DEFAULT_PAST_DAYS}. Must match the past_days value used "
             f"when calling finetuning_pipeline.",
    )
    parser.add_argument(
        "--api_key",
        type=str,
        default=None,
        help="OpenAI API key. Falls back to OPENAI_API_KEY env var. "
             "Required for training and few_shot_test modes; not needed "
             "for zero_shot_test.",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point. Returns 0 on success, 1 on any mode failing."""
    args = _parse_args()

    print(f"Dataset creation: mode={args.mode}, year={args.year}, past_days={args.past_days}")

    formatted_diagnoses = _load_formatted_diagnoses(args.year)
    if not formatted_diagnoses:
        print("ERROR: cannot proceed without formatted diagnoses")
        return 1

    # Resolve API key eagerly for modes that need it, so users see a clear
    # error before any work starts rather than mid-generation.
    needs_api = args.mode in ("training", "few_shot_test", "all")
    api_key: Optional[str] = None
    if needs_api:
        try:
            api_key = _resolve_api_key(args.api_key)
        except RuntimeError as e:
            print(f"ERROR: {e}")
            return 1

    all_ok = True

    if args.mode in ("training", "all"):
        print("=== Mode: training ===")
        ok = _run_training_mode(
            year=args.year, past_days=args.past_days,
            api_key=api_key, formatted_diagnoses=formatted_diagnoses,
        )
        all_ok = all_ok and ok

    if args.mode in ("few_shot_test", "all"):
        print("=== Mode: few_shot_test ===")
        ok = _run_few_shot_test_mode(
            year=args.year, past_days=args.past_days,
            api_key=api_key, formatted_diagnoses=formatted_diagnoses,
        )
        all_ok = all_ok and ok

    if args.mode in ("zero_shot_test", "all"):
        print("=== Mode: zero_shot_test ===")
        ok = _run_zero_shot_test_mode(
            year=args.year, past_days=args.past_days,
            formatted_diagnoses=formatted_diagnoses,
        )
        all_ok = all_ok and ok

    if all_ok:
        print("Dataset creation complete")
        return 0
    print("Dataset creation finished with errors")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Diagnostic script to identify missing dates in training dataset and find the root cause.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Set
import logging
from datetime import datetime, timedelta

# Import existing functions
from prompting.utils.check_data_availability import check_data_availability
from prompting.utils.extract_data_from_tables import extract_comprehensive_weather_data
from prompting.utils.config import get_training_date_ranges

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DateDiagnostic:
    def __init__(self, year: int = 2024, past_days: int = 5):
        self.year = year
        self.past_days = past_days
        
        # Load formatted diagnoses
        self.formatted_diagnoses = self.load_formatted_diagnoses()
        
        # Get expected training dates
        self.expected_training_dates = get_training_date_ranges(year)
        
        print(f"Diagnostic for year {year} with {past_days} past days")
        print(f"Expected training dates: {len(self.expected_training_dates)}")

    def load_formatted_diagnoses(self) -> Dict:
        """Load formatted diagnoses from JSON file."""
        file_path = f"formatted_diagnoses_{self.year}/formatted_diagnoses_{self.year}.json"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"Loaded {len(data)} formatted diagnoses from {file_path}")
            return data
        except FileNotFoundError:
            print(f"Could not find file: {file_path}")
            return {}
        except Exception as e:
            print(f"Error loading formatted diagnoses: {str(e)}")
            return {}

    def check_expected_vs_actual_dates(self):
        """Check which dates should exist vs which actually exist."""
        
        # Generate expected dates manually (1-25 of each month)
        manual_expected_dates = []
        for month in range(1, 13):  # January to December
            for day in range(1, 26):  # 1st to 25th
                try:
                    date = datetime(self.year, month, day).strftime("%Y-%m-%d")
                    manual_expected_dates.append(date)
                except ValueError:
                    # Handle invalid dates (like Feb 30)
                    continue
        
        # Compare with config function
        config_dates = set(self.expected_training_dates)
        manual_dates = set(manual_expected_dates)
        
        print(f"\n{'='*60}")
        print("DATE GENERATION COMPARISON")
        print(f"{'='*60}")
        print(f"Manual generation (1-25 each month): {len(manual_dates)} dates")
        print(f"Config function generation: {len(config_dates)} dates")
        
        if manual_dates != config_dates:
            print(f"❌ MISMATCH detected!")
            missing_in_config = manual_dates - config_dates
            extra_in_config = config_dates - manual_dates
            
            if missing_in_config:
                print(f"Missing in config function: {len(missing_in_config)} dates")
                for date in sorted(missing_in_config)[:10]:  # Show first 10
                    print(f"  - {date}")
                if len(missing_in_config) > 10:
                    print(f"  ... and {len(missing_in_config) - 10} more")
            
            if extra_in_config:
                print(f"Extra in config function: {len(extra_in_config)} dates")
                for date in sorted(extra_in_config)[:10]:  # Show first 10
                    print(f"  - {date}")
        else:
            print(f"✅ Date generation matches!")
        
        return manual_expected_dates

    def check_formatted_diagnoses_coverage(self, expected_dates: List[str]):
        """Check which expected dates have formatted diagnoses."""
        
        expected_set = set(expected_dates)
        diagnosis_set = set(self.formatted_diagnoses.keys())
        
        print(f"\n{'='*60}")
        print("FORMATTED DIAGNOSES COVERAGE")
        print(f"{'='*60}")
        print(f"Expected training dates: {len(expected_set)}")
        print(f"Available formatted diagnoses: {len(diagnosis_set)}")
        
        missing_diagnoses = expected_set - diagnosis_set
        extra_diagnoses = diagnosis_set - expected_set
        
        if missing_diagnoses:
            print(f"❌ Missing {len(missing_diagnoses)} formatted diagnoses:")
            
            # Group by month for better readability
            missing_by_month = {}
            for date in missing_diagnoses:
                month = date[:7]  # YYYY-MM
                if month not in missing_by_month:
                    missing_by_month[month] = []
                missing_by_month[month].append(date)
            
            for month in sorted(missing_by_month.keys()):
                dates = sorted(missing_by_month[month])
                print(f"  {month}: {len(dates)} missing - {dates}")
        else:
            print(f"✅ All expected dates have formatted diagnoses!")
        
        if extra_diagnoses:
            print(f"ℹ️ Extra {len(extra_diagnoses)} diagnoses (not in training range)")
        
        return expected_set - missing_diagnoses

    def check_weather_data_availability(self, available_dates: Set[str]):
        """Check which dates have sufficient weather data."""
        
        print(f"\n{'='*60}")
        print("WEATHER DATA AVAILABILITY CHECK")
        print(f"{'='*60}")
        print(f"Checking {len(available_dates)} dates for weather data...")
        
        sufficient_data_dates = set()
        insufficient_data_dates = set()
        error_dates = set()
        
        for i, date in enumerate(sorted(available_dates)):
            try:
                result = check_data_availability(date, self.past_days)
                if result.get('sufficient_data', False):
                    sufficient_data_dates.add(date)
                else:
                    insufficient_data_dates.add(date)
                
                if (i + 1) % 50 == 0:
                    print(f"  Checked {i + 1}/{len(available_dates)} dates...")
                    
            except Exception as e:
                error_dates.add(date)
                print(f"  Error checking {date}: {str(e)}")
        
        print(f"\nResults:")
        print(f"✅ Sufficient data: {len(sufficient_data_dates)} dates")
        print(f"❌ Insufficient data: {len(insufficient_data_dates)} dates")
        print(f"⚠️ Errors: {len(error_dates)} dates")
        
        if insufficient_data_dates:
            print(f"\nDates with insufficient data:")
            # Group by month
            insufficient_by_month = {}
            for date in insufficient_data_dates:
                month = date[:7]
                if month not in insufficient_by_month:
                    insufficient_by_month[month] = []
                insufficient_by_month[month].append(date)
            
            for month in sorted(insufficient_by_month.keys()):
                dates = sorted(insufficient_by_month[month])
                print(f"  {month}: {len(dates)} dates - {dates}")
        
        if error_dates:
            print(f"\nDates with errors:")
            for date in sorted(error_dates):
                print(f"  - {date}")
        
        return sufficient_data_dates

    def check_weather_extraction(self, sufficient_dates: Set[str]):
        """Check which dates successfully extract weather data."""
        
        print(f"\n{'='*60}")
        print("WEATHER DATA EXTRACTION CHECK")
        print(f"{'='*60}")
        print(f"Checking {len(sufficient_dates)} dates for weather extraction...")
        
        successful_extraction = set()
        failed_extraction = set()
        
        # Check a sample of dates to avoid taking too long
        sample_dates = sorted(sufficient_dates)[:50]  # Check first 50
        
        for i, date in enumerate(sample_dates):
            try:
                weather_data = extract_comprehensive_weather_data(date, self.past_days)
                if weather_data:
                    successful_extraction.add(date)
                else:
                    failed_extraction.add(date)
                    
                if (i + 1) % 10 == 0:
                    print(f"  Extracted {i + 1}/{len(sample_dates)} dates...")
                    
            except Exception as e:
                failed_extraction.add(date)
                print(f"  Error extracting {date}: {str(e)}")
        
        print(f"\nSample results ({len(sample_dates)} dates checked):")
        print(f"✅ Successful extraction: {len(successful_extraction)} dates")
        print(f"❌ Failed extraction: {len(failed_extraction)} dates")
        
        if failed_extraction:
            print(f"\nFailed extractions:")
            for date in sorted(failed_extraction):
                print(f"  - {date}")
        
        return successful_extraction

    def load_existing_training_data(self):
        """Load existing train_data.json to see what's actually there."""
        
        if not Path("train_data.json").exists():
            print(f"\n❌ train_data.json does not exist yet")
            return set()
        
        try:
            with open("train_data.json", 'r', encoding='utf-8') as f:
                train_data = json.load(f)
            
            existing_dates = set()
            for item in train_data:
                if 'date' in item:
                    existing_dates.add(item['date'])
            
            print(f"\n{'='*60}")
            print("EXISTING TRAINING DATA")
            print(f"{'='*60}")
            print(f"Found {len(existing_dates)} dates in train_data.json")
            
            return existing_dates
            
        except Exception as e:
            print(f"\n❌ Error loading train_data.json: {str(e)}")
            return set()

    def run_complete_diagnostic(self):
        """Run complete diagnostic to find missing dates."""
        
        print(f"{'='*80}")
        print("COMPLETE DIAGNOSTIC FOR MISSING TRAINING DATES")
        print(f"{'='*80}")
        
        # Step 1: Check date generation
        expected_dates = self.check_expected_vs_actual_dates()
        
        # Step 2: Check formatted diagnoses coverage
        dates_with_diagnoses = self.check_formatted_diagnoses_coverage(expected_dates)
        
        # Step 3: Check weather data availability
        dates_with_weather = self.check_weather_data_availability(dates_with_diagnoses)
        
        # Step 4: Check weather extraction (sample)
        extractable_dates = self.check_weather_extraction(dates_with_weather)
        
        # Step 5: Check existing training data
        existing_dates = self.load_existing_training_data()
        
        # Final summary
        print(f"\n{'='*80}")
        print("DIAGNOSTIC SUMMARY")
        print(f"{'='*80}")
        print(f"Expected training dates (1-25 each month): {len(expected_dates)}")
        print(f"Dates with formatted diagnoses: {len(dates_with_diagnoses)}")
        print(f"Dates with sufficient weather data: {len(dates_with_weather)}")
        print(f"Dates in existing train_data.json: {len(existing_dates)}")
        
        # Calculate losses at each step
        loss_1 = len(expected_dates) - len(dates_with_diagnoses)
        loss_2 = len(dates_with_diagnoses) - len(dates_with_weather)
        
        print(f"\nLosses:")
        print(f"❌ Lost {loss_1} dates due to missing formatted diagnoses")
        print(f"❌ Lost {loss_2} dates due to insufficient weather data")
        
        if existing_dates:
            missing_from_training = dates_with_weather - existing_dates
            if missing_from_training:
                print(f"❌ {len(missing_from_training)} dates should be in training but aren't:")
                for date in sorted(missing_from_training)[:20]:  # Show first 20
                    print(f"  - {date}")
                if len(missing_from_training) > 20:
                    print(f"  ... and {len(missing_from_training) - 20} more")
        
        print(f"\n💡 RECOMMENDATION:")
        if loss_1 > 0:
            print(f"   1. Generate more formatted diagnoses for missing dates")
        if loss_2 > 0:
            print(f"   2. Check weather data availability for problem dates")
        if existing_dates and len(dates_with_weather) > len(existing_dates):
            print(f"   3. Re-run training data generation to include all available dates")
        
        print(f"{'='*80}")
        
        return {
            'expected_dates': expected_dates,
            'dates_with_diagnoses': dates_with_diagnoses,
            'dates_with_weather': dates_with_weather,
            'existing_dates': existing_dates
        }

def main():
    """Run the diagnostic."""
    
    diagnostic = DateDiagnostic(year=2024, past_days=5)
    results = diagnostic.run_complete_diagnostic()
    
    # Save diagnostic results
    with open("diagnostic_results.json", 'w', encoding='utf-8') as f:
        # Convert sets to lists for JSON serialization
        json_results = {
            'expected_dates': sorted(list(results['expected_dates'])),
            'dates_with_diagnoses': sorted(list(results['dates_with_diagnoses'])),
            'dates_with_weather': sorted(list(results['dates_with_weather'])),
            'existing_dates': sorted(list(results['existing_dates']))
        }
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Diagnostic results saved to diagnostic_results.json")

if __name__ == "__main__":
    main()
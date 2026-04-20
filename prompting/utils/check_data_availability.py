# import pandas as pd
# from datetime import datetime, timedelta
# from pathlib import Path

# def check_data_availability(target_date_str, num_days):
#     """
#     Check if there's sufficient meteorological data for a given date range.
    
#     Meteorological days run from 08:30 of one day to 06:30 of the next day.
#     For example, meteorological day 2024-01-05 spans from 2024-01-04 08:30:00 to 2024-01-05 06:30:00.
    
#     Args:
#         target_date_str (str): Target date in format "yyyy-mm-dd" (e.g., "2024-01-05")
#         num_days (int): Number of meteorological days to check (e.g., 5)
    
#     Returns:
#         dict: {
#             'sufficient_data': bool,
#             'start_datetime': datetime,
#             'end_datetime': datetime,
#             'expected_records': int,
#             'found_records': int,
#             'missing_records': int,
#             'coverage_percentage': float,
#             'missing_timestamps': list
#         }
#     """
    
#     print(f"=" * 60)
#     print(f"CHECKING DATA AVAILABILITY")
#     print(f"Target date: {target_date_str}")
#     print(f"Number of days: {num_days}")
#     print(f"=" * 60)
    
#     # Load the data
#     bucuresti_folder = Path("date/bucuresti")
#     target_file = "SirDate_1748514797752_Bucuresti.csv"
#     target_path = bucuresti_folder / target_file
    
#     if not target_path.exists():
#         print(f"❌ Data file not found: {target_path}")
#         return {
#             'sufficient_data': False,
#             'error': f"File not found: {target_path}"
#         }
    
#     try:
#         df = pd.read_csv(target_path, encoding='utf-8')
#         print(f"✓ Loaded data file: {df.shape}")
        
#         if 'Data masurarii' not in df.columns:
#             available_cols = [col for col in df.columns if 'data' in col.lower() or 'masur' in col.lower()]
#             print(f"❌ 'Data masurarii' column not found")
#             print(f"Available date-related columns: {available_cols}")
#             return {
#                 'sufficient_data': False,
#                 'error': "'Data masurarii' column not found"
#             }
            
#     except Exception as e:
#         print(f"❌ Error loading data: {e}")
#         return {
#             'sufficient_data': False,
#             'error': f"Error loading data: {e}"
#         }
    
#     # Parse target date
#     try:
#         target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
#         print(f"✓ Parsed target date: {target_date}")
#     except ValueError as e:
#         print(f"❌ Invalid date format. Expected 'yyyy-mm-dd', got: {target_date_str}")
#         return {
#             'sufficient_data': False,
#             'error': f"Invalid date format: {target_date_str}"
#         }
    
#     # Calculate the date range for meteorological days
#     # For num_days ending on target_date, we need:
#     # - Start: (target_date - num_days + 1) - 1 day + 08:30:00
#     # - End: target_date + 06:30:00
    
#     # Calculate start datetime
#     start_date = target_date - timedelta(days=num_days)  # Go back num_days
#     start_datetime = datetime.combine(start_date, datetime.min.time().replace(hour=8, minute=30))
    
#     # Calculate end datetime  
#     end_datetime = datetime.combine(target_date, datetime.min.time().replace(hour=6, minute=30))
    
#     print(f"✓ Calculated date range:")
#     print(f"  Start: {start_datetime}")
#     print(f"  End: {end_datetime}")
    
#     # Generate all expected timestamps (assuming 30-minute intervals)
#     expected_timestamps = []
#     current_dt = start_datetime
    
#     while current_dt <= end_datetime:
#         expected_timestamps.append(current_dt)
#         current_dt += timedelta(hours=1)     # Every hour

#     print(f"✓ Generated {len(expected_timestamps)} expected timestamps (1-hour intervals)")
#     print(f"  First: {expected_timestamps[0]}")
#     print(f"  Last: {expected_timestamps[-1]}")
    
#     # Convert data timestamps to datetime objects
#     try:
#         # Handle different possible datetime formats
#         data_timestamps = pd.to_datetime(df['Data masurarii']).tolist()
#         print(f"✓ Converted {len(data_timestamps)} data timestamps")
        
#         # Show sample of actual data timestamps
#         print(f"Sample data timestamps:")
#         for i, ts in enumerate(data_timestamps[:5]):
#             print(f"  {i+1}. {ts}")
            
#     except Exception as e:
#         print(f"❌ Error parsing timestamps: {e}")
#         return {
#             'sufficient_data': False,
#             'error': f"Error parsing timestamps: {e}"
#         }
    
#     # Convert to set for faster lookup
#     data_timestamp_set = set(data_timestamps)
    
#     # Check which expected timestamps are missing
#     missing_timestamps = []
#     found_count = 0
    
#     for expected_ts in expected_timestamps:
#         if expected_ts in data_timestamp_set:
#             found_count += 1
#         else:
#             missing_timestamps.append(expected_ts)
    
#     # Calculate statistics
#     expected_count = len(expected_timestamps)
#     missing_count = len(missing_timestamps)
#     coverage_percentage = (found_count / expected_count) * 100 if expected_count > 0 else 0
    
#     # Determine if data is sufficient (e.g., require 95% coverage)
#     sufficient_threshold = 95.0  # Can be adjusted
#     sufficient_data = coverage_percentage >= sufficient_threshold
    
#     print(f"\n" + "-" * 40)
#     print(f"DATA AVAILABILITY RESULTS")
#     print(f"-" * 40)
#     print(f"Expected records: {expected_count}")
#     print(f"Found records: {found_count}")
#     print(f"Missing records: {missing_count}")
#     print(f"Coverage: {coverage_percentage:.2f}%")
#     print(f"Sufficient data (≥{sufficient_threshold}%): {'✓ YES' if sufficient_data else '❌ NO'}")
    
#     # Show some missing timestamps if any
#     if missing_timestamps:
#         print(f"\nFirst 10 missing timestamps:")
#         for i, ts in enumerate(missing_timestamps[:10]):
#             print(f"  {i+1}. {ts}")
#         if len(missing_timestamps) > 10:
#             print(f"  ... and {len(missing_timestamps) - 10} more")
    
#     return {
#         'sufficient_data': sufficient_data,
#         'start_datetime': start_datetime,
#         'end_datetime': end_datetime,
#         'expected_records': expected_count,
#         'found_records': found_count,
#         'missing_records': missing_count,
#         'coverage_percentage': coverage_percentage,
#         'missing_timestamps': missing_timestamps,
#         'threshold_used': sufficient_threshold
#     }

# # def batch_check_data_availability(date_list, num_days):
# #     """
# #     Check data availability for multiple dates.
    
# #     Args:
# #         date_list (list): List of date strings in format "yyyy-mm-dd"
# #         num_days (int): Number of days to check for each date
    
# #     Returns:
# #         pd.DataFrame: Summary of results for all dates
# #     """
    
# #     results = []
    
# #     print(f"BATCH CHECKING DATA AVAILABILITY FOR {len(date_list)} DATES")
# #     print(f"=" * 60)
    
# #     for i, date_str in enumerate(date_list):
# #         print(f"\n[{i+1}/{len(date_list)}] Checking {date_str}...")
        
# #         result = check_data_availability(date_str, num_days)
        
# #         if 'error' not in result:
# #             results.append({
# #                 'date': date_str,
# #                 'num_days': num_days,
# #                 'sufficient_data': result['sufficient_data'],
# #                 'coverage_percentage': result['coverage_percentage'],
# #                 'expected_records': result['expected_records'],
# #                 'found_records': result['found_records'],
# #                 'missing_records': result['missing_records'],
# #                 'start_datetime': result['start_datetime'],
# #                 'end_datetime': result['end_datetime']
# #             })
# #         else:
# #             results.append({
# #                 'date': date_str,
# #                 'num_days': num_days,
# #                 'sufficient_data': False,
# #                 'coverage_percentage': 0.0,
# #                 'expected_records': 0,
# #                 'found_records': 0,
# #                 'missing_records': 0,
# #                 'error': result['error']
# #             })
    
# #     # Create summary DataFrame
# #     summary_df = pd.DataFrame(results)
    
# #     print(f"\n" + "=" * 60)
# #     print(f"BATCH RESULTS SUMMARY")
# #     print(f"=" * 60)
    
# #     if not summary_df.empty:
# #         sufficient_count = summary_df['sufficient_data'].sum()
# #         total_count = len(summary_df)
        
# #         print(f"Total dates checked: {total_count}")
# #         print(f"Dates with sufficient data: {sufficient_count}")
# #         print(f"Success rate: {(sufficient_count/total_count)*100:.1f}%")
        
# #         if 'coverage_percentage' in summary_df.columns:
# #             avg_coverage = summary_df['coverage_percentage'].mean()
# #             print(f"Average coverage: {avg_coverage:.2f}%")
    
# #     return summary_df
    
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


def check_data_availability(target_date_str, num_days):
    """
    Check if there's sufficient meteorological data for a given date range.

    Meteorological days run from 08:30 of one day to 06:30 of the next day.
    For example, meteorological day 2024-01-05 spans from 2024-01-04 08:30:00
    to 2024-01-05 06:30:00.

    Args:
        target_date_str (str): Target date in format "yyyy-mm-dd" (e.g., "2024-01-05")
        num_days (int): Number of meteorological days to check (e.g., 5)

    Returns:
        dict: {
            'sufficient_data': bool,
            'start_datetime': datetime,
            'end_datetime': datetime,
            'expected_records': int,
            'found_records': int,
            'missing_records': int,
            'coverage_percentage': float,
            'missing_timestamps': list,
            'threshold_used': float,
        }
        On error, returns {'sufficient_data': False, 'error': <message>}.
    """

    # Load the data
    bucuresti_folder = Path("date/bucuresti")
    target_file = "SirDate_1748514797752_Bucuresti.csv"
    target_path = bucuresti_folder / target_file

    if not target_path.exists():
        print(f"Data file not found: {target_path}")
        return {
            'sufficient_data': False,
            'error': f"File not found: {target_path}",
        }

    try:
        df = pd.read_csv(target_path, encoding='utf-8')
        print(f"Loaded {target_file}: {df.shape[0]} rows, {df.shape[1]} columns")

        if 'Data masurarii' not in df.columns:
            available_cols = [c for c in df.columns if 'data' in c.lower() or 'masur' in c.lower()]
            print(f"'Data masurarii' column not found. Date-related columns present: {available_cols}")
            return {
                'sufficient_data': False,
                'error': "'Data masurarii' column not found",
            }

    except Exception as e:
        print(f"Error loading data: {e}")
        return {
            'sufficient_data': False,
            'error': f"Error loading data: {e}",
        }

    # Parse target date
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Invalid date format. Expected 'yyyy-mm-dd', got: {target_date_str}")
        return {
            'sufficient_data': False,
            'error': f"Invalid date format: {target_date_str}",
        }

    # Calculate the meteorological window.
    # For num_days ending on target_date:
    #   start = (target_date - num_days) at 08:30
    #   end   = target_date at 06:30
    start_date = target_date - timedelta(days=num_days)
    start_datetime = datetime.combine(start_date, datetime.min.time().replace(hour=8, minute=30))
    end_datetime = datetime.combine(target_date, datetime.min.time().replace(hour=6, minute=30))

    # Generate all expected timestamps at 1-hour intervals across the window.
    expected_timestamps = []
    current_dt = start_datetime
    while current_dt <= end_datetime:
        expected_timestamps.append(current_dt)
        current_dt += timedelta(hours=1)

    # Convert data timestamps and check membership
    try:
        data_timestamps = pd.to_datetime(df['Data masurarii']).tolist()
    except Exception as e:
        print(f"Error parsing timestamps: {e}")
        return {
            'sufficient_data': False,
            'error': f"Error parsing timestamps: {e}",
        }

    data_timestamp_set = set(data_timestamps)

    missing_timestamps = [ts for ts in expected_timestamps if ts not in data_timestamp_set]
    expected_count = len(expected_timestamps)
    found_count = expected_count - len(missing_timestamps)
    missing_count = len(missing_timestamps)
    coverage_percentage = (found_count / expected_count) * 100 if expected_count > 0 else 0

    sufficient_threshold = 95.0
    sufficient_data = coverage_percentage >= sufficient_threshold

    print(
        f"Data availability for {target_date_str} ({num_days} days): "
        f"window {start_datetime} -> {end_datetime}, "
        f"{found_count}/{expected_count} records "
        f"({coverage_percentage:.2f}% coverage, threshold {sufficient_threshold}%), "
        f"sufficient={sufficient_data}"
    )

    return {
        'sufficient_data': sufficient_data,
        'start_datetime': start_datetime,
        'end_datetime': end_datetime,
        'expected_records': expected_count,
        'found_records': found_count,
        'missing_records': missing_count,
        'coverage_percentage': coverage_percentage,
        'missing_timestamps': missing_timestamps,
        'threshold_used': sufficient_threshold,
    }

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
    
import argparse
import pandas as pd
import sys
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


def check_station_coverage(
    date_folder: str = "date",
    output_filename: str = "station_coverage.json",
    station_column: str = "Denumire",
) -> dict:
    """
    Audit station-name coverage across the raw CSV files in `date_folder`.

    Reads every top-level CSV in the folder (subdirectories like
    `bucuresti/` are ignored), extracts the unique values from the
    `station_column` of each file, and reports:

      - intersection_stations: stations present in *every* file
      - extra_stations_by_file: for each file, the stations that file
        contains beyond the intersection (i.e. stations the file has
        that aren't shared by all the others). When this map is empty
        for every file, the files agree perfectly.

    Per-file full station lists are intentionally not emitted; the
    report focuses on the strict intersection and on the per-file
    asymmetric extras only.

    The result is written as JSON to `{date_folder}/{output_filename}`
    and also returned in memory.

    Args:
        date_folder: Folder containing the raw CSV files.
        output_filename: Name of the JSON to write inside `date_folder`.
        station_column: Column holding station names. Defaults to the
            Romanian 'Denumire' used by ANM exports.

    Returns:
        {
            'date_folder': str,
            'files_scanned': [str, ...],
            'intersection_stations': [station, ...],
            'extra_stations_by_file': {filename: [station, ...]},
            'all_files_consistent': bool,
            'errors': {filename: error_message, ...},
        }
    """
    import json

    folder = Path(date_folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"date folder not found: {folder.resolve()}")

    csv_files = sorted(p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".csv")

    per_file_stations: dict = {}
    errors: dict = {}

    for filename in csv_files:
        path = folder / filename
        try:
            df = pd.read_csv(path, encoding="utf-8", usecols=[station_column])
        except ValueError as e:
            errors[filename] = f"missing '{station_column}' column: {e}"
            continue
        except Exception as e:
            errors[filename] = f"read failed: {e}"
            continue

        stations = sorted(
            {str(s).strip() for s in df[station_column].dropna().unique() if str(s).strip()}
        )
        per_file_stations[filename] = stations

    if per_file_stations:
        station_sets = [set(v) for v in per_file_stations.values()]
        intersection = set.intersection(*station_sets)
    else:
        intersection = set()

    extra_stations_by_file = {
        filename: sorted(set(stations) - intersection)
        for filename, stations in per_file_stations.items()
        if set(stations) - intersection
    }

    result = {
        "date_folder": str(folder),
        "files_scanned": list(per_file_stations.keys()),
        "intersection_stations": sorted(intersection),
        "extra_stations_by_file": extra_stations_by_file,
        "all_files_consistent": len(extra_stations_by_file) == 0 and not errors,
        "errors": errors,
    }

    output_path = folder / output_filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Scanned {len(per_file_stations)} CSV file(s) in '{folder}'")
    print(f"  Intersection (present in every file): {len(intersection)} stations")
    if extra_stations_by_file:
        for filename, extras in extra_stations_by_file.items():
            print(f"  EXTRAS in {filename} beyond intersection: {len(extras)} station(s) "
                  f"-> {extras[:5]}{'...' if len(extras) > 5 else ''}")
    else:
        print("  No per-file extras - every file agrees on the same station set.")
    if errors:
        for filename, msg in errors.items():
            print(f"  ERROR reading {filename}: {msg}")
    print(f"Wrote report to {output_path}")

    return result


def _neighbour_fill(
    df: pd.DataFrame,
    columns: list,
    group_column: str,
    fill_window_days: int,
) -> pd.DataFrame:
    """
    Fill NaN cells in each `columns` entry by averaging the valid
    values in a centred window of size 2N+1 around each cell, computed
    per `group_column` group (typically a per-station temporal fill).

    Returns a copy of `df` with the named columns filled where possible.
    Cells with no valid neighbour in the window stay NaN.

    The arithmetic uses pandas' rolling sum/count rather than `.mean()`
    so the centre cell can be subtracted out - a valid centre would
    otherwise bias its own fill. `min_periods=1` ensures the window
    mean is computed whenever at least one neighbour is valid.
    """
    out = df.copy()
    N = fill_window_days

    def _fill_col(group: pd.DataFrame, col: str) -> pd.Series:
        s = group[col]
        win = s.rolling(window=2 * N + 1, center=True, min_periods=1)
        win_sum = win.sum()
        win_cnt = win.count()
        centre_contrib = s.fillna(0.0)
        centre_present = s.notna().astype(int)
        neighbour_sum = win_sum - centre_contrib
        neighbour_cnt = win_cnt - centre_present
        neighbour_mean = neighbour_sum.where(neighbour_cnt > 0) / neighbour_cnt.where(neighbour_cnt > 0)
        return s.fillna(neighbour_mean)

    for col in columns:
        out[col] = out.groupby(group_column, group_keys=False).apply(
            lambda g, _c=col: _fill_col(g, _c)
        )
    return out


def _load_station_metadata(regions_json_path: Path) -> tuple:
    """
    Walk the nested `stations_by_region` block in the regions JSON and
    return two flat mappings:

        ({station: regiune}, {station: judet})

    Expected JSON shape (per generate_stations_by_region's output):

        "stations_by_region": {
            "<region>": {
                "<county_code>": ["<station>", ...],
                ...
            },
            ...
        }

    Raises FileNotFoundError if the path doesn't exist; KeyError if the
    expected `stations_by_region` block is missing.
    """
    import json
    if not regions_json_path.is_file():
        raise FileNotFoundError(f"regions file not found: {regions_json_path}")
    with open(regions_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "stations_by_region" not in data:
        raise KeyError(
            f"{regions_json_path.name} is missing 'stations_by_region'; "
            f"available top-level keys: {list(data.keys())}"
        )

    station_to_region: dict = {}
    station_to_county: dict = {}
    for region, counties in data["stations_by_region"].items():
        if not isinstance(counties, dict):
            raise ValueError(
                f"stations_by_region[{region!r}] must be a county->stations dict; "
                f"got {type(counties).__name__}. Regenerate the regions JSON "
                f"with the `regions` subcommand."
            )
        for county, stations in counties.items():
            for station in stations:
                station_to_region[str(station)] = str(region)
                station_to_county[str(station)] = str(county)
    return station_to_region, station_to_county


def _aggregate_by_group(per_station: dict, station_to_group: dict) -> tuple:
    """
    Macro-average per-station monthly means within each group label.

    Returns (per_group_dict, unmapped_station_list).

    For each group, the output dict carries the mean of per-station
    mean_temp / mean_tmax / mean_tmin over the stations that both belong
    to that group (per `station_to_group`) and produced usable data this
    month (present as keys in `per_station`). It also records
    `stations_expected` (how many stations the group registry claimed)
    and `stations_missing` (those expected stations that produced no
    usable data this month).
    """
    if not station_to_group:
        return {}, []

    expected_per_group: dict = {}
    for station_name, group in station_to_group.items():
        expected_per_group.setdefault(group, []).append(station_name)

    active_per_group: dict = {}
    unmapped: list = []
    for station_name in per_station.keys():
        group = station_to_group.get(station_name)
        if group is None:
            unmapped.append(station_name)
            continue
        active_per_group.setdefault(group, []).append(station_name)

    out: dict = {}
    for group in sorted(set(expected_per_group) | set(active_per_group)):
        active = active_per_group.get(group, [])
        expected = expected_per_group.get(group, [])
        missing = sorted(set(expected) - set(active))
        if not active:
            out[group] = {
                "mean_temp": None,
                "mean_tmax": None,
                "mean_tmin": None,
                "stations_aggregated": 0,
                "stations_expected": len(expected),
                "stations_missing": missing,
            }
            continue
        out[group] = {
            "mean_temp": float(sum(per_station[s]["mean_temp"] for s in active) / len(active)),
            "mean_tmax": float(sum(per_station[s]["mean_tmax"] for s in active) / len(active)),
            "mean_tmin": float(sum(per_station[s]["mean_tmin"] for s in active) / len(active)),
            "stations_aggregated": len(active),
            "stations_expected": len(expected),
            "stations_missing": missing,
        }
    return out, unmapped


def analyze_monthly_temperature(
    month: str,
    date_folder: str = "date",
    temp_csv_glob: str = "DateZilniceTemp_*.csv",
    fill_window_days: int = 3,
    sentinel: float = -999.0,
    regions_filename: str = "stations_by_region.json",
    station_column: str = "Denumire",
    date_column: str = "Data masurarii",
    tmax_column: str = "Tamax24",
    tmin_column: str = "Tamin24",
    output_filename: str = None,
) -> dict:
    """
    Compute per-station and global mean temperature for a given month from
    the daily-temperature ANM CSV, filling sentinel-marked missing cells
    from neighbouring days.

    Daily mean temperature is (Tamax24 + Tamin24) / 2. Per-station monthly
    mean is the average of daily means within the target month. Global
    monthly mean is the average of per-station monthly means.

    Sentinel handling: cells equal to `sentinel` (default -999) are treated
    as missing. Missing cells are filled with the mean of the surrounding
    ±`fill_window_days` days for the same station and the same
    column (Tamax and Tmin are filled independently). The fill window
    is allowed to extend outside the target month so days near the
    month boundary still get a value when neighbouring data exists. If
    no valid neighbour exists within the window, the cell stays missing
    and that (station, day) is dropped from downstream means.

    Args:
        month: Target month as 'YYYY-MM'.
        date_folder: Folder containing the temperature CSV.
        temp_csv_glob: Glob to locate the temperature CSV inside
            `date_folder`. The first match is used; an error is raised if
            zero or more than one file matches.
        fill_window_days: Half-width N of the fill window.
            Each missing cell looks at days t-N..t-1 and t+1..t+N for the
            same station and averages the non-missing values it finds.
        sentinel: Value treated as missing in the CSV. Default -999.
        regions_filename: JSON file inside `date_folder` mapping stations
            to historical regions. Expected to expose a `station_details`
            object of the form
            `{station_name: {"regiune": <region>, ...}}`. When the file is
            absent or empty, per-region means are omitted from the report
            and a note is logged.
        station_column, date_column, tmax_column, tmin_column: column
            names in the CSV.
        output_filename: JSON output filename inside `date_folder`. If
            None, defaults to 'temperature_{month}.json'.

    Returns:
        {
            'month': str,
            'csv_file': str,
            'fill_window_days': int,
            'fill_stats': {
                'missing_tmax_total': int,
                'missing_tmin_total': int,
                'filled_tmax': int,
                'filled_tmin': int,
                'still_missing_tmax': int,
                'still_missing_tmin': int,
            },
            'per_station_mean_celsius': {
                station: {'mean_temp': float, 'mean_tmax': float,
                          'mean_tmin': float, 'days_used': int},
                ...
            },
            'global_mean_celsius': {
                'mean_temp': float, 'mean_tmax': float, 'mean_tmin': float,
                'stations_aggregated': int,
            },
            'per_region_mean_celsius': {        # omitted if regions file absent
                region: {'mean_temp': float, 'mean_tmax': float,
                         'mean_tmin': float, 'stations_aggregated': int,
                         'stations_expected': int,
                         'stations_missing': [station, ...]},
                ...
            },
            'per_county_mean_celsius': {        # same shape, keyed by 'judet'
                county_code: { ... },           # same fields as per-region
                ...
            },
            'unmapped_stations': [station, ...], # stations with temp data
                                                  # but no region/county
                                                  # assignment
            'dates_considered': [str, ...],   # YYYY-MM-DD, sorted, at end
        }
    """
    import json
    import re

    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError(f"--month must be 'YYYY-MM', got: {month!r}")
    year_int, month_int = int(month[:4]), int(month[5:7])
    if not (1 <= month_int <= 12):
        raise ValueError(f"month component out of range: {month_int}")

    folder = Path(date_folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"date folder not found: {folder.resolve()}")

    candidates = sorted(folder.glob(temp_csv_glob))
    if not candidates:
        raise FileNotFoundError(
            f"no CSV matching '{temp_csv_glob}' in {folder.resolve()}"
        )
    if len(candidates) > 1:
        raise RuntimeError(
            f"ambiguous temperature CSV: {[p.name for p in candidates]}; "
            f"narrow --temp_csv_glob to a single match"
        )
    csv_path = candidates[0]

    df = pd.read_csv(csv_path, encoding="utf-8",
                     usecols=[station_column, date_column, tmax_column, tmin_column])

    df["_date"] = pd.to_datetime(df[date_column]).dt.normalize()

    for col in (tmax_column, tmin_column):
        df[col] = df[col].mask(df[col] == sentinel)

    missing_tmax_total = int(df[tmax_column].isna().sum())
    missing_tmin_total = int(df[tmin_column].isna().sum())

    df = df.sort_values([station_column, "_date"]).reset_index(drop=True)
    df = _neighbour_fill(
        df, columns=[tmax_column, tmin_column],
        group_column=station_column, fill_window_days=fill_window_days,
    )

    still_missing_tmax = int(df[tmax_column].isna().sum())
    still_missing_tmin = int(df[tmin_column].isna().sum())
    filled_tmax = missing_tmax_total - still_missing_tmax
    filled_tmin = missing_tmin_total - still_missing_tmin

    month_mask = (df["_date"].dt.year == year_int) & (df["_date"].dt.month == month_int)
    month_df = df.loc[month_mask].copy()
    if month_df.empty:
        raise RuntimeError(
            f"no rows in CSV for month {month} "
            f"(file covers {df['_date'].min().date()}..{df['_date'].max().date()})"
        )

    month_df["_daily_mean"] = (month_df[tmax_column] + month_df[tmin_column]) / 2.0

    per_station: dict = {}
    for station, sub in month_df.groupby(station_column):
        valid = sub.dropna(subset=["_daily_mean", tmax_column, tmin_column])
        if valid.empty:
            continue
        per_station[str(station)] = {
            "mean_temp": float(valid["_daily_mean"].mean()),
            "mean_tmax": float(valid[tmax_column].mean()),
            "mean_tmin": float(valid[tmin_column].mean()),
            "days_used": int(len(valid)),
        }

    if per_station:
        global_mean = {
            "mean_temp": float(sum(s["mean_temp"] for s in per_station.values()) / len(per_station)),
            "mean_tmax": float(sum(s["mean_tmax"] for s in per_station.values()) / len(per_station)),
            "mean_tmin": float(sum(s["mean_tmin"] for s in per_station.values()) / len(per_station)),
            "stations_aggregated": len(per_station),
        }
    else:
        global_mean = {"mean_temp": None, "mean_tmax": None, "mean_tmin": None, "stations_aggregated": 0}

    # Per-region and per-county aggregation: macro-average of station
    # means within each group, matching the global-mean convention.
    # Stations with no region/county assignment go into
    # 'unmapped_stations' instead of being silently dropped.
    per_region: dict = {}
    per_county: dict = {}
    unmapped_stations: list = []
    regions_path = folder / regions_filename if regions_filename else None
    station_to_region: dict = {}
    station_to_county: dict = {}
    if regions_path and regions_path.is_file():
        try:
            station_to_region, station_to_county = _load_station_metadata(regions_path)
        except (KeyError, ValueError) as e:
            print(f"NOTE: per-region and per-county means skipped: {e}")
            station_to_region, station_to_county = {}, {}
    elif regions_filename:
        print(f"NOTE: per-region and per-county means skipped; regions file not found: {regions_path}")

    if station_to_region:
        per_region, unmapped_region = _aggregate_by_group(per_station, station_to_region)
        unmapped_stations.extend(unmapped_region)
    if station_to_county:
        per_county, unmapped_county = _aggregate_by_group(per_station, station_to_county)
        # Same per_station drives both aggregations, so the unmapped sets
        # should agree on the station identities even when region/county
        # assignments differ. Union-merge to be safe.
        for s in unmapped_county:
            if s not in unmapped_stations:
                unmapped_stations.append(s)

    dates_considered = sorted({d.strftime("%Y-%m-%d") for d in month_df["_date"].unique()})

    result = {
        "month": month,
        "csv_file": csv_path.name,
        "fill_window_days": fill_window_days,
        "fill_stats": {
            "missing_tmax_total": missing_tmax_total,
            "missing_tmin_total": missing_tmin_total,
            "filled_tmax": filled_tmax,
            "filled_tmin": filled_tmin,
            "still_missing_tmax": still_missing_tmax,
            "still_missing_tmin": still_missing_tmin,
        },
        "per_station_mean_celsius": dict(sorted(per_station.items())),
        "global_mean_celsius": global_mean,
        "per_region_mean_celsius": per_region,
        "per_county_mean_celsius": per_county,
        "unmapped_stations": sorted(unmapped_stations),
        "dates_considered": dates_considered,
    }

    output_name = output_filename or f"temperature_{month}.json"
    output_path = folder / output_name
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Analyzed {csv_path.name} for month {month}")
    print(f"  Stations with usable data: {len(per_station)}")
    print(f"  Missing -> filled -> remaining (Tmax): {missing_tmax_total} -> {filled_tmax} -> {still_missing_tmax}")
    print(f"  Missing -> filled -> remaining (Tmin): {missing_tmin_total} -> {filled_tmin} -> {still_missing_tmin}")
    if per_station:
        print(f"  Global mean temp: {global_mean['mean_temp']:.2f}°C "
              f"(Tmax {global_mean['mean_tmax']:.2f}, Tmin {global_mean['mean_tmin']:.2f})")
    if per_region:
        print(f"  Per-region means ({len(per_region)} regions):")
        for region, stats in per_region.items():
            if stats["mean_temp"] is None:
                print(f"    {region}: no usable data "
                      f"({stats['stations_aggregated']}/{stats['stations_expected']} stations)")
            else:
                print(f"    {region}: {stats['mean_temp']:.2f}°C "
                      f"(Tmax {stats['mean_tmax']:.2f}, Tmin {stats['mean_tmin']:.2f}) "
                      f"[{stats['stations_aggregated']}/{stats['stations_expected']} stations]")
    if per_county:
        # Counties are many (~40 ANM judete); summarise rather than dump.
        with_data = [c for c, s in per_county.items() if s["mean_temp"] is not None]
        no_data = [c for c, s in per_county.items() if s["mean_temp"] is None]
        print(f"  Per-county means: {len(with_data)} county/counties with usable data"
              f"{f', {len(no_data)} with no usable data' if no_data else ''}")
        warmest = max(with_data, key=lambda c: per_county[c]["mean_temp"], default=None)
        coldest = min(with_data, key=lambda c: per_county[c]["mean_temp"], default=None)
        if warmest:
            print(f"    Warmest: {warmest} {per_county[warmest]['mean_temp']:.2f}°C "
                  f"[{per_county[warmest]['stations_aggregated']}/"
                  f"{per_county[warmest]['stations_expected']} stations]")
        if coldest and coldest != warmest:
            print(f"    Coldest: {coldest} {per_county[coldest]['mean_temp']:.2f}°C "
                  f"[{per_county[coldest]['stations_aggregated']}/"
                  f"{per_county[coldest]['stations_expected']} stations]")
    if per_region or per_county:
        if unmapped_stations:
            print(f"  WARNING: {len(unmapped_stations)} station(s) had temp data "
                  f"but no region/county assignment: {unmapped_stations[:5]}"
                  f"{'...' if len(unmapped_stations) > 5 else ''}")
    print(f"  Days included: {len(dates_considered)}")
    print(f"Wrote report to {output_path}")

    return result


def build_county_daily_mean_csv(
    date_folder: str = "date",
    temp_csv_glob: str = "DateZilniceTemp_*.csv",
    regions_filename: str = "stations_by_region.json",
    fill_window_days: int = 3,
    sentinel: float = -999.0,
    output_filename: str = "daily_county_mean.csv",
    metadata_filename: str = "daily_county_mean_metadata.json",
    station_column: str = "Denumire",
    date_column: str = "Data masurarii",
    tmax_column: str = "Tamax24",
    tmin_column: str = "Tamin24",
) -> dict:
    """
    Build the (T, C) county-day mean-temperature matrix used as the
    input tensor for the multivariate baseline models.

    Pipeline:
        raw rows
          -> sentinel masking (sentinel -> NaN)
          -> station-level neighbour fill (±fill_window_days)
          -> per-station daily mean = (Tmax + Tmin) / 2
          -> per-county daily mean (macro average of station means)
          -> wide matrix indexed by date, columns = county codes
          -> fallback fill: county-day NaN -> same-day region mean
                            -> same-day global mean if region still NaN

    The output CSV always contains a complete matrix (no NaN cells) so
    downstream tensor construction is straightforward. The companion
    JSON records exactly how many cells were filled by each fallback
    step and which (date, county) pairs each fallback was applied to.

    Args:
        date_folder, temp_csv_glob, regions_filename, fill_window_days,
        sentinel: same semantics as analyze_monthly_temperature.
        output_filename: wide CSV name inside `date_folder`.
        metadata_filename: companion JSON name inside `date_folder`.
        station_column, date_column, tmax_column, tmin_column: column
            names in the measurement CSV.

    Returns:
        {
            'csv_file': str,                       # measurement CSV name
            'output_csv': str,
            'metadata_file': str,
            'shape': [n_dates, n_counties],
            'date_range': [first_date, last_date], # YYYY-MM-DD
            'counties': [county_code, ...],        # column order in CSV
            'station_fill_stats': {                # neighbour-fill audit
                'missing_tmax_total': int,
                'missing_tmin_total': int,
                'filled_tmax': int, 'filled_tmin': int,
                'still_missing_tmax': int,
                'still_missing_tmin': int,
            },
            'matrix_fill_stats': {
                'cells_total': int,                # n_dates * n_counties
                'cells_from_county_mean': int,     # before any fallback
                'cells_filled_by_region': int,
                'cells_filled_by_global': int,
                'cells_still_missing': int,        # should be 0
            },
            'fallback_cells': {
                'region': [[date, county], ...],
                'global': [[date, county], ...],
            },
            'unmapped_stations': [station, ...],
        }
    """
    import json

    folder = Path(date_folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"date folder not found: {folder.resolve()}")

    candidates = sorted(folder.glob(temp_csv_glob))
    if not candidates:
        raise FileNotFoundError(
            f"no CSV matching '{temp_csv_glob}' in {folder.resolve()}"
        )
    if len(candidates) > 1:
        raise RuntimeError(
            f"ambiguous temperature CSV: {[p.name for p in candidates]}; "
            f"narrow --temp_csv_glob"
        )
    csv_path = candidates[0]

    regions_path = folder / regions_filename
    station_to_region, station_to_county = _load_station_metadata(regions_path)

    # --- station-level prep ---
    df = pd.read_csv(
        csv_path, encoding="utf-8",
        usecols=[station_column, date_column, tmax_column, tmin_column],
    )
    df["_date"] = pd.to_datetime(df[date_column]).dt.normalize()
    for col in (tmax_column, tmin_column):
        df[col] = df[col].mask(df[col] == sentinel)

    missing_tmax_total = int(df[tmax_column].isna().sum())
    missing_tmin_total = int(df[tmin_column].isna().sum())

    df = df.sort_values([station_column, "_date"]).reset_index(drop=True)
    df = _neighbour_fill(
        df, columns=[tmax_column, tmin_column],
        group_column=station_column, fill_window_days=fill_window_days,
    )
    still_missing_tmax = int(df[tmax_column].isna().sum())
    still_missing_tmin = int(df[tmin_column].isna().sum())

    df["_daily_mean"] = (df[tmax_column] + df[tmin_column]) / 2.0
    df["_county"] = df[station_column].map(station_to_county)
    df["_region"] = df[station_column].map(station_to_region)

    unmapped_stations = sorted({
        str(s) for s in df.loc[df["_county"].isna(), station_column].unique()
        if pd.notna(s)
    })
    df_mapped = df.dropna(subset=["_county", "_daily_mean"]).copy()

    # --- aggregate to county-day, region-day, global-day ---
    county_day = (
        df_mapped.groupby(["_date", "_county"])["_daily_mean"]
        .mean().rename("mean_temp").reset_index()
    )
    region_day = (
        df_mapped.groupby(["_date", "_region"])["_daily_mean"]
        .mean().rename("region_mean").reset_index()
    )
    global_day = (
        df_mapped.groupby(["_date"])["_daily_mean"]
        .mean().rename("global_mean").reset_index()
    )

    # Build the wide matrix: rows=date, cols=county.
    matrix = county_day.pivot(index="_date", columns="_county", values="mean_temp")
    matrix = matrix.sort_index()
    matrix.columns = [str(c) for c in matrix.columns]
    matrix = matrix.reindex(sorted(matrix.columns), axis=1)

    # Map each county to its region for the fallback lookup.
    # All stations in a county share the same region (per the regions
    # JSON's nested structure), so the lookup is unambiguous.
    county_to_region = {}
    for region, counties in json.load(
        open(regions_path, "r", encoding="utf-8")
    )["stations_by_region"].items():
        for county in counties:
            county_to_region[str(county)] = str(region)

    region_lookup = (
        region_day.set_index(["_date", "_region"])["region_mean"]
    )
    global_lookup = global_day.set_index("_date")["global_mean"]

    fallback_region: list = []
    fallback_global: list = []
    cells_total = matrix.size

    for county in matrix.columns:
        region = county_to_region.get(county)
        col = matrix[county]
        na_mask = col.isna()
        if not na_mask.any():
            continue
        for date in col.index[na_mask]:
            value = None
            if region is not None:
                try:
                    value = region_lookup.loc[(date, region)]
                except KeyError:
                    value = None
            if value is None or pd.isna(value):
                try:
                    value = global_lookup.loc[date]
                    fallback_global.append([date.strftime("%Y-%m-%d"), county])
                except KeyError:
                    value = None
            else:
                fallback_region.append([date.strftime("%Y-%m-%d"), county])
            if value is not None and not pd.isna(value):
                matrix.at[date, county] = float(value)

    cells_still_missing = int(matrix.isna().sum().sum())

    # --- write CSV (date as ISO index) ---
    output_path = folder / output_filename
    matrix_for_csv = matrix.copy()
    matrix_for_csv.index = matrix_for_csv.index.strftime("%Y-%m-%d")
    matrix_for_csv.index.name = "date"
    matrix_for_csv.to_csv(output_path, encoding="utf-8")

    cells_from_county = cells_total - len(fallback_region) - len(fallback_global) - cells_still_missing

    metadata = {
        "csv_file": csv_path.name,
        "output_csv": output_path.name,
        "metadata_file": metadata_filename,
        "shape": list(matrix.shape),
        "date_range": [
            matrix.index.min().strftime("%Y-%m-%d"),
            matrix.index.max().strftime("%Y-%m-%d"),
        ],
        "counties": list(matrix.columns),
        "fill_window_days": fill_window_days,
        "station_fill_stats": {
            "missing_tmax_total": missing_tmax_total,
            "missing_tmin_total": missing_tmin_total,
            "filled_tmax": missing_tmax_total - still_missing_tmax,
            "filled_tmin": missing_tmin_total - still_missing_tmin,
            "still_missing_tmax": still_missing_tmax,
            "still_missing_tmin": still_missing_tmin,
        },
        "matrix_fill_stats": {
            "cells_total": cells_total,
            "cells_from_county_mean": cells_from_county,
            "cells_filled_by_region": len(fallback_region),
            "cells_filled_by_global": len(fallback_global),
            "cells_still_missing": cells_still_missing,
        },
        "fallback_cells": {
            "region": fallback_region,
            "global": fallback_global,
        },
        "unmapped_stations": unmapped_stations,
    }

    metadata_path = folder / metadata_filename
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Built county-day matrix from {csv_path.name}")
    print(f"  Shape: {matrix.shape[0]} days x {matrix.shape[1]} counties")
    print(f"  Date range: {metadata['date_range'][0]} .. {metadata['date_range'][1]}")
    print(f"  Station-level fill: Tmax {missing_tmax_total}->{still_missing_tmax}, "
          f"Tmin {missing_tmin_total}->{still_missing_tmin}")
    print(f"  Matrix cells: {cells_total} total, "
          f"{cells_from_county} from county aggregation, "
          f"{len(fallback_region)} from region fallback, "
          f"{len(fallback_global)} from global fallback, "
          f"{cells_still_missing} unfilled")
    print(f"Wrote {output_path}")
    print(f"Wrote {metadata_path}")

    return metadata


def build_county_daily_precip_csv(
    date_folder: str = "date",
    precip_csv_glob: str = "DateZilnicePrecip_*.csv",
    regions_filename: str = "stations_by_region.json",
    fill_window_days: int = 3,
    sentinel: float = -999.0,
    date_shift_days: int = -1,
    output_filename: str = "daily_county_precip.csv",
    metadata_filename: str = "daily_county_precip_metadata.json",
    station_column: str = "Denumire",
    date_column: str = "Data masurarii",
    precip_column: str = "R24",
) -> dict:
    """
    Build the (T, C) county-day precipitation matrix (R24 in mm) used
    as an auxiliary input channel for the multivariate baselines.

    Pipeline mirrors `build_county_daily_mean_csv` but adds a calendar
    date attribution shift:

        raw rows
          -> sentinel masking (sentinel -> NaN)
          -> date attribution shift (default `date_shift_days=-1`)
          -> station-level neighbour fill (±fill_window_days)
          -> per-county daily mean across stations (no transformation;
             the matrix stores RAW R24 in mm)
          -> wide matrix indexed by date, columns = county code
          -> fallback fill: county-day NaN
               -> same-day region mean
               -> same-day global mean if region also NaN

    Why the date shift:
        ANM stamps each precipitation row with the morning observation
        time (~05:30 of the recorded calendar date). The R24 value then
        represents the rainfall accumulated over the PREVIOUS 24 hours,
        so a row stamped `2024-03-15T05:30:00` actually reports the
        precipitation that fell during `2024-03-14`. We shift the date
        by `date_shift_days = -1` so the matrix index is the calendar
        day on which the rain fell, matching how downstream consumers
        (and humans) think about it.

    Normalisation:
        The CSV stores RAW R24 in mm so the file is interpretable as a
        physical quantity. Precipitation is strongly right-skewed, so
        the training pipeline is expected to apply log1p before the
        per-county z-score (the transformation lives at training time,
        not in this builder).

    Args:
        date_folder: Folder holding inputs and outputs.
        precip_csv_glob: Glob to locate the precipitation CSV.
        regions_filename: JSON file mapping station to region/county.
        fill_window_days: Half-width N of the station-level neighbour fill.
        sentinel: Value treated as missing in the CSV (default -999).
        date_shift_days: How many days to shift the row date by before
            building the matrix. Default -1; pass 0 to disable the
            shift entirely (e.g. for diagnostics or if the upstream
            convention changes).
        output_filename: Wide CSV filename inside `date_folder`.
        metadata_filename: Companion JSON filename inside `date_folder`.
        station_column, date_column, precip_column: column names in the
            measurement CSV.

    Returns:
        Same shape as build_county_daily_mean_csv's metadata return,
        with `station_fill_stats` carrying only the precipitation column
        and an added `date_shift_days` field at the top level.
    """
    import json

    folder = Path(date_folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"date folder not found: {folder.resolve()}")

    candidates = sorted(folder.glob(precip_csv_glob))
    if not candidates:
        raise FileNotFoundError(
            f"no CSV matching '{precip_csv_glob}' in {folder.resolve()}"
        )
    if len(candidates) > 1:
        raise RuntimeError(
            f"ambiguous precipitation CSV: {[p.name for p in candidates]}; "
            f"narrow --precip_csv_glob"
        )
    csv_path = candidates[0]

    regions_path = folder / regions_filename
    station_to_region, station_to_county = _load_station_metadata(regions_path)

    # --- load + sentinel mask + date shift ---
    df = pd.read_csv(
        csv_path, encoding="utf-8",
        usecols=[station_column, date_column, precip_column],
    )
    df["_date"] = pd.to_datetime(df[date_column]).dt.normalize()
    if date_shift_days != 0:
        df["_date"] = df["_date"] + pd.Timedelta(days=date_shift_days)
    df[precip_column] = df[precip_column].mask(df[precip_column] == sentinel)

    missing_total = int(df[precip_column].isna().sum())

    df = df.sort_values([station_column, "_date"]).reset_index(drop=True)
    df = _neighbour_fill(
        df, columns=[precip_column],
        group_column=station_column, fill_window_days=fill_window_days,
    )
    still_missing = int(df[precip_column].isna().sum())

    df["_county"] = df[station_column].map(station_to_county)
    df["_region"] = df[station_column].map(station_to_region)

    unmapped_stations = sorted({
        str(s) for s in df.loc[df["_county"].isna(), station_column].unique()
        if pd.notna(s)
    })
    df_mapped = df.dropna(subset=["_county", precip_column]).copy()

    # --- aggregate to county-day, region-day, global-day ---
    county_day = (
        df_mapped.groupby(["_date", "_county"])[precip_column]
        .mean().rename("precip_mm").reset_index()
    )
    region_day = (
        df_mapped.groupby(["_date", "_region"])[precip_column]
        .mean().rename("region_mean").reset_index()
    )
    global_day = (
        df_mapped.groupby(["_date"])[precip_column]
        .mean().rename("global_mean").reset_index()
    )

    # Wide matrix: rows = date, cols = county code.
    matrix = county_day.pivot(index="_date", columns="_county", values="precip_mm")
    matrix = matrix.sort_index()
    matrix.columns = [str(c) for c in matrix.columns]
    matrix = matrix.reindex(sorted(matrix.columns), axis=1)

    # county -> region lookup (every station in a county shares one region
    # by the regions JSON's nested structure).
    county_to_region = {}
    for region, counties in json.load(
        open(regions_path, "r", encoding="utf-8")
    )["stations_by_region"].items():
        for county in counties:
            county_to_region[str(county)] = str(region)

    region_lookup = region_day.set_index(["_date", "_region"])["region_mean"]
    global_lookup = global_day.set_index("_date")["global_mean"]

    fallback_region: list = []
    fallback_global: list = []
    cells_total = matrix.size

    for county in matrix.columns:
        region = county_to_region.get(county)
        col = matrix[county]
        na_mask = col.isna()
        if not na_mask.any():
            continue
        for date in col.index[na_mask]:
            value = None
            if region is not None:
                try:
                    value = region_lookup.loc[(date, region)]
                except KeyError:
                    value = None
            if value is None or pd.isna(value):
                try:
                    value = global_lookup.loc[date]
                    fallback_global.append([date.strftime("%Y-%m-%d"), county])
                except KeyError:
                    value = None
            else:
                fallback_region.append([date.strftime("%Y-%m-%d"), county])
            if value is not None and not pd.isna(value):
                matrix.at[date, county] = float(value)

    cells_still_missing = int(matrix.isna().sum().sum())

    # --- write CSV (date as ISO index, RAW R24 in mm) ---
    output_path = folder / output_filename
    matrix_for_csv = matrix.copy()
    matrix_for_csv.index = matrix_for_csv.index.strftime("%Y-%m-%d")
    matrix_for_csv.index.name = "date"
    matrix_for_csv.to_csv(output_path, encoding="utf-8")

    cells_from_county = cells_total - len(fallback_region) - len(fallback_global) - cells_still_missing

    metadata = {
        "csv_file": csv_path.name,
        "output_csv": output_path.name,
        "metadata_file": metadata_filename,
        "variable": "precipitation_R24_mm",
        "units": "mm/day",
        "date_shift_days": date_shift_days,
        "date_shift_explanation": (
            "Each input row's Data masurarii is shifted by "
            f"{date_shift_days} day(s) before bucketing. The default "
            "of -1 reflects ANM's morning-observation convention: "
            "R24 stamped at YYYY-MM-DD 05:30 is the 24h accumulation "
            "ending that morning, i.e. the rainfall that fell on "
            "(YYYY-MM-DD - 1 day)."
        ),
        "shape": list(matrix.shape),
        "date_range": [
            matrix.index.min().strftime("%Y-%m-%d"),
            matrix.index.max().strftime("%Y-%m-%d"),
        ],
        "counties": list(matrix.columns),
        "fill_window_days": fill_window_days,
        "station_fill_stats": {
            "missing_total": missing_total,
            "filled": missing_total - still_missing,
            "still_missing": still_missing,
        },
        "matrix_fill_stats": {
            "cells_total": cells_total,
            "cells_from_county_mean": cells_from_county,
            "cells_filled_by_region": len(fallback_region),
            "cells_filled_by_global": len(fallback_global),
            "cells_still_missing": cells_still_missing,
        },
        "fallback_cells": {
            "region": fallback_region,
            "global": fallback_global,
        },
        "unmapped_stations": unmapped_stations,
    }

    metadata_path = folder / metadata_filename
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Built county-day precipitation matrix from {csv_path.name}")
    print(f"  Shape: {matrix.shape[0]} days x {matrix.shape[1]} counties")
    print(f"  Date range: {metadata['date_range'][0]} .. {metadata['date_range'][1]}")
    print(f"  Date shift applied: {date_shift_days} day(s)")
    print(f"  Station-level fill: R24 {missing_total} -> {still_missing}")
    print(f"  Matrix cells: {cells_total} total, "
          f"{cells_from_county} from county aggregation, "
          f"{len(fallback_region)} from region fallback, "
          f"{len(fallback_global)} from global fallback, "
          f"{cells_still_missing} unfilled")
    print(f"Wrote {output_path}")
    print(f"Wrote {metadata_path}")

    return metadata


def build_county_daily_wind_csv(
    date_folder: str = "date",
    hourly_csv_glob: str = "SirDate_*.csv",
    regions_filename: str = "stations_by_region.json",
    fill_window_days: int = 3,
    sentinel: float = -999.0,
    output_filename: str = "daily_county_wind.csv",
    metadata_filename: str = "daily_county_wind_metadata.json",
    station_column: str = "Denumire",
    datetime_column: str = "Data masurarii",
    wind_column: str = "Rff1",
) -> dict:
    """
    Build the (T, C) county-day mean wind-speed matrix from the hourly
    SirDate CSV (Rff1, m/s). Two-stage pipeline:

        STAGE A: hourly -> (station, day)
            -> sentinel masking (-999 -> NaN)
            -> mean of valid Rff1 across hourly readings within each
               calendar day, per station

        STAGE B: (station, day) -> (county, day) wide matrix
            -> station-level neighbour fill (±fill_window_days)
            -> per-county daily mean across stations
            -> wide matrix indexed by date, columns = county code
            -> fallback fill: county-day NaN
                 -> same-day region mean
                 -> same-day global mean if region also NaN

    Stage A's daily reduction uses calendar day (00:00 - 23:59) rather
    than the meteorological 08:30 - 06:30 window the LLM-prompt
    pipeline uses, so the date axis matches the daily temperature and
    precipitation matrices for direct multi-variable stacking.

    Output CSV stores RAW mean wind in m/s; the per-county z-score
    normalisation happens at training time (fit per fold).

    Args:
        date_folder: Folder holding inputs and outputs.
        hourly_csv_glob: Glob for the hourly SirDate CSV.
        regions_filename: JSON file mapping station to region/county.
        fill_window_days: Half-width N of the station-level day-axis fill.
        sentinel: Value treated as missing in the CSV (default -999).
        output_filename: Wide CSV filename inside `date_folder`.
        metadata_filename: Companion JSON filename inside `date_folder`.
        station_column, datetime_column, wind_column: column names in
            the hourly CSV.

    Returns:
        Same shape as build_county_daily_precip_csv's metadata return,
        with `variable` set to "wind_speed_Rff1_ms" and "units" to "m/s".
        `station_fill_stats` reports the hourly->daily reduction
        (`hourly_rows_total`, `hourly_rows_sentinel`,
        `station_day_cells_total`, `station_day_cells_with_data`) plus
        the day-axis neighbour-fill counts.
    """
    import json

    folder = Path(date_folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"date folder not found: {folder.resolve()}")

    candidates = sorted(folder.glob(hourly_csv_glob))
    if not candidates:
        raise FileNotFoundError(
            f"no CSV matching '{hourly_csv_glob}' in {folder.resolve()}"
        )
    if len(candidates) > 1:
        raise RuntimeError(
            f"ambiguous hourly CSV: {[p.name for p in candidates]}; "
            f"narrow --hourly_csv_glob"
        )
    csv_path = candidates[0]

    regions_path = folder / regions_filename
    station_to_region, station_to_county = _load_station_metadata(regions_path)

    # --- STAGE A: hourly -> (station, day) ---
    df = pd.read_csv(
        csv_path, encoding="utf-8",
        usecols=[station_column, datetime_column, wind_column],
    )
    df[datetime_column] = pd.to_datetime(df[datetime_column])
    df["_date"] = df[datetime_column].dt.normalize()

    hourly_rows_total = len(df)
    hourly_rows_sentinel = int((df[wind_column] == sentinel).sum())
    df[wind_column] = df[wind_column].mask(df[wind_column] == sentinel)

    # Mean of valid Rff1 per (station, day). pandas .mean() ignores NaN by
    # default, so days with all-NaN hours produce NaN (handled by neighbour
    # fill in stage B).
    station_day = (
        df.groupby([station_column, "_date"])[wind_column]
        .mean().reset_index()
        .rename(columns={wind_column: wind_column})
    )

    station_day_cells_total = len(station_day)
    station_day_cells_with_data = int(station_day[wind_column].notna().sum())
    missing_total = station_day_cells_total - station_day_cells_with_data

    # --- STAGE B: (station, day) -> (county, day) wide matrix ---
    station_day = station_day.sort_values([station_column, "_date"]).reset_index(drop=True)
    station_day = _neighbour_fill(
        station_day, columns=[wind_column],
        group_column=station_column, fill_window_days=fill_window_days,
    )
    still_missing = int(station_day[wind_column].isna().sum())

    station_day["_county"] = station_day[station_column].map(station_to_county)
    station_day["_region"] = station_day[station_column].map(station_to_region)

    unmapped_stations = sorted({
        str(s) for s in station_day.loc[station_day["_county"].isna(), station_column].unique()
        if pd.notna(s)
    })
    sd_mapped = station_day.dropna(subset=["_county", wind_column]).copy()

    county_day = (
        sd_mapped.groupby(["_date", "_county"])[wind_column]
        .mean().rename("wind_ms").reset_index()
    )
    region_day = (
        sd_mapped.groupby(["_date", "_region"])[wind_column]
        .mean().rename("region_mean").reset_index()
    )
    global_day = (
        sd_mapped.groupby(["_date"])[wind_column]
        .mean().rename("global_mean").reset_index()
    )

    matrix = county_day.pivot(index="_date", columns="_county", values="wind_ms")
    matrix = matrix.sort_index()
    matrix.columns = [str(c) for c in matrix.columns]
    matrix = matrix.reindex(sorted(matrix.columns), axis=1)

    county_to_region = {}
    for region, counties in json.load(
        open(regions_path, "r", encoding="utf-8")
    )["stations_by_region"].items():
        for county in counties:
            county_to_region[str(county)] = str(region)

    region_lookup = region_day.set_index(["_date", "_region"])["region_mean"]
    global_lookup = global_day.set_index("_date")["global_mean"]

    fallback_region: list = []
    fallback_global: list = []
    cells_total = matrix.size

    for county in matrix.columns:
        region = county_to_region.get(county)
        col = matrix[county]
        na_mask = col.isna()
        if not na_mask.any():
            continue
        for date in col.index[na_mask]:
            value = None
            if region is not None:
                try:
                    value = region_lookup.loc[(date, region)]
                except KeyError:
                    value = None
            if value is None or pd.isna(value):
                try:
                    value = global_lookup.loc[date]
                    fallback_global.append([date.strftime("%Y-%m-%d"), county])
                except KeyError:
                    value = None
            else:
                fallback_region.append([date.strftime("%Y-%m-%d"), county])
            if value is not None and not pd.isna(value):
                matrix.at[date, county] = float(value)

    cells_still_missing = int(matrix.isna().sum().sum())

    output_path = folder / output_filename
    matrix_for_csv = matrix.copy()
    matrix_for_csv.index = matrix_for_csv.index.strftime("%Y-%m-%d")
    matrix_for_csv.index.name = "date"
    matrix_for_csv.to_csv(output_path, encoding="utf-8")

    cells_from_county = cells_total - len(fallback_region) - len(fallback_global) - cells_still_missing

    metadata = {
        "csv_file": csv_path.name,
        "output_csv": output_path.name,
        "metadata_file": metadata_filename,
        "variable": "wind_speed_Rff1_ms",
        "units": "m/s",
        "stage_a_reduction": "mean of valid Rff1 per (station, calendar_day)",
        "shape": list(matrix.shape),
        "date_range": [
            matrix.index.min().strftime("%Y-%m-%d"),
            matrix.index.max().strftime("%Y-%m-%d"),
        ],
        "counties": list(matrix.columns),
        "fill_window_days": fill_window_days,
        "station_fill_stats": {
            "hourly_rows_total": hourly_rows_total,
            "hourly_rows_sentinel": hourly_rows_sentinel,
            "station_day_cells_total": station_day_cells_total,
            "station_day_cells_with_data": station_day_cells_with_data,
            "station_day_missing_before_fill": missing_total,
            "station_day_filled": missing_total - still_missing,
            "station_day_still_missing": still_missing,
        },
        "matrix_fill_stats": {
            "cells_total": cells_total,
            "cells_from_county_mean": cells_from_county,
            "cells_filled_by_region": len(fallback_region),
            "cells_filled_by_global": len(fallback_global),
            "cells_still_missing": cells_still_missing,
        },
        "fallback_cells": {
            "region": fallback_region,
            "global": fallback_global,
        },
        "unmapped_stations": unmapped_stations,
    }

    metadata_path = folder / metadata_filename
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Built county-day wind matrix from {csv_path.name}")
    print(f"  Shape: {matrix.shape[0]} days x {matrix.shape[1]} counties")
    print(f"  Date range: {metadata['date_range'][0]} .. {metadata['date_range'][1]}")
    print(f"  Hourly rows: {hourly_rows_total} ({hourly_rows_sentinel} sentinel)")
    print(f"  (station, day) cells: {station_day_cells_total} "
          f"({station_day_cells_with_data} with data after stage A)")
    print(f"  Day-axis neighbour fill: {missing_total} -> {still_missing}")
    print(f"  Matrix cells: {cells_total} total, "
          f"{cells_from_county} from county aggregation, "
          f"{len(fallback_region)} from region fallback, "
          f"{len(fallback_global)} from global fallback, "
          f"{cells_still_missing} unfilled")
    print(f"Wrote {output_path}")
    print(f"Wrote {metadata_path}")

    return metadata


def build_county_daily_nebulosity_csv(
    date_folder: str = "date",
    hourly_csv_glob: str = "SirDate_*.csv",
    regions_filename: str = "stations_by_region.json",
    fill_window_days: int = 3,
    sentinel: float = -999.0,
    obscured_value: int = 9,
    output_filename: str = "daily_county_nebulosity.csv",
    metadata_filename: str = "daily_county_nebulosity_metadata.json",
    station_column: str = "Denumire",
    datetime_column: str = "Data masurarii",
    nop_column: str = "Nop",
) -> dict:
    """
    Build the (T, C) county-day mean-nebulosity matrix from the hourly
    SirDate CSV (Nop, WMO 2700 octa scale). Two-stage pipeline:

        STAGE A: hourly -> (station, day) mean in [0, 8]
            -> coerce Nop to numeric (the "/" string sentinel becomes NaN
               under pd.to_numeric(errors='coerce'))
            -> mask `sentinel` (default -999) -> NaN
            -> mask `obscured_value` (default 9 = WMO "sky obscured /
               cannot be estimated") -> NaN  (semantically not 9 oktas
               of cloud; it's an unobservable-sky state)
            -> mean of remaining valid 0..8 readings per (station,
               calendar_day). Continuous float, more informative for
               regression than the discrete mode used by the LLM-prompt
               pipeline.

        STAGE B: (station, day) -> (county, day) wide matrix
            -> station-level day-axis neighbour fill (±fill_window_days)
            -> per-county daily mean across stations
            -> region/global fallback

    Output CSV stores RAW mean nebulosity in [0, 8] octas; per-county
    z-score normalisation happens at training time.

    Args:
        date_folder: Folder holding inputs and outputs.
        hourly_csv_glob: Glob for the hourly SirDate CSV.
        regions_filename: JSON file mapping station to region/county.
        fill_window_days: Half-width N of the day-axis station-level fill.
        sentinel: Numeric sentinel marking missing values (default -999).
        obscured_value: Nop value treated as missing rather than
            measured (default 9; the WMO 2700 'sky obscured' code).
            Pass a non-existent value (e.g. -1) to keep 9 as a
            legitimate reading.
        output_filename: Wide CSV filename inside `date_folder`.
        metadata_filename: Companion JSON filename inside `date_folder`.
        station_column, datetime_column, nop_column: column names in
            the hourly CSV.

    Returns:
        Same shape as build_county_daily_wind_csv's metadata return,
        with `variable` set to "nebulosity_Nop_oktas", "units" to
        "oktas (0=clear, 8=overcast; 9 obscured filtered as missing)",
        and `station_fill_stats` extended with a `hourly_rows_obscured`
        counter for transparency.
    """
    import json

    folder = Path(date_folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"date folder not found: {folder.resolve()}")

    candidates = sorted(folder.glob(hourly_csv_glob))
    if not candidates:
        raise FileNotFoundError(
            f"no CSV matching '{hourly_csv_glob}' in {folder.resolve()}"
        )
    if len(candidates) > 1:
        raise RuntimeError(
            f"ambiguous hourly CSV: {[p.name for p in candidates]}; "
            f"narrow --hourly_csv_glob"
        )
    csv_path = candidates[0]

    regions_path = folder / regions_filename
    station_to_region, station_to_county = _load_station_metadata(regions_path)

    # --- STAGE A: hourly -> (station, day) ---
    df = pd.read_csv(
        csv_path, encoding="utf-8",
        usecols=[station_column, datetime_column, nop_column],
    )
    df[datetime_column] = pd.to_datetime(df[datetime_column])
    df["_date"] = df[datetime_column].dt.normalize()

    hourly_rows_total = len(df)
    # `pd.to_numeric` with errors='coerce' turns the "/" string sentinel
    # and any other non-numeric values into NaN. We track the count
    # before/after for the audit trail.
    nop_numeric = pd.to_numeric(df[nop_column], errors="coerce")
    hourly_rows_string_sentinel = int(
        nop_numeric.isna().sum() - df[nop_column].isna().sum()
    )
    df[nop_column] = nop_numeric

    hourly_rows_neg_sentinel = int((df[nop_column] == sentinel).sum())
    df[nop_column] = df[nop_column].mask(df[nop_column] == sentinel)
    hourly_rows_obscured = int((df[nop_column] == obscured_value).sum())
    df[nop_column] = df[nop_column].mask(df[nop_column] == obscured_value)

    station_day = (
        df.groupby([station_column, "_date"])[nop_column]
        .mean().reset_index()
    )

    station_day_cells_total = len(station_day)
    station_day_cells_with_data = int(station_day[nop_column].notna().sum())
    missing_total = station_day_cells_total - station_day_cells_with_data

    # --- STAGE B: (station, day) -> (county, day) wide matrix ---
    station_day = station_day.sort_values([station_column, "_date"]).reset_index(drop=True)
    station_day = _neighbour_fill(
        station_day, columns=[nop_column],
        group_column=station_column, fill_window_days=fill_window_days,
    )
    still_missing = int(station_day[nop_column].isna().sum())

    station_day["_county"] = station_day[station_column].map(station_to_county)
    station_day["_region"] = station_day[station_column].map(station_to_region)

    unmapped_stations = sorted({
        str(s) for s in station_day.loc[station_day["_county"].isna(), station_column].unique()
        if pd.notna(s)
    })
    sd_mapped = station_day.dropna(subset=["_county", nop_column]).copy()

    county_day = (
        sd_mapped.groupby(["_date", "_county"])[nop_column]
        .mean().rename("nebulosity_oktas").reset_index()
    )
    region_day = (
        sd_mapped.groupby(["_date", "_region"])[nop_column]
        .mean().rename("region_mean").reset_index()
    )
    global_day = (
        sd_mapped.groupby(["_date"])[nop_column]
        .mean().rename("global_mean").reset_index()
    )

    matrix = county_day.pivot(index="_date", columns="_county", values="nebulosity_oktas")
    matrix = matrix.sort_index()
    matrix.columns = [str(c) for c in matrix.columns]
    matrix = matrix.reindex(sorted(matrix.columns), axis=1)

    county_to_region = {}
    for region, counties in json.load(
        open(regions_path, "r", encoding="utf-8")
    )["stations_by_region"].items():
        for county in counties:
            county_to_region[str(county)] = str(region)

    region_lookup = region_day.set_index(["_date", "_region"])["region_mean"]
    global_lookup = global_day.set_index("_date")["global_mean"]

    fallback_region: list = []
    fallback_global: list = []
    cells_total = matrix.size

    for county in matrix.columns:
        region = county_to_region.get(county)
        col = matrix[county]
        na_mask = col.isna()
        if not na_mask.any():
            continue
        for date in col.index[na_mask]:
            value = None
            if region is not None:
                try:
                    value = region_lookup.loc[(date, region)]
                except KeyError:
                    value = None
            if value is None or pd.isna(value):
                try:
                    value = global_lookup.loc[date]
                    fallback_global.append([date.strftime("%Y-%m-%d"), county])
                except KeyError:
                    value = None
            else:
                fallback_region.append([date.strftime("%Y-%m-%d"), county])
            if value is not None and not pd.isna(value):
                matrix.at[date, county] = float(value)

    cells_still_missing = int(matrix.isna().sum().sum())

    output_path = folder / output_filename
    matrix_for_csv = matrix.copy()
    matrix_for_csv.index = matrix_for_csv.index.strftime("%Y-%m-%d")
    matrix_for_csv.index.name = "date"
    matrix_for_csv.to_csv(output_path, encoding="utf-8")

    cells_from_county = cells_total - len(fallback_region) - len(fallback_global) - cells_still_missing

    metadata = {
        "csv_file": csv_path.name,
        "output_csv": output_path.name,
        "metadata_file": metadata_filename,
        "variable": "nebulosity_Nop_oktas",
        "units": "oktas (0=clear, 8=overcast; 9 obscured filtered as missing)",
        "stage_a_reduction": "mean of valid Nop in {0..8} per (station, calendar_day)",
        "obscured_value": obscured_value,
        "shape": list(matrix.shape),
        "date_range": [
            matrix.index.min().strftime("%Y-%m-%d"),
            matrix.index.max().strftime("%Y-%m-%d"),
        ],
        "counties": list(matrix.columns),
        "fill_window_days": fill_window_days,
        "station_fill_stats": {
            "hourly_rows_total": hourly_rows_total,
            "hourly_rows_string_sentinel_(coerced_to_NaN)": hourly_rows_string_sentinel,
            "hourly_rows_neg_sentinel": hourly_rows_neg_sentinel,
            "hourly_rows_obscured": hourly_rows_obscured,
            "station_day_cells_total": station_day_cells_total,
            "station_day_cells_with_data": station_day_cells_with_data,
            "station_day_missing_before_fill": missing_total,
            "station_day_filled": missing_total - still_missing,
            "station_day_still_missing": still_missing,
        },
        "matrix_fill_stats": {
            "cells_total": cells_total,
            "cells_from_county_mean": cells_from_county,
            "cells_filled_by_region": len(fallback_region),
            "cells_filled_by_global": len(fallback_global),
            "cells_still_missing": cells_still_missing,
        },
        "fallback_cells": {
            "region": fallback_region,
            "global": fallback_global,
        },
        "unmapped_stations": unmapped_stations,
    }

    metadata_path = folder / metadata_filename
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Built county-day nebulosity matrix from {csv_path.name}")
    print(f"  Shape: {matrix.shape[0]} days x {matrix.shape[1]} counties")
    print(f"  Date range: {metadata['date_range'][0]} .. {metadata['date_range'][1]}")
    print(f"  Hourly rows: {hourly_rows_total} total")
    print(f"    string sentinel '/'  -> NaN: {hourly_rows_string_sentinel}")
    print(f"    neg sentinel {sentinel:g} -> NaN: {hourly_rows_neg_sentinel}")
    print(f"    obscured value {obscured_value} -> NaN: {hourly_rows_obscured}")
    print(f"  (station, day) cells: {station_day_cells_total} "
          f"({station_day_cells_with_data} with data after stage A)")
    print(f"  Day-axis neighbour fill: {missing_total} -> {still_missing}")
    print(f"  Matrix cells: {cells_total} total, "
          f"{cells_from_county} from county aggregation, "
          f"{len(fallback_region)} from region fallback, "
          f"{len(fallback_global)} from global fallback, "
          f"{cells_still_missing} unfilled")
    print(f"Wrote {output_path}")
    print(f"Wrote {metadata_path}")

    return metadata


def generate_stations_by_region(
    date_folder: str = "date",
    stations_csv: str = "statii_meteo.csv",
    source_csv_glob: str = "DateZilniceTemp_*.csv",
    output_filename: str = "stations_by_region.json",
    region_column: str = "regiune_CMR",
    judet_column: str = "judet_JU",
    wmo_column: str = "cod_wmo_CODST",
    name_column: str = "nume_NUME",
    source_station_column: str = "Denumire",
    source_code_column: str = "Cod sinoptic",
) -> dict:
    """
    Build `stations_by_region.json` by joining `statii_meteo.csv`
    (authoritative region assignments under `regiune_CMR`) to the
    measurement CSV via the WMO synoptic code, so that station keys in
    the output JSON match the station-name convention used in the
    measurement CSV.

    Join key:
        statii_meteo.cod_wmo_CODST  ==  source_csv['Cod sinoptic']

    Stations present in statii_meteo but with no matching code in the
    measurement CSV are dropped (they have no temperature data and
    would never surface in downstream analyses anyway); the dropped
    list is included in metadata for transparency.

    Per-station details (judet code, WMO code) are intentionally not
    duplicated into this JSON - they already live in `statii_meteo.csv`
    and `_load_station_metadata` reconstructs the (station -> region)
    and (station -> judet) mappings by walking the nested
    `stations_by_region` block, so a flat `station_details` table would
    be redundant.

    Args:
        date_folder: Folder holding both CSVs and the output JSON.
        stations_csv: Authoritative station+region CSV inside
            `date_folder`.
        source_csv_glob: Glob to locate the measurement CSV that defines
            the station-naming convention used downstream. Must match
            exactly one file.
        output_filename: Output JSON name inside `date_folder`.
        region_column, judet_column, wmo_column, name_column: column
            names in `stations_csv`.
        source_station_column, source_code_column: column names in the
            measurement CSV.

    Returns:
        {
            'metadata': {...},
            'counts_by_region': {region: int},
            'stations_by_region': {
                region: {
                    county_code: [station, ...],   # alphabetically sorted
                    ...
                },
                ...
            },
        }
    """
    import json

    folder = Path(date_folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"date folder not found: {folder.resolve()}")

    stations_path = folder / stations_csv
    if not stations_path.is_file():
        raise FileNotFoundError(f"stations CSV not found: {stations_path}")

    candidates = sorted(folder.glob(source_csv_glob))
    if not candidates:
        raise FileNotFoundError(
            f"no measurement CSV matching '{source_csv_glob}' in {folder.resolve()}"
        )
    if len(candidates) > 1:
        raise RuntimeError(
            f"ambiguous measurement CSV: {[p.name for p in candidates]}; "
            f"narrow --source_csv_glob"
        )
    source_path = candidates[0]

    stations_df = pd.read_csv(
        stations_path,
        encoding="utf-8",
        usecols=[wmo_column, region_column, judet_column, name_column],
    )
    source_df = pd.read_csv(
        source_path,
        encoding="utf-8",
        usecols=[source_station_column, source_code_column],
    ).drop_duplicates()

    # Reduce the source CSV to one row per (Denumire, Cod sinoptic) pair.
    source_pairs = (
        source_df.dropna(subset=[source_station_column, source_code_column])
        .assign(**{source_code_column: lambda d: d[source_code_column].astype(int)})
        .drop_duplicates()
    )

    stations_df = stations_df.dropna(subset=[wmo_column, region_column]).assign(
        **{wmo_column: lambda d: d[wmo_column].astype(int)}
    )

    merged = source_pairs.merge(
        stations_df, how="left",
        left_on=source_code_column, right_on=wmo_column,
    )

    unmapped_source = sorted(
        str(s).strip() for s in
        merged.loc[merged[region_column].isna(), source_station_column].unique()
        if str(s).strip()
    )

    matched = merged.dropna(subset=[region_column])

    source_codes = set(source_pairs[source_code_column].astype(int).unique())
    dropped_stations_csv_codes = sorted(set(stations_df[wmo_column]) - source_codes)
    dropped_stations_csv = stations_df.loc[
        stations_df[wmo_column].isin(dropped_stations_csv_codes),
        [wmo_column, name_column, region_column, judet_column],
    ].to_dict(orient="records")

    # Nested grouping: region -> county_code -> sorted [station, ...].
    # Stations without a county assignment fall under a "_unassigned"
    # bucket inside their region so they don't get silently dropped.
    counts_by_region: dict = {}
    stations_by_region: dict = {}
    total_stations = 0

    for _, row in matched.iterrows():
        station = str(row[source_station_column]).strip()
        region = str(row[region_column]).strip()
        judet = (
            str(row[judet_column]).strip()
            if pd.notna(row[judet_column]) and str(row[judet_column]).strip()
            else "_unassigned"
        )
        counts_by_region[region] = counts_by_region.get(region, 0) + 1
        stations_by_region.setdefault(region, {}).setdefault(judet, []).append(station)
        total_stations += 1

    for region, counties in stations_by_region.items():
        stations_by_region[region] = {
            county: sorted(set(stations)) for county, stations in sorted(counties.items())
        }
    counts_by_region = dict(sorted(counts_by_region.items()))
    stations_by_region = dict(sorted(stations_by_region.items()))

    result = {
        "metadata": {
            "stations_csv": stations_path.name,
            "source_csv": source_path.name,
            "region_column": region_column,
            "join_key": f"{wmo_column} == {source_code_column}",
            "total_stations": total_stations,
            "unmapped_source_stations": unmapped_source,
            "dropped_stations_csv_rows": dropped_stations_csv,
        },
        "counts_by_region": counts_by_region,
        "stations_by_region": stations_by_region,
    }

    output_path = folder / output_filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Built regions from {stations_path.name} joined to {source_path.name}")
    print(f"  Stations mapped: {total_stations}")
    print(f"  Counts by region (counties in parens):")
    for region, count in counts_by_region.items():
        county_count = len(stations_by_region[region])
        print(f"    {region}: {count} stations across {county_count} county/counties")
    if unmapped_source:
        print(f"  WARNING: {len(unmapped_source)} measurement-CSV station(s) had no "
              f"region in {stations_csv}: {unmapped_source[:5]}"
              f"{'...' if len(unmapped_source) > 5 else ''}")
    if dropped_stations_csv:
        print(f"  Dropped {len(dropped_stations_csv)} row(s) from {stations_csv} "
              f"with no matching measurement data "
              f"(WMO codes: {[r[wmo_column] for r in dropped_stations_csv]})")
    print(f"Wrote {output_path}")
    return result


def audit_station_monthly_coverage(
    date_folder: str = "date",
    csv_glob: str = "DateZilniceTemp_*.csv",
    station_column: str = "Denumire",
    date_column: str = "Data masurarii",
    include_partial_months: bool = False,
    output_filename: str = None,
) -> dict:
    """
    For each station, identify months where the station's daily registry
    is fully absent ("missing_months") versus months where at least one
    day is absent ("partially_missing_months", with the missing dates
    enumerated).

    "Missing" here means the (station, day) row does not appear in the
    CSV at all. Sentinel-valued readings (e.g. Tamax24 == -999) still
    count as present - this audit measures *registry* completeness, not
    measurement validity. Use `analyze_monthly_temperature` for the
    latter on the temperature CSV.

    Edge-month policy: by default, only months whose first and last
    calendar day both fall inside the CSV's observed date range are
    audited. Partial boundary months (e.g. when data starts on day 15)
    would otherwise flag every station as partially-missing for the
    same days, which is noise rather than signal. Pass
    `include_partial_months=True` to override.

    Args:
        date_folder: Folder containing the CSV.
        csv_glob: Glob to locate the CSV inside `date_folder`. Must
            match exactly one file.
        station_column: Column holding station names.
        date_column: Column holding the timestamp/date string. Parsed
            with pandas; only the date component is used (hourly CSVs
            collapse to one entry per (station, day)).
        include_partial_months: Include the dataset's boundary months
            even when they are not fully covered by the data range.
        output_filename: JSON output filename inside `date_folder`. If
            None, defaults to 'missing_dates_{year}.json' where {year}
            is the single year audited (e.g. '2024') or the range
            ('2024_2025') when months span multiple years.

    Returns:
        {
            'csv_file': str,
            'date_range': [str, str],          # YYYY-MM-DD min/max
            'months_audited': [str, ...],      # YYYY-MM
            'include_partial_months': bool,
            'summary': {
                'total_stations': int,
                'stations_with_missing_months': int,
                'stations_with_partial_months': int,
                'stations_with_no_gaps': int,
            },
            'per_station': {
                station: {
                    'missing_months': [str, ...],            # YYYY-MM
                    'partially_missing_months': {
                        'YYYY-MM': [str, ...],   # YYYY-MM-DD missing days
                        ...
                    },
                },
                ...
            },
        }
    """
    import json
    import calendar

    folder = Path(date_folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"date folder not found: {folder.resolve()}")

    candidates = sorted(folder.glob(csv_glob))
    if not candidates:
        raise FileNotFoundError(
            f"no CSV matching '{csv_glob}' in {folder.resolve()}"
        )
    if len(candidates) > 1:
        raise RuntimeError(
            f"ambiguous CSV: {[p.name for p in candidates]}; narrow --csv_glob"
        )
    csv_path = candidates[0]

    df = pd.read_csv(csv_path, encoding="utf-8", usecols=[station_column, date_column])
    df["_date"] = pd.to_datetime(df[date_column]).dt.normalize()

    min_date = df["_date"].min()
    max_date = df["_date"].max()

    # Determine the months to audit.
    candidate_months = sorted({(d.year, d.month) for d in df["_date"].unique()})
    if include_partial_months:
        months_audited_pairs = candidate_months
    else:
        # Keep only months whose calendar bounds are within [min_date, max_date].
        months_audited_pairs = [
            (y, m) for (y, m) in candidate_months
            if pd.Timestamp(y, m, 1) >= min_date
            and pd.Timestamp(y, m, calendar.monthrange(y, m)[1]) <= max_date
        ]
    months_audited = [f"{y:04d}-{m:02d}" for (y, m) in months_audited_pairs]

    # Build a {station: {(y, m): set(day_int)}} index of what's present.
    df["_year"] = df["_date"].dt.year
    df["_month"] = df["_date"].dt.month
    df["_day"] = df["_date"].dt.day
    present: dict = {}
    for station, sub in df.groupby(station_column):
        bucket: dict = {}
        for (y, m), days in sub.groupby(["_year", "_month"])["_day"]:
            bucket[(y, m)] = set(int(d) for d in days)
        present[str(station)] = bucket

    per_station: dict = {}
    n_full_gap = n_partial_gap = n_clean = 0
    for station in sorted(present.keys()):
        station_present = present[station]
        missing_months: list = []
        partial: dict = {}
        for (y, m) in months_audited_pairs:
            expected_days = set(range(1, calendar.monthrange(y, m)[1] + 1))
            actual_days = station_present.get((y, m), set())
            missing_days = expected_days - actual_days
            if not missing_days:
                continue
            if len(missing_days) == len(expected_days):
                missing_months.append(f"{y:04d}-{m:02d}")
            else:
                partial[f"{y:04d}-{m:02d}"] = [
                    f"{y:04d}-{m:02d}-{d:02d}" for d in sorted(missing_days)
                ]

        per_station[station] = {
            "missing_months": missing_months,
            "partially_missing_months": partial,
        }
        if missing_months and partial:
            n_full_gap += 1
            n_partial_gap += 1
        elif missing_months:
            n_full_gap += 1
        elif partial:
            n_partial_gap += 1
        else:
            n_clean += 1

    result = {
        "csv_file": csv_path.name,
        "date_range": [min_date.strftime("%Y-%m-%d"), max_date.strftime("%Y-%m-%d")],
        "months_audited": months_audited,
        "include_partial_months": include_partial_months,
        "summary": {
            "total_stations": len(per_station),
            "stations_with_missing_months": n_full_gap,
            "stations_with_partial_months": n_partial_gap,
            "stations_with_no_gaps": n_clean,
        },
        "per_station": per_station,
    }

    if output_filename:
        output_name = output_filename
    else:
        years_in_audit = sorted({int(m[:4]) for m in months_audited})
        if not years_in_audit:
            year_token = "empty"
        elif len(years_in_audit) == 1:
            year_token = str(years_in_audit[0])
        else:
            year_token = f"{years_in_audit[0]}_{years_in_audit[-1]}"
        output_name = f"missing_dates_{year_token}.json"
    output_path = folder / output_name
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Audited {csv_path.name}")
    print(f"  Date range: {result['date_range'][0]} .. {result['date_range'][1]}")
    print(f"  Months audited: {len(months_audited)} "
          f"({'partial boundary months included' if include_partial_months else 'full months only'})")
    print(f"  Stations: {result['summary']['total_stations']} total -> "
          f"{n_full_gap} with fully-missing month(s), "
          f"{n_partial_gap} with partially-missing month(s), "
          f"{n_clean} clean")
    print(f"Wrote report to {output_path}")

    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Data-quality utilities for the raw ANM CSV exports. "
            "Two subcommands: 'stations' audits station-name coverage "
            "across files; 'temperature' computes per-station and global "
            "monthly mean temperature with sentinel-cell fill from "
            "neighbouring days."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_stations = subparsers.add_parser(
        "stations",
        help="Audit station-name coverage across the CSV files in --date_folder.",
    )
    p_stations.add_argument("--date_folder", type=str, default="date",
                            help="Folder containing the raw CSV files (default: 'date').")
    p_stations.add_argument("--output_filename", type=str, default="station_coverage.json",
                            help="JSON report filename inside --date_folder.")
    p_stations.add_argument("--station_column", type=str, default="Denumire",
                            help="Column holding station names (default: 'Denumire').")
    p_stations.add_argument("--strict", action="store_true",
                            help="Exit 1 if any file is missing stations or any CSV failed to read.")

    p_temp = subparsers.add_parser(
        "temperature",
        help="Compute per-station and global monthly mean temperature.",
    )
    p_temp.add_argument("--month", type=str, required=True,
                        help="Target month, 'YYYY-MM' (e.g. '2024-03').")
    p_temp.add_argument("--fill_window_days", "-N", type=int, default=3,
                        help="Half-width N of the fill window. Missing cells are "
                             "filled with the mean of valid values in days t-N..t+N for "
                             "the same station (default: 3).")
    p_temp.add_argument("--date_folder", type=str, default="date",
                        help="Folder containing the temperature CSV (default: 'date').")
    p_temp.add_argument("--temp_csv_glob", type=str, default="DateZilniceTemp_*.csv",
                        help="Glob to locate the temperature CSV inside --date_folder. "
                             "Must match exactly one file.")
    p_temp.add_argument("--sentinel", type=float, default=-999.0,
                        help="Value treated as missing in the CSV (default: -999).")
    p_temp.add_argument("--regions_filename", type=str, default="stations_by_region.json",
                        help="JSON file inside --date_folder mapping stations to "
                             "regions (default: 'stations_by_region.json'). Pass '' "
                             "to disable per-region aggregation.")
    p_temp.add_argument("--output_filename", type=str, default=None,
                        help="JSON output filename (default: 'temperature_{month}.json').")

    p_reg = subparsers.add_parser(
        "regions",
        help="Build stations_by_region.json from statii_meteo.csv joined to "
             "the measurement CSV by WMO/synoptic code.",
    )
    p_reg.add_argument("--date_folder", type=str, default="date",
                       help="Folder holding both CSVs and the output JSON (default: 'date').")
    p_reg.add_argument("--stations_csv", type=str, default="statii_meteo.csv",
                       help="Authoritative station+region CSV (default: 'statii_meteo.csv').")
    p_reg.add_argument("--source_csv_glob", type=str, default="DateZilniceTemp_*.csv",
                       help="Glob for the measurement CSV whose station-naming "
                            "convention should drive the JSON keys "
                            "(default: 'DateZilniceTemp_*.csv').")
    p_reg.add_argument("--output_filename", type=str, default="stations_by_region.json",
                       help="Output JSON filename inside --date_folder.")
    p_reg.add_argument("--region_column", type=str, default="regiune_CMR",
                       help="Region column name in --stations_csv (default: 'regiune_CMR').")

    p_cov = subparsers.add_parser(
        "monthly_coverage",
        help="Audit per-station monthly completeness of one CSV.",
    )
    p_cov.add_argument("--date_folder", type=str, default="date",
                       help="Folder containing the CSV (default: 'date').")
    p_cov.add_argument("--csv_glob", type=str, default="DateZilniceTemp_*.csv",
                       help="Glob to locate the CSV inside --date_folder. "
                            "Must match exactly one file (default: "
                            "'DateZilniceTemp_*.csv').")
    p_cov.add_argument("--station_column", type=str, default="Denumire",
                       help="Column holding station names (default: 'Denumire').")
    p_cov.add_argument("--date_column", type=str, default="Data masurarii",
                       help="Column holding the date/timestamp (default: 'Data masurarii').")
    p_cov.add_argument("--include_partial_months", action="store_true",
                       help="Also audit boundary months whose calendar range is "
                            "not fully covered by the data range. Default skips "
                            "them to avoid flagging every station uniformly.")
    p_cov.add_argument("--output_filename", type=str, default=None,
                       help="JSON output filename (default: "
                            "'missing_dates_{year}.json'; year is derived "
                            "from the audited months).")

    p_mat = subparsers.add_parser(
        "county_matrix",
        help="Build the (T, C) daily county-mean temperature matrix used "
             "as the multivariate baseline input tensor.",
    )
    p_mat.add_argument("--date_folder", type=str, default="date",
                       help="Folder holding inputs and outputs (default: 'date').")
    p_mat.add_argument("--temp_csv_glob", type=str, default="DateZilniceTemp_*.csv",
                       help="Glob for the temperature CSV (default: 'DateZilniceTemp_*.csv').")
    p_mat.add_argument("--regions_filename", type=str, default="stations_by_region.json",
                       help="Regions JSON (default: 'stations_by_region.json').")
    p_mat.add_argument("--fill_window_days", "-N", type=int, default=3,
                       help="Half-width N of the station-level neighbour fill (default: 3).")
    p_mat.add_argument("--sentinel", type=float, default=-999.0,
                       help="Sentinel marking missing values (default: -999).")
    p_mat.add_argument("--output_filename", type=str, default="daily_county_mean.csv",
                       help="Wide CSV filename inside --date_folder.")
    p_mat.add_argument("--metadata_filename", type=str, default="daily_county_mean_metadata.json",
                       help="Companion JSON filename inside --date_folder.")

    p_prc = subparsers.add_parser(
        "county_precip",
        help="Build the (T, C) daily county-mean precipitation matrix "
             "(RAW R24 in mm) used as an auxiliary input channel for "
             "the multivariate baselines.",
    )
    p_prc.add_argument("--date_folder", type=str, default="date",
                       help="Folder holding inputs and outputs (default: 'date').")
    p_prc.add_argument("--precip_csv_glob", type=str, default="DateZilnicePrecip_*.csv",
                       help="Glob for the precipitation CSV (default: 'DateZilnicePrecip_*.csv').")
    p_prc.add_argument("--regions_filename", type=str, default="stations_by_region.json",
                       help="Regions JSON (default: 'stations_by_region.json').")
    p_prc.add_argument("--fill_window_days", "-N", type=int, default=3,
                       help="Half-width N of the station-level neighbour fill (default: 3).")
    p_prc.add_argument("--sentinel", type=float, default=-999.0,
                       help="Sentinel marking missing values (default: -999).")
    p_prc.add_argument("--date_shift_days", type=int, default=-1,
                       help="Shift each row's Data masurarii by this many "
                            "days before bucketing. Default -1 reflects "
                            "ANM's morning-observation convention: R24 "
                            "stamped at YYYY-MM-DD 05:30 is the 24h "
                            "accumulation ending that morning, i.e. the "
                            "rainfall that fell on (YYYY-MM-DD - 1 day). "
                            "Pass 0 to disable the shift.")
    p_prc.add_argument("--output_filename", type=str, default="daily_county_precip.csv",
                       help="Wide CSV filename inside --date_folder.")
    p_prc.add_argument("--metadata_filename", type=str,
                       default="daily_county_precip_metadata.json",
                       help="Companion JSON filename inside --date_folder.")

    p_wnd = subparsers.add_parser(
        "county_wind",
        help="Build the (T, C) daily county-mean wind matrix (Rff1, m/s) "
             "from the hourly SirDate CSV. Hourly readings are reduced "
             "to (station, calendar-day) means before the county pipeline.",
    )
    p_wnd.add_argument("--date_folder", type=str, default="date",
                       help="Folder holding inputs and outputs (default: 'date').")
    p_wnd.add_argument("--hourly_csv_glob", type=str, default="SirDate_*.csv",
                       help="Glob for the hourly CSV (default: 'SirDate_*.csv').")
    p_wnd.add_argument("--regions_filename", type=str, default="stations_by_region.json",
                       help="Regions JSON (default: 'stations_by_region.json').")
    p_wnd.add_argument("--fill_window_days", "-N", type=int, default=3,
                       help="Half-width N of the day-axis station-level fill (default: 3).")
    p_wnd.add_argument("--sentinel", type=float, default=-999.0,
                       help="Sentinel marking missing values (default: -999).")
    p_wnd.add_argument("--output_filename", type=str, default="daily_county_wind.csv",
                       help="Wide CSV filename inside --date_folder.")
    p_wnd.add_argument("--metadata_filename", type=str,
                       default="daily_county_wind_metadata.json",
                       help="Companion JSON filename inside --date_folder.")

    p_neb = subparsers.add_parser(
        "county_nebulosity",
        help="Build the (T, C) daily county-mean nebulosity matrix "
             "(Nop, WMO 2700 octas in [0, 8]) from the hourly SirDate "
             "CSV. The '/' string sentinel and the 9 obscured-sky "
             "code are filtered as missing.",
    )
    p_neb.add_argument("--date_folder", type=str, default="date",
                       help="Folder holding inputs and outputs (default: 'date').")
    p_neb.add_argument("--hourly_csv_glob", type=str, default="SirDate_*.csv",
                       help="Glob for the hourly CSV (default: 'SirDate_*.csv').")
    p_neb.add_argument("--regions_filename", type=str, default="stations_by_region.json",
                       help="Regions JSON (default: 'stations_by_region.json').")
    p_neb.add_argument("--fill_window_days", "-N", type=int, default=3,
                       help="Half-width N of the day-axis station-level fill (default: 3).")
    p_neb.add_argument("--sentinel", type=float, default=-999.0,
                       help="Numeric sentinel marking missing values (default: -999).")
    p_neb.add_argument("--obscured_value", type=int, default=9,
                       help="Nop value treated as missing rather than as a "
                            "valid 9-okta reading. Default 9 (WMO 'sky "
                            "obscured / not estimable'). Pass -1 to keep "
                            "9 as a legitimate measurement.")
    p_neb.add_argument("--output_filename", type=str, default="daily_county_nebulosity.csv",
                       help="Wide CSV filename inside --date_folder.")
    p_neb.add_argument("--metadata_filename", type=str,
                       default="daily_county_nebulosity_metadata.json",
                       help="Companion JSON filename inside --date_folder.")

    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.command == "stations":
        result = check_station_coverage(
            date_folder=args.date_folder,
            output_filename=args.output_filename,
            station_column=args.station_column,
        )
        if args.strict and not result["all_files_consistent"]:
            sys.exit(1)
    elif args.command == "temperature":
        analyze_monthly_temperature(
            month=args.month,
            date_folder=args.date_folder,
            temp_csv_glob=args.temp_csv_glob,
            fill_window_days=args.fill_window_days,
            sentinel=args.sentinel,
            regions_filename=args.regions_filename,
            output_filename=args.output_filename,
        )
    elif args.command == "regions":
        generate_stations_by_region(
            date_folder=args.date_folder,
            stations_csv=args.stations_csv,
            source_csv_glob=args.source_csv_glob,
            output_filename=args.output_filename,
            region_column=args.region_column,
        )
    elif args.command == "monthly_coverage":
        audit_station_monthly_coverage(
            date_folder=args.date_folder,
            csv_glob=args.csv_glob,
            station_column=args.station_column,
            date_column=args.date_column,
            include_partial_months=args.include_partial_months,
            output_filename=args.output_filename,
        )
    elif args.command == "county_matrix":
        build_county_daily_mean_csv(
            date_folder=args.date_folder,
            temp_csv_glob=args.temp_csv_glob,
            regions_filename=args.regions_filename,
            fill_window_days=args.fill_window_days,
            sentinel=args.sentinel,
            output_filename=args.output_filename,
            metadata_filename=args.metadata_filename,
        )
    elif args.command == "county_precip":
        build_county_daily_precip_csv(
            date_folder=args.date_folder,
            precip_csv_glob=args.precip_csv_glob,
            regions_filename=args.regions_filename,
            fill_window_days=args.fill_window_days,
            sentinel=args.sentinel,
            date_shift_days=args.date_shift_days,
            output_filename=args.output_filename,
            metadata_filename=args.metadata_filename,
        )
    elif args.command == "county_wind":
        build_county_daily_wind_csv(
            date_folder=args.date_folder,
            hourly_csv_glob=args.hourly_csv_glob,
            regions_filename=args.regions_filename,
            fill_window_days=args.fill_window_days,
            sentinel=args.sentinel,
            output_filename=args.output_filename,
            metadata_filename=args.metadata_filename,
        )
    elif args.command == "county_nebulosity":
        build_county_daily_nebulosity_csv(
            date_folder=args.date_folder,
            hourly_csv_glob=args.hourly_csv_glob,
            regions_filename=args.regions_filename,
            fill_window_days=args.fill_window_days,
            sentinel=args.sentinel,
            obscured_value=args.obscured_value,
            output_filename=args.output_filename,
            metadata_filename=args.metadata_filename,
        )

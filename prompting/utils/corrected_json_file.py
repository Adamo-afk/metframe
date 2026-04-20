import json
import copy

def process_meteorological_json(data):
    """
    Process meteorological JSON data by removing specific tags and modifying formatted_diagnosis.
    
    Parameters:
    data (dict): The input JSON data (can be a single day's data or full dataset)
    
    Returns:
    dict: Processed data with specified modifications
    """
    # Create a deep copy to avoid modifying the original data
    processed_data = copy.deepcopy(data)
    
    # Tags to remove
    tags_to_remove = ["interval", "pdf_path", "processing_timestamp"]
    
    # If data contains date keys (full dataset)
    if any(key for key in processed_data.keys() if key.count('-') == 2):
        # Process each date entry
        for date_key, date_data in processed_data.items():
            if isinstance(date_data, dict):
                # Remove unwanted tags
                for tag in tags_to_remove:
                    date_data.pop(tag, None)
                
                # Process formatted_diagnosis
                if "formatted_diagnosis" in date_data:
                    formatted_diag = date_data["formatted_diagnosis"]
                    if "PRIMA_PROPOZITIE" in formatted_diag:
                        # Keep only PRIMA_PROPOZITIE and add prefix
                        prima_content = formatted_diag["PRIMA_PROPOZITIE"]
                        date_data["formatted_diagnosis"] = {
                            "PRIMA_PROPOZITIE": f"PRIMA PROPOZIȚIE: {prima_content}"
                        }
                    else:
                        # If PRIMA_PROPOZITIE doesn't exist, remove formatted_diagnosis
                        date_data.pop("formatted_diagnosis", None)
    
    # If data is a single day's entry (no date keys)
    else:
        # Remove unwanted tags
        for tag in tags_to_remove:
            processed_data.pop(tag, None)
        
        # Process formatted_diagnosis
        if "formatted_diagnosis" in processed_data:
            formatted_diag = processed_data["formatted_diagnosis"]
            if "PRIMA_PROPOZITIE" in formatted_diag:
                # Keep only PRIMA_PROPOZITIE and add prefix
                prima_content = formatted_diag["PRIMA_PROPOZITIE"]
                processed_data["formatted_diagnosis"] = {
                    "PRIMA_PROPOZITIE": f"PRIMA PROPOZIȚIE: {prima_content}"
                }
            else:
                # If PRIMA_PROPOZITIE doesn't exist, remove formatted_diagnosis
                processed_data.pop("formatted_diagnosis", None)
    
    return processed_data

def process_json_file(input_file_path, output_file_path=None):
    """
    Process a JSON file and optionally save the result to a new file.
    
    Parameters:
    input_file_path (str): Path to the input JSON file
    output_file_path (str, optional): Path to save the processed JSON file
    
    Returns:
    dict: Processed data
    """
    # Read the JSON file
    with open(input_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Process the data
    processed_data = process_meteorological_json(data)
    
    # Save to file if output path is provided
    if output_file_path:
        with open(output_file_path, 'w', encoding='utf-8') as file:
            json.dump(processed_data, file, ensure_ascii=False, indent=2)
        print(f"Processed data saved to: {output_file_path}")
    
    return processed_data

# Example usage:
if __name__ == "__main__":
    input_path = "C:\\Users\\sateliti1\\Desktop\\Claudiu\\AI_disertatie\\formatted_diagnoses_2024\\formatted_diagnoses_2024.json"
    output_path = "C:\\Users\\sateliti1\\Desktop\\Claudiu\\AI_disertatie\\formatted_diagnoses_2024\\formatted_diagnoses_2024.json"
    processed = process_json_file(input_path, output_path)
    print(processed)
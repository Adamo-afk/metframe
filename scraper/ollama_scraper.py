import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

def scrape_ollama_model_page(url="https://ollama.com/library/llama3.1/tags"):
    """
    Scrapes the Ollama model page and extracts ALL model variant information
    """
    
    try:
        # Send GET request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract model information
        model_info = {
            'model_name': 'llama3.1',
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'variants': []
        }
        
        # Find the main title
        title = soup.find('h1')
        if title:
            model_info['full_title'] = title.text.strip()
        
        # Find download and update info
        stats_section = soup.find('div', string=re.compile(r'\d+\.?\d*[MK]?\s+Downloads'))
        if stats_section:
            model_info['stats'] = stats_section.text.strip()
        
        # Find description
        description = soup.find('meta', {'name': 'description'})
        if description:
            model_info['description'] = description.get('content', '')
        
        # Method 1: Look for all anchor tags that match model variant pattern
        all_links = soup.find_all('a', href=True)
        model_pattern = re.compile(r'/library/llama3\.1[:/].*')
        
        for link in all_links:
            href = link.get('href', '')
            if model_pattern.match(href):
                # Extract the model variant info from the link and its surrounding text
                variant_info = {
                    'href': href,
                    'name': href.split('/')[-1] if '/' in href else href,
                    'full_text': link.text.strip() if link.text else ''
                }
                
                # Try to extract structured information from the link's parent container
                parent = link.parent
                if parent:
                    # Look for size information (e.g., "3.7GB", "4.9GB")
                    size_match = re.search(r'(\d+\.?\d*)\s*(GB|MB|KB|TB)', parent.text)
                    if size_match:
                        variant_info['size'] = size_match.group(0)
                    
                    # Look for context window (e.g., "128K context")
                    context_match = re.search(r'(\d+[KM]?)\s*context', parent.text)
                    if context_match:
                        variant_info['context_window'] = context_match.group(1)
                    
                    # Look for parameter count (e.g., "8B", "70B", "405B")
                    param_match = re.search(r'(\d+\.?\d*)\s*B\s*parameter', parent.text)
                    if param_match:
                        variant_info['parameters'] = param_match.group(1) + 'B'
                    
                    # Look for time information (e.g., "11 months ago")
                    time_match = re.search(r'(\d+\s+(?:months?|days?|hours?|minutes?)\s+ago)', parent.text)
                    if time_match:
                        variant_info['last_updated'] = time_match.group(1)
                    
                    # Look for input/output type
                    if 'Text input' in parent.text:
                        variant_info['input_type'] = 'Text'
                    if 'Text output' in parent.text:
                        variant_info['output_type'] = 'Text'
                
                model_info['variants'].append(variant_info)
        
        # Method 2: Look for table rows or list items containing model variants
        # This handles cases where models might be in a table or list structure
        
        # Check for table structure
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                # Look for cells that might contain model info
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_text = ' '.join([cell.text.strip() for cell in cells])
                    
                    # Check if this row contains a model variant
                    if 'llama3.1' in row_text.lower():
                        variant = {
                            'source': 'table_row',
                            'raw_text': row_text
                        }
                        
                        # Extract specific fields from cells
                        if len(cells) >= 1:
                            variant['name'] = cells[0].text.strip()
                        if len(cells) >= 2:
                            variant['size'] = cells[1].text.strip()
                        if len(cells) >= 3:
                            variant['context'] = cells[2].text.strip()
                        if len(cells) >= 4:
                            variant['input'] = cells[3].text.strip()
                        
                        # Only add if we haven't already captured this variant
                        if not any(v.get('name') == variant.get('name') for v in model_info['variants']):
                            model_info['variants'].append(variant)
        
        # Method 3: Look for div containers with model information
        # Common patterns: div with class containing 'model', 'variant', 'tag', etc.
        model_divs = soup.find_all('div', class_=re.compile(r'(model|variant|tag)', re.I))
        for div in model_divs:
            div_text = div.text.strip()
            if 'llama3.1' in div_text.lower():
                # Extract model name from the div
                model_name_match = re.search(r'llama3\.1[:\-]?[\w\-_\.]+', div_text, re.I)
                if model_name_match:
                    variant = {
                        'source': 'div_container',
                        'name': model_name_match.group(0),
                        'raw_text': div_text[:500]  # Limit text length
                    }
                    
                    # Extract additional metadata
                    size_match = re.search(r'(\d+\.?\d*)\s*(GB|MB|KB|TB)', div_text)
                    if size_match:
                        variant['size'] = size_match.group(0)
                    
                    context_match = re.search(r'(\d+[KM]?)\s*context', div_text)
                    if context_match:
                        variant['context_window'] = context_match.group(1)
                    
                    # Check if not duplicate
                    if not any(v.get('name') == variant.get('name') for v in model_info['variants']):
                        model_info['variants'].append(variant)
        
        # Remove duplicates based on name or href
        seen = set()
        unique_variants = []
        for variant in model_info['variants']:
            identifier = variant.get('name') or variant.get('href', '')
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique_variants.append(variant)
        
        model_info['variants'] = unique_variants
        
        # Sort variants by name for better readability
        model_info['variants'].sort(key=lambda x: x.get('name', x.get('href', '')))
        
        # Extract any code blocks (installation instructions)
        code_blocks = soup.find_all(['code', 'pre'])
        if code_blocks:
            model_info['code_examples'] = []
            for code in code_blocks[:10]:
                code_text = code.text.strip()
                if code_text and len(code_text) > 5:  # Filter out empty or very short snippets
                    model_info['code_examples'].append(code_text)
        
        # Summary statistics
        model_info['total_variants_found'] = len(model_info['variants'])
        
        return model_info
        
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return None
    except Exception as e:
        print(f"Error parsing the page: {e}")
        import traceback
        traceback.print_exc()
        return None

def print_model_info(model_info):
    """
    Pretty print the extracted model information
    """
    if not model_info:
        print("No data to display")
        return
    
    print("=" * 80)
    print(f"MODEL: {model_info.get('model_name', 'Unknown')}")
    print(f"Scraped at: {model_info.get('scraped_at', 'Unknown time')}")
    print("=" * 80)
    
    if 'full_title' in model_info:
        print(f"Full Title: {model_info['full_title']}")
    
    if 'description' in model_info:
        print(f"\nDescription: {model_info['description']}")
    
    if 'stats' in model_info:
        print(f"\nStats: {model_info['stats']}")
    
    print(f"\n{'-' * 40}")
    print(f"MODEL VARIANTS ({model_info.get('total_variants_found', 0)} found):")
    print(f"{'-' * 40}")
    
    if model_info.get('variants'):
        for i, variant in enumerate(model_info['variants'], 1):
            print(f"\n{i}. Model: {variant.get('name', variant.get('href', 'Unknown'))}")
            
            # Print all available fields
            exclude_fields = {'name', 'href', 'raw_text', 'full_text', 'source'}
            for key, value in variant.items():
                if key not in exclude_fields and value:
                    print(f"   {key.replace('_', ' ').title()}: {value}")
            
            # If we have href, show it
            if 'href' in variant:
                print(f"   URL: {variant['href']}")
    else:
        print("No variants found - the page structure might have changed.")
    
    if model_info.get('code_examples'):
        print(f"\n{'-' * 40}")
        print("CODE EXAMPLES:")
        print(f"{'-' * 40}")
        for i, code in enumerate(model_info['code_examples'], 1):
            print(f"\n{i}. {code[:200]}...")  # Show first 200 chars

def save_to_json(model_info, filename="ollama_model_data.json"):
    """
    Save the extracted data to a JSON file
    """
    if model_info:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(model_info, f, indent=2, ensure_ascii=False)
        print(f"\nData saved to {filename}")

def save_to_csv(model_info, filename="ollama_model_variants.csv"):
    """
    Save the model variants to a CSV file for easy analysis
    """
    import csv
    
    if model_info and model_info.get('variants'):
        # Collect all unique keys from all variants
        all_keys = set()
        for variant in model_info['variants']:
            all_keys.update(variant.keys())
        
        # Remove keys we don't want in CSV
        all_keys.discard('raw_text')
        all_keys.discard('full_text')
        all_keys = sorted(all_keys)
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            
            for variant in model_info['variants']:
                # Create row with only the keys we want
                row = {k: variant.get(k, '') for k in all_keys}
                writer.writerow(row)
        
        print(f"CSV data saved to {filename}")

if __name__ == "__main__":
    # Scrape the page
    print("Starting comprehensive web scraper for Ollama llama3.1 page...")
    print("=" * 80)
    
    url = "https://ollama.com/library/llama3.1/tags"
    
    # Get the data
    model_data = scrape_ollama_model_page(url)
    
    if model_data:
        # Print the information
        print_model_info(model_data)
        
        # Save to JSON file
        save_to_json(model_data)
        
        # Save to CSV file for easy viewing in Excel/Google Sheets
        save_to_csv(model_data)
        
        print("\n" + "=" * 80)
        print(f"Scraping completed! Found {model_data.get('total_variants_found', 0)} model variants.")
        print("Data saved to:")
        print("  - ollama_model_data.json (complete data)")
        print("  - ollama_model_variants.csv (variants table)")
    else:
        print("Failed to scrape the page. Please check the URL and your internet connection.")
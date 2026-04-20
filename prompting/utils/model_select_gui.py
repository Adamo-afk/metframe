import requests
from bs4 import BeautifulSoup
import re
import json
import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from pathlib import Path
import subprocess
import psutil
import GPUtil

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ModelVariant:
    name: str
    size: str
    context: str
    input_type: str
    size_bytes: int = 0
    fits_in_memory: bool = False

@dataclass
class ModelInfo:
    name: str
    description: str
    variants: List[ModelVariant]
    url: str

class OllamaModelCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.available_memory = self.get_available_gpu_memory()
    
    def get_available_gpu_memory(self) -> int:
        """Get available GPU memory in bytes."""
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                # Use the first GPU's free memory
                gpu = gpus[0]
                free_memory_mb = gpu.memoryFree
                return free_memory_mb * 1024 * 1024  # Convert to bytes
            else:
                logger.warning("No GPU detected, using system RAM estimate")
                # Fallback to system RAM (use 50% as conservative estimate)
                ram = psutil.virtual_memory()
                return int(ram.available * 0.5)
        except Exception as e:
            logger.warning(f"Could not detect GPU memory: {e}. Using system RAM estimate.")
            try:
                ram = psutil.virtual_memory()
                return int(ram.available * 0.5)
            except:
                return 8 * 1024 * 1024 * 1024  # 8GB default fallback
    
    def parse_model_size(self, size_str: str) -> int:
        """Convert size string (like '4.7GB', '24GB', '5.2GB') to bytes."""
        if not size_str or size_str.lower() == 'unknown':
            return 0
        
        size_str = size_str.upper().strip()
        
        # Handle different size formats from Ollama
        if 'GB' in size_str:
            # Extract number before GB (handles formats like '4.7GB', '24GB')
            numbers = re.findall(r'[\d.]+', size_str)
            if numbers:
                number = float(numbers[0])
                return int(number * 1024 * 1024 * 1024)
        elif 'MB' in size_str:
            # Extract number before MB
            numbers = re.findall(r'[\d.]+', size_str)
            if numbers:
                number = float(numbers[0])
                return int(number * 1024 * 1024)
        elif 'KB' in size_str:
            # Extract number before KB
            numbers = re.findall(r'[\d.]+', size_str)
            if numbers:
                number = float(numbers[0])
                return int(number * 1024)
        elif 'B' in size_str and 'GB' not in size_str and 'MB' not in size_str and 'KB' not in size_str:
            # Handle parameter count like '7B', '13B' - estimate size
            numbers = re.findall(r'[\d.]+', size_str)
            if numbers:
                number = float(numbers[0])
                # Rough estimation: 1B parameters ≈ 2-4GB depending on precision
                estimated_gb = number * 2.5  # Conservative estimate
                return int(estimated_gb * 1024 * 1024 * 1024)
        
        return 0
    
    def crawl_popular_models(self, n: int) -> List[str]:
        """Crawl the Ollama search page to find n most popular models."""
        logger.info(f"Crawling Ollama search page for {n} most popular models...")
        
        try:
            response = self.session.get("https://ollama.com/search", timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find model links - these are typically in cards or list items
            model_links = []
            
            # Look for various possible selectors for model names/links
            possible_selectors = [
                'a[href*="/library/"]',
                '.model-card a',
                '.search-result a',
                'a[href^="/library/"]'
            ]
            
            for selector in possible_selectors:
                links = soup.select(selector)
                if links:
                    logger.info(f"Found {len(links)} model links using selector: {selector}")
                    break
            
            # Extract model names from URLs
            for link in links[:n]:
                href = link.get('href', '')
                if '/library/' in href:
                    model_name = href.split('/library/')[-1].split('/')[0]
                    if model_name and model_name not in model_links:
                        model_links.append(model_name)
            
            logger.info(f"Found {len(model_links)} popular models: {model_links}")
            return model_links[:n]
            
        except Exception as e:
            logger.error(f"Error crawling search page: {e}")
            # Fallback to some popular known models
            fallback_models = [
                'llama3.1', 'llama3', 'mistral', 'codellama', 'vicuna', 
                'orca-mini', 'wizard-coder', 'phi', 'neural-chat', 'starling-lm'
            ]
            logger.info(f"Using fallback models: {fallback_models[:n]}")
            return fallback_models[:n]
    
    def crawl_model_details(self, model_name: str) -> Optional[ModelInfo]:
        """Crawl model details page to get variants and information using the correct tags endpoint."""
        logger.info(f"Crawling details for model: {model_name}")
        
        try:
            # Use the /tags endpoint instead of the main model page - this is where the variants are listed!
            base_url = f"https://ollama.com/library/{model_name}"
            tags_url = f"{base_url}/tags"
            
            # First get the main page for description
            response = self.session.get(base_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            description = self.extract_description(soup)
            
            # Now get the tags page for the actual model variants
            logger.info(f"Fetching tags page: {tags_url}")
            tags_response = self.session.get(tags_url, timeout=30)
            tags_response.raise_for_status()
            
            tags_soup = BeautifulSoup(tags_response.content, 'html.parser')
            
            # Extract model variants using comprehensive methods from the tags page
            variants = self.extract_variants_from_tags_page(tags_soup, model_name)
            
            # If no variants were found, raise an error instead of creating fake ones
            if not variants:
                error_msg = f"No model variants found for {model_name}. Could not locate variants on the tags page."
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"Successfully found {len(variants)} variants for {model_name}")
            return ModelInfo(
                name=model_name,
                description=description,
                variants=variants,
                url=base_url
            )
            
        except Exception as e:
            logger.error(f"Error crawling model {model_name}: {e}")
            raise e
        
        finally:
            time.sleep(1)  # Be respectful to the server
    
    def extract_description(self, soup: BeautifulSoup) -> str:
        """Extract model description using multiple methods."""
        description = "No description available"
        
        # Method 1: Meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            desc_text = meta_desc.get('content', '')
            if desc_text and len(desc_text) > 20:
                description = desc_text[:300]
                return description
        
        # Method 2: Look for paragraphs with parameter information
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if any(keyword in text.lower() for keyword in ['parameter', 'model from', 'available in']):
                if len(text) > 20:
                    description = text[:300]
                    return description
        
        # Method 3: Look for title or header descriptions
        title = soup.find('h1')
        if title:
            parent = title.parent
            if parent:
                next_elem = title.find_next_sibling(['p', 'div'])
                if next_elem:
                    text = next_elem.get_text(strip=True)
                    if len(text) > 20:
                        description = text[:300]
        
        return description
    
    def extract_variants_from_tags_page(self, soup: BeautifulSoup, model_name: str) -> List[ModelVariant]:
        """Extract model variants from the tags page - this is where the real data is!"""
        variants = []
        
        # Method 1: Look for the main table with model variants
        logger.info("Extracting variants from tags page table...")
        
        # Find tables that contain model variant information
        tables = soup.find_all('table')
        for table in tables:
            # Look for table headers to confirm this is the variants table
            headers = table.find_all(['th', 'thead td'])
            if headers:
                header_texts = [h.get_text(strip=True).lower() for h in headers]
                logger.info(f"Found table with headers: {header_texts}")
                
                # Check if this table contains model variant headers
                if any(keyword in ' '.join(header_texts) for keyword in ['name', 'size', 'context', 'input']):
                    rows = table.find_all('tr')
                    
                    # Skip header row and process data rows
                    for row in rows[1:] if len(rows) > 1 else rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:  # At least name, size, context
                            try:
                                variant_name = cells[0].get_text(strip=True)
                                size = cells[1].get_text(strip=True)  
                                context = cells[2].get_text(strip=True) if len(cells) > 2 else "Unknown"
                                input_type = cells[3].get_text(strip=True) if len(cells) > 3 else "Text"
                                
                                # Skip header rows
                                if variant_name.lower() in ['name', 'tag', 'model']:
                                    continue
                                
                                # Better context extraction - look for common patterns
                                if context and context != "Unknown":
                                    # Clean up context field - look for patterns like "128k", "32k context", "4096 tokens"
                                    context_clean = self.clean_context_field(context)
                                    if context_clean:
                                        context = context_clean
                                
                                # If context is still unknown, try to find it in other cells or row text
                                if context == "Unknown" or not context:
                                    row_text = row.get_text()
                                    context_match = re.search(r'(\d+[KM]?)(?:\s*(?:context|tokens?|ctx))?', row_text, re.IGNORECASE)
                                    if context_match:
                                        context = context_match.group(1) + ("K" if not context_match.group(1).endswith(("K", "M")) else "")
                                
                                # Construct full model name
                                if ':' not in variant_name and variant_name:
                                    full_name = f"{model_name}:{variant_name}"
                                elif variant_name.startswith(model_name):
                                    full_name = variant_name
                                else:
                                    continue
                                
                                size_bytes = self.parse_model_size(size)
                                fits_memory = size_bytes <= self.available_memory if size_bytes > 0 else False
                                
                                variant = ModelVariant(
                                    name=full_name,
                                    size=size,
                                    context=context if context and context != "Unknown" else "128K",  # Default fallback
                                    input_type=input_type,
                                    size_bytes=size_bytes,
                                    fits_in_memory=fits_memory
                                )
                                variants.append(variant)
                                logger.info(f"Added variant: {full_name} ({size}, {context}, {input_type})")
                                
                            except Exception as e:
                                logger.warning(f"Error processing table row: {e}")
                                continue
        
        # Method 2: Look for div containers with model variant information (alternative structure)
        if not variants:
            logger.info("No table found, trying div-based extraction...")
            
            # Look for div containers that might contain model variants
            # Common patterns in Ollama pages
            variant_containers = soup.find_all('div', class_=re.compile(r'(card|item|row|variant|tag)', re.I))
            
            for container in variant_containers:
                container_text = container.get_text()
                
                # Check if this container has model variant information
                if model_name.lower() in container_text.lower() and any(size_indicator in container_text for size_indicator in ['GB', 'MB', 'B parameter']):
                    # Extract information from the container
                    lines = [line.strip() for line in container_text.split('\n') if line.strip()]
                    
                    # Look for patterns that indicate model variants
                    for i, line in enumerate(lines):
                        if model_name.lower() in line.lower():
                            variant_name = line.strip()
                            
                            # Try to extract size, context, and input from surrounding lines
                            size = "Unknown"
                            context = "128K"  # Default context
                            input_type = "Text"
                            
                            # Look in current and next few lines for size/context info
                            search_lines = lines[i:i+3] if i+3 <= len(lines) else lines[i:]
                            combined_text = ' '.join(search_lines)
                            
                            # Size extraction
                            size_match = re.search(r'(\d+\.?\d*)\s*(GB|MB|KB)', combined_text, re.IGNORECASE)
                            if size_match:
                                size = size_match.group(0)
                            
                            # Context extraction - look for multiple patterns
                            context_patterns = [
                                r'(\d+[KM]?)\s*(?:context|ctx|tokens?)',
                                r'context[:\s]*(\d+[KM]?)',
                                r'(\d+[KM]?)\s*token',
                                r'(\d+[KM]?)'  # Just numbers with K/M
                            ]
                            
                            for pattern in context_patterns:
                                context_match = re.search(pattern, combined_text, re.IGNORECASE)
                                if context_match:
                                    context = context_match.group(1)
                                    if not context.endswith(('K', 'M')):
                                        context += 'K'  # Add K if missing
                                    break
                            
                            # Construct full name
                            if ':' not in variant_name:
                                full_name = f"{model_name}:{variant_name.split()[-1]}"  # Take last word as tag
                            else:
                                full_name = variant_name
                            
                            size_bytes = self.parse_model_size(size)
                            fits_memory = size_bytes <= self.available_memory if size_bytes > 0 else False
                            
                            variant = ModelVariant(
                                name=full_name,
                                size=size,
                                context=context,
                                input_type=input_type,
                                size_bytes=size_bytes,
                                fits_in_memory=fits_memory
                            )
                            variants.append(variant)
                            logger.info(f"Added variant from div: {full_name} ({size}, {context})")
        
        # Method 3: Look for anchor links with variant information (from your original scraper)
        if not variants:
            logger.info("No structured data found, trying link-based extraction...")
            
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                
                # Look for links that point to model variants
                if f'/library/{model_name}' in href and ':' in href:
                    variant_text = link.get_text(strip=True)
                    
                    # Extract variant name from href
                    variant_match = re.search(rf'/library/{model_name}[:/]([^/\s]+)', href)
                    if variant_match:
                        variant_tag = variant_match.group(1)
                        full_name = f"{model_name}:{variant_tag}"
                        
                        # Try to extract size and context from the link's parent container
                        parent = link.parent
                        size = "Unknown"
                        context = "128K"  # Default context
                        
                        if parent:
                            parent_text = parent.get_text()
                            
                            # Extract size
                            size_match = re.search(r'(\d+\.?\d*)\s*(GB|MB|KB)', parent_text, re.IGNORECASE)
                            if size_match:
                                size = size_match.group(0)
                            
                            # Extract context with multiple patterns
                            context_patterns = [
                                r'(\d+[KM]?)\s*(?:context|ctx|tokens?)',
                                r'context[:\s]*(\d+[KM]?)',
                                r'(\d+[KM]?)\s*token',
                                r'(\d+)K',  # Just look for numbers followed by K
                                r'(\d+)M'   # Just look for numbers followed by M
                            ]
                            
                            for pattern in context_patterns:
                                context_match = re.search(pattern, parent_text, re.IGNORECASE)
                                if context_match:
                                    context = context_match.group(1)
                                    if not context.endswith(('K', 'M')):
                                        context += 'K'  # Add K if missing
                                    break
                        
                        size_bytes = self.parse_model_size(size)
                        fits_memory = size_bytes <= self.available_memory if size_bytes > 0 else False
                        
                        variant = ModelVariant(
                            name=full_name,
                            size=size,
                            context=context,
                            input_type="Text",
                            size_bytes=size_bytes,
                            fits_in_memory=fits_memory
                        )
                        variants.append(variant)
                        logger.info(f"Added variant from link: {full_name} ({size}, {context})")
        
        # Remove duplicates and return
        return self.deduplicate_model_variants(variants)
    
    def clean_context_field(self, context_text: str) -> str:
        """Clean and standardize context field values."""
        if not context_text or context_text.lower() in ['unknown', '-', '']:
            return None
            
        # Look for patterns like "128K", "32K", "4096", "128k context", etc.
        patterns = [
            r'(\d+[KM]?)(?:\s*(?:context|ctx|tokens?))?',
            r'(\d+)(?:\s*(?:context|ctx|tokens?))',
            r'context[:\s]*(\d+[KM]?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, context_text, re.IGNORECASE)
            if match:
                value = match.group(1)
                # Ensure it has K or M suffix for readability
                if value.isdigit():
                    # If it's a plain number, assume it's in thousands (K)
                    if int(value) >= 1000:
                        value = str(int(value) // 1000) + "K"
                    else:
                        value += "K"
                return value.upper()
        
        return None
    
    def extract_from_links(self, soup: BeautifulSoup, model_name: str) -> List[Dict]:
        """Extract variants from anchor tags (Method 1)."""
        variants = []
        
        # Look for links matching the model pattern
        all_links = soup.find_all('a', href=True)
        model_pattern = re.compile(rf'/library/{model_name}[:/].*')
        
        for link in all_links:
            href = link.get('href', '')
            if model_pattern.match(href):
                variant_name = href.split('/')[-1] if '/' in href else href.split(':')[-1]
                
                if ':' not in variant_name and variant_name:
                    full_name = f"{model_name}:{variant_name}"
                elif variant_name.startswith(model_name):
                    full_name = variant_name
                else:
                    continue
                    
                variant_info = {
                    'name': full_name,
                    'source': 'link'
                }
                
                # Extract information from the link's parent container
                parent = link.parent
                if parent:
                    parent_text = parent.get_text()
                    
                    # Extract size (e.g., "4.7GB", "24GB")
                    size_match = re.search(r'(\d+\.?\d*)\s*(GB|MB|KB|TB)', parent_text, re.IGNORECASE)
                    if size_match:
                        variant_info['size'] = size_match.group(0)
                    
                    # Extract context window (e.g., "128K context")  
                    context_match = re.search(r'(\d+[KM]?)\s*context', parent_text, re.IGNORECASE)
                    if context_match:
                        variant_info['context'] = context_match.group(1)
                    
                    # Extract input type
                    if re.search(r'text\s+input', parent_text, re.IGNORECASE):
                        variant_info['input_type'] = 'Text'
                
                variants.append(variant_info)
        
        return variants
    
    def extract_from_tables(self, soup: BeautifulSoup, model_name: str) -> List[Dict]:
        """Extract variants from table structures (Method 2).""" 
        variants = []
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            
            # Check if this looks like a variants table
            if len(rows) < 2:
                continue
                
            header_row = rows[0]
            header_text = ' '.join([cell.get_text(strip=True).lower() for cell in header_row.find_all(['th', 'td'])])
            
            # Skip if doesn't look like a model variants table
            if not any(keyword in header_text for keyword in ['name', 'size', 'context', 'tag']):
                continue
                
            logger.info(f"Found variants table with headers: {header_text}")
            
            # Process data rows
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    
                    variant_name = cells[0].get_text(strip=True)
                    
                    # Skip header rows
                    if variant_name.lower() in ['name', 'tag', 'model', 'variant', 'size']:
                        continue
                    
                    # Construct full model name
                    if variant_name and not variant_name.lower() == model_name.lower():
                        if ':' not in variant_name:
                            full_name = f"{model_name}:{variant_name}"
                        else:
                            full_name = variant_name
                            
                        variant_info = {
                            'name': full_name,
                            'source': 'table'
                        }
                        
                        # Extract information from cells
                        if len(cells) >= 2:
                            variant_info['size'] = cells[1].get_text(strip=True)
                        if len(cells) >= 3:
                            variant_info['context'] = cells[2].get_text(strip=True)
                        if len(cells) >= 4:
                            variant_info['input_type'] = cells[3].get_text(strip=True)
                        
                        variants.append(variant_info)
        
        return variants
    
    def extract_from_divs(self, soup: BeautifulSoup, model_name: str) -> List[Dict]:
        """Extract variants from div containers (Method 3)."""
        variants = []
        
        # Look for divs that might contain model information
        model_divs = soup.find_all('div', class_=re.compile(r'(model|variant|tag)', re.I))
        
        for div in model_divs:
            div_text = div.get_text()
            
            # Look for model name patterns
            model_pattern = re.compile(rf'{model_name}[:\-]?[\w\-_\.]+', re.IGNORECASE)
            matches = model_pattern.findall(div_text)
            
            for match in matches:
                if match and match.lower() != model_name.lower():
                    variant_info = {
                        'name': match if ':' in match else f"{model_name}:{match.split(model_name)[-1].lstrip(':-')}",
                        'source': 'div'
                    }
                    
                    # Extract size information
                    size_match = re.search(r'(\d+\.?\d*)\s*(GB|MB|KB|TB)', div_text, re.IGNORECASE)
                    if size_match:
                        variant_info['size'] = size_match.group(0)
                    
                    # Extract context information
                    context_match = re.search(r'(\d+[KM]?)\s*context', div_text, re.IGNORECASE)
                    if context_match:
                        variant_info['context'] = context_match.group(1)
                    
                    variants.append(variant_info)
        
        return variants
    
    def deduplicate_model_variants(self, variants: List[ModelVariant]) -> List[ModelVariant]:
        """Remove duplicate variants based on name."""
        seen = set()
        unique_variants = []
        
        for variant in variants:
            if variant.name and variant.name not in seen:
                seen.add(variant.name)
                unique_variants.append(variant)
        
        # Sort by name for consistency
        unique_variants.sort(key=lambda x: x.name)
        
        return unique_variants
    
    def crawl_all_models(self, n: int) -> List[ModelInfo]:
        """Crawl n most popular models and their details."""
        model_names = self.crawl_popular_models(n)
        model_infos = []
        failed_models = []
        
        for model_name in model_names:
            try:
                model_info = self.crawl_model_details(model_name)
                model_infos.append(model_info)
                logger.info(f"✓ Successfully crawled {model_name}")
            except Exception as e:
                logger.error(f"✗ Failed to crawl {model_name}: {e}")
                failed_models.append((model_name, str(e)))
                continue
        
        if failed_models:
            logger.warning(f"Failed to crawl {len(failed_models)} models:")
            for model_name, error in failed_models:
                logger.warning(f"  - {model_name}: {error}")
        
        if not model_infos:
            raise RuntimeError("Failed to crawl any models successfully. Please check your internet connection and try again.")
        
        logger.info(f"Successfully crawled {len(model_infos)} out of {len(model_names)} models")
        return model_infos

class ModelSelectionGUI:
    def __init__(self, models: List[ModelInfo]):
        self.models = models
        self.selected_variants = set()
        self.root = tk.Tk()
        self.root.title("Ollama Model Selection")
        self.root.geometry("1000x700")
        
        self.setup_gui()
        self.show_welcome_page()
    
    def setup_gui(self):
        """Set up the main GUI layout."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel (model list)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        ttk.Label(left_frame, text="Models", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Scrollable list for models
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.model_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, width=20)
        self.model_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.model_listbox.yview)
        
        # Populate model list
        for model in self.models:
            self.model_listbox.insert(tk.END, model.name)
        
        self.model_listbox.bind('<<ListboxSelect>>', self.on_model_select)
        
        # Right panel (model details)
        self.right_frame = ttk.Frame(main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Initialize tracking variables for the table interface
        self.variant_checkboxes = {}
        self.tree_variants = {}
        
        # Bottom panel (action buttons)
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(bottom_frame, text="Select Models", 
                  command=self.save_selected_models, 
                  style='Accent.TButton').pack(side=tk.RIGHT, padx=(10, 0))
        
        # Status label
        self.status_label = ttk.Label(bottom_frame, text=f"Available GPU Memory: {self.format_memory_size(self.get_available_memory())}")
        self.status_label.pack(side=tk.LEFT)
    
    def get_available_memory(self) -> int:
        """Get available memory for display purposes."""
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                return gpus[0].memoryFree * 1024 * 1024
            else:
                ram = psutil.virtual_memory()
                return int(ram.available * 0.5)
        except:
            return 8 * 1024 * 1024 * 1024
    
    def format_memory_size(self, size_bytes: int) -> str:
        """Format memory size for display."""
        if size_bytes >= 1024**3:
            return f"{size_bytes / (1024**3):.1f} GB"
        elif size_bytes >= 1024**2:
            return f"{size_bytes / (1024**2):.1f} MB"
        else:
            return f"{size_bytes} bytes"
    
    def show_welcome_page(self):
        """Show the welcome page."""
        for widget in self.right_frame.winfo_children():
            widget.destroy()
        
        welcome_frame = ttk.Frame(self.right_frame)
        welcome_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title = ttk.Label(welcome_frame, text="Welcome to Ollama Model Selection", 
                         font=('Arial', 16, 'bold'))
        title.pack(pady=(0, 20))
        
        welcome_text = """
This tool helps you select Ollama models for testing.

Instructions:
1. Browse the model list on the left
2. Click on any model to see its variants
3. Check the boxes next to variants you want to test
4. Models that fit in your available memory are marked with *
5. Click "Select Models" when done to save your selection

Your selections will be saved to 'models_to_test.txt' for use with the testing suite.
        """
        
        text_widget = tk.Text(welcome_frame, wrap=tk.WORD, height=15, 
                             font=('Arial', 11), relief=tk.FLAT, 
                             bg=self.root.cget('bg'))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, welcome_text.strip())
        text_widget.config(state=tk.DISABLED)
    
    def on_model_select(self, event):
        """Handle model selection from the list."""
        selection = self.model_listbox.curselection()
        if not selection:
            return
        
        model_idx = selection[0]
        model = self.models[model_idx]
        self.show_model_details(model)
    
    def show_model_details(self, model: ModelInfo):
        """Show details for a selected model using a table format."""
        for widget in self.right_frame.winfo_children():
            widget.destroy()
        
        # Main scrollable frame for model details
        canvas = tk.Canvas(self.right_frame)
        scrollbar = ttk.Scrollbar(self.right_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Model title and description
        title = ttk.Label(scrollable_frame, text=model.name, 
                         font=('Arial', 16, 'bold'))
        title.pack(pady=(10, 5), anchor='w')
        
        desc_frame = ttk.Frame(scrollable_frame)
        desc_frame.pack(fill=tk.X, pady=(0, 20), anchor='w')
        
        desc_text = tk.Text(desc_frame, wrap=tk.WORD, height=4, 
                           font=('Arial', 10), relief=tk.FLAT,
                           bg=self.root.cget('bg'))
        desc_text.pack(fill=tk.X)
        desc_text.insert(tk.END, model.description)
        desc_text.config(state=tk.DISABLED)
        
        # Variants section
        variants_title = ttk.Label(scrollable_frame, text="Model Variants", 
                                 font=('Arial', 12, 'bold'))
        variants_title.pack(pady=(10, 10), anchor='w')
        
        # Create table using Treeview
        table_frame = ttk.Frame(scrollable_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Define columns
        columns = ('Select', 'Model Name', 'Size', 'Context', 'Input', 'Memory')
        
        # Create Treeview with columns
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)
        
        # Configure column headings
        tree.heading('Select', text='Select')
        tree.heading('Model Name', text='Model Name')
        tree.heading('Size', text='Size')
        tree.heading('Context', text='Context')
        tree.heading('Input', text='Input Type')
        tree.heading('Memory', text='Fits Memory')
        
        # Configure column widths
        tree.column('Select', width=60, minwidth=50)
        tree.column('Model Name', width=200, minwidth=150)
        tree.column('Size', width=80, minwidth=60)
        tree.column('Context', width=80, minwidth=60)
        tree.column('Input', width=80, minwidth=60)
        tree.column('Memory', width=80, minwidth=60)
        
        # Store variant objects and checkbox states for each row
        self.variant_checkboxes = {}
        self.tree_variants = {}
        
        # Insert data rows
        for i, variant in enumerate(model.variants):
            # Determine if already selected
            is_selected = variant.name in self.selected_variants
            
            # Memory indicator
            memory_indicator = "*" if variant.fits_in_memory else ""
            
            # Insert row into treeview
            item_id = tree.insert('', 'end', values=(
                "☑" if is_selected else "☐",
                variant.name,
                variant.size,
                variant.context,
                variant.input_type,
                memory_indicator
            ))
            
            # Store variant reference for this tree item
            self.tree_variants[item_id] = variant
            self.variant_checkboxes[item_id] = is_selected
        
        # Add table scrollbar
        table_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=table_scrollbar.set)
        
        # Pack table and scrollbar
        tree.pack(side="left", fill="both", expand=True)
        table_scrollbar.pack(side="right", fill="y")
        
        # Bind click events for row selection
        tree.bind('<Button-1>', lambda event: self.on_table_click(event, tree))
        tree.bind('<Return>', lambda event: self.on_table_click(event, tree))
        tree.bind('<space>', lambda event: self.on_table_click(event, tree))
        
        # Pack main canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Also bind to the tree for better UX
        def _on_tree_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        tree.bind("<MouseWheel>", _on_tree_mousewheel)
    
    def on_table_click(self, event, tree):
        """Handle table row clicks to toggle selection."""
        # Identify the clicked item
        item = tree.identify('item', event.x, event.y)
        if not item:
            return
        
        # Get the variant for this item
        if item not in self.tree_variants:
            return
            
        variant = self.tree_variants[item]
        
        # Toggle selection state
        current_state = self.variant_checkboxes.get(item, False)
        new_state = not current_state
        self.variant_checkboxes[item] = new_state
        
        # Update the display
        if variant.fits_in_memory:
            # Update the global selected variants set
            if new_state:
                self.selected_variants.add(variant.name)
            else:
                self.selected_variants.discard(variant.name)
            current_values = list(tree.item(item, 'values'))
            current_values[0] = "☑" if new_state else "☐"
            tree.item(item, values=current_values)
        else:
            messagebox.showwarning("Memory Warning", f"Variant {variant.name} may not fit in memory.")
            return
        
        logger.info(f"{'Selected' if new_state else 'Deselected'} variant: {variant.name}")
        logger.info(f"Total selected variants: {len(self.selected_variants)}")
    
    def save_selected_models(self):
        """Save selected models to file and close GUI."""
        if not self.selected_variants:
            messagebox.showwarning("No Selection", "Please select at least one model variant.")
            return

        try:
            with open("models_to_test.txt", "w", encoding="utf-8") as f:
                for variant_name in sorted(self.selected_variants):
                    f.write(f"{variant_name}\n")
            
            messagebox.showinfo("Success", 
                              f"Successfully saved {len(self.selected_variants)} model variants to 'models_to_test.txt'")
            self.root.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save models: {e}")
    
    def run(self):
        """Start the GUI main loop."""
        self.root.mainloop()

def generate_gui(n_models: int = 10):
    """Main function to crawl models and show GUI."""
    logger.info(f"Starting Ollama model crawler for {n_models} popular models...")
    
    try:
        # Initialize crawler
        crawler = OllamaModelCrawler()
        
        # Show progress in console
        print("Crawling models... This may take a few minutes.")
        
        # Crawl models
        models = crawler.crawl_all_models(n_models)
        
        logger.info(f"Successfully crawled {len(models)} models")
        
        # Launch GUI
        logger.info("Launching model selection GUI...")
        gui = ModelSelectionGUI(models)
        gui.run()
        
        logger.info("Model selection completed!")
        
    except RuntimeError as e:
        logger.error(f"Critical error: {e}")
        print(f"\nError: {e}")
        print("Please check your internet connection and try again.")
        return
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\nUnexpected error occurred: {e}")
        return

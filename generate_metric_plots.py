import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from pathlib import Path
from datetime import datetime
import glob
from typing import List, Optional, Tuple

class ModelPerformanceVisualizer:
    """
    A comprehensive visualization system for model performance analysis
    across different dates and metrics.
    """
    
    def __init__(self, base_path: str = "AI_disertatie", output_path: str = "plots"):
        """
        Initialize the visualizer with base paths.
        """
        self.base_path = Path(base_path)
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)
        
        print(f"🔍 DEBUGGING PATH SETUP:")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Base path set to: {self.base_path}")
        print(f"Absolute base path: {self.base_path.resolve()}")
        print(f"Base path exists: {self.base_path.exists()}")
        
        if self.base_path.exists():
            print(f"Contents of base path:")
            for item in self.base_path.iterdir():
                print(f"  {'📁' if item.is_dir() else '📄'} {item.name}")
        else:
            print(f"❌ Base path does not exist!")
            print(f"Contents of current directory:")
            for item in Path('.').iterdir():
                print(f"  {'📁' if item.is_dir() else '📄'} {item.name}")
        
        # Available July 2024 dates
        self.july_dates = [
            "2024-07-05", "2024-07-10", "2024-07-15", 
            "2024-07-20", "2024-07-25", "2024-07-30"
        ]
        
        # Available metrics
        self.available_metrics = [
            'rouge1_f', 'rouge1_p', 'rouge1_r', 'rouge2_f', 'rouge2_p', 'rouge2_r',
            'rougeL_f', 'rougeL_p', 'rougeL_r', 'bleu', 'bert_precision', 
            'bert_recall', 'bert_f1', 'meteor', 'jaccard_similarity', 
            'reference_coverage', 'response_coverage'
        ]
    
    def auto_detect_base_path(self):
        """
        Try to automatically detect the correct base path.
        """
        print(f"\n🔍 AUTO-DETECTING BASE PATH:")
        
        # Try current directory first
        current_dir = Path('.')
        if (current_dir / 'results').exists():
            print(f"✓ Found 'results' directory in current location")
            self.base_path = current_dir
            return True
        
        # Try common base path names
        possible_paths = [
            Path('.'),
            Path('AI_disertatie'),
            Path('../AI_disertatie'),
            Path('../../AI_disertatie')
        ]
        
        for path in possible_paths:
            results_path = path / 'results'
            print(f"Checking: {results_path.resolve()}")
            if results_path.exists():
                print(f"✓ Found results directory at: {path.resolve()}")
                self.base_path = path
                return True
        
        print(f"❌ Could not auto-detect base path")
        return False
    
    def scan_actual_structure(self):
        """
        Scan what actually exists in the file system.
        """
        print(f"\n🔍 SCANNING ACTUAL FILE STRUCTURE:")
        print("="*60)
        
        # Check if we can find the results directory
        results_path = self.base_path / "results"
        print(f"Looking for results at: {results_path.resolve()}")
        print(f"Results directory exists: {results_path.exists()}")
        
        if not results_path.exists():
            print(f"\n❌ Results directory not found!")
            print(f"Trying auto-detection...")
            if self.auto_detect_base_path():
                results_path = self.base_path / "results"
            else:
                return
        
        print(f"\n📁 RESULTS DIRECTORY CONTENTS:")
        try:
            items = list(results_path.iterdir())
            if not items:
                print(f"  (empty)")
            else:
                for item in sorted(items):
                    if item.is_dir():
                        print(f"  📁 {item.name}/")
                        # Check what's inside each date folder
                        try:
                            sub_items = list(item.iterdir())
                            for sub_item in sub_items:
                                if sub_item.is_dir():
                                    print(f"    📁 {sub_item.name}/")
                                    # Check for CSV files in subdirectory
                                    csv_files = list(sub_item.glob("*.csv"))
                                    for csv_file in csv_files:
                                        print(f"      📄 {csv_file.name}")
                                else:
                                    print(f"    📄 {sub_item.name}")
                        except Exception as e:
                            print(f"    ❌ Error reading subdirectory: {e}")
                    else:
                        print(f"  📄 {item.name}")
        except Exception as e:
            print(f"❌ Error reading results directory: {e}")
        
        print("\n" + "="*60)
    
    def load_data_for_date(self, date: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Load both summary files for a specific date.
        """
        print(f"  🔍 Looking for data files for {date}...")
        
        # Build possible paths
        possible_paths = [
            self.base_path / "results" / date,
            self.base_path / "results" / date / "4_past_days"
        ]
        
        print(f"    Checking these paths:")
        for path in possible_paths:
            print(f"      {path.resolve()} -> {'EXISTS' if path.exists() else 'NOT FOUND'}")
        
        summary_by_model_df = None
        summary_by_past_days_df = None
        
        for path in possible_paths:
            if not path.exists():
                continue
                
            print(f"    ✓ Found directory: {path}")
            
            # Look for CSV files
            model_file = path / "summary_by_model.csv"
            days_file = path / "summary_by_past_days.csv"
            
            print(f"      summary_by_model.csv: {'EXISTS' if model_file.exists() else 'NOT FOUND'}")
            print(f"      summary_by_past_days.csv: {'EXISTS' if days_file.exists() else 'NOT FOUND'}")
            
            # List all files in this directory
            all_files = list(path.glob("*"))
            print(f"      All files in directory: {[f.name for f in all_files]}")
            
            # Try to load files
            if model_file.exists() and summary_by_model_df is None:
                try:
                    summary_by_model_df = pd.read_csv(model_file)
                    print(f"      ✓ Loaded summary_by_model.csv ({len(summary_by_model_df)} rows)")
                except Exception as e:
                    print(f"      ❌ Error loading model file: {e}")
            
            if days_file.exists() and summary_by_past_days_df is None:
                try:
                    summary_by_past_days_df = pd.read_csv(days_file)
                    print(f"      ✓ Loaded summary_by_past_days.csv ({len(summary_by_past_days_df)} rows)")
                except Exception as e:
                    print(f"      ❌ Error loading days file: {e}")
        
        return summary_by_model_df, summary_by_past_days_df
    
    def create_bubble_plot(self, data: pd.DataFrame, metric: str, date: str, save_path: Path):
        """Create annotated bubble plot showing model performance."""
        if data is None or metric not in data.columns:
            print(f"    ❌ Cannot create bubble plot: missing data or metric '{metric}'")
            return
        
        plt.figure(figsize=(12, 8))
        
        bubble_sizes = (data[metric] - data[metric].min() + 0.1) * 500
        colors = plt.cm.Set3(np.linspace(0, 1, len(data)))
        
        scatter = plt.scatter(
            range(len(data)), data[metric], s=bubble_sizes, c=colors,
            alpha=0.7, edgecolors='black', linewidth=1
        )
        
        for i, model in enumerate(data['model']):
            plt.annotate(
                model, (i, data[metric].iloc[i]),
                xytext=(5, 5), textcoords='offset points',
                fontsize=10, fontweight='bold'
            )
        
        plt.title(f'Model Performance Comparison - {metric}\n{date}', 
                 fontsize=16, fontweight='bold')
        plt.ylabel(f'{metric} Score', fontsize=12)
        plt.xlabel('Models', fontsize=12)
        plt.xticks(range(len(data)), data['model'], rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        plt.savefig(save_path / f'bubble_plot_{metric}_{date}.png', 
                   dpi=300, bbox_inches='tight')
        plt.close()
        print(f"    ✓ Bubble plot saved")
    
    def create_moving_average_plot(self, all_data: dict, metric: str, save_path: Path):
        """Create moving average plot for a metric across all July dates."""
        if not all_data:
            print("  ❌ No data available for moving average plot")
            return
        
        dates = []
        metric_values = []
        
        for date in sorted(all_data.keys()):
            if all_data[date] is not None and metric in all_data[date].columns:
                dates.append(datetime.strptime(date, '%Y-%m-%d'))
                metric_values.append(all_data[date][metric].mean())
        
        if len(dates) < 2:
            print(f"  ❌ Insufficient data for moving average plot")
            return
        
        plt.figure(figsize=(12, 8))
        
        window_size = min(3, len(metric_values))
        moving_avg = pd.Series(metric_values).rolling(window=window_size, center=True).mean()
        
        plt.plot(dates, metric_values, 'o-', label=f'Original {metric}', 
                linewidth=2, markersize=8, alpha=0.7)
        plt.plot(dates, moving_avg, 's-', label=f'Moving Average (window={window_size})', 
                linewidth=3, markersize=10)
        
        plt.title(f'Moving Average Trend - {metric}\nJuly 2024', 
                 fontsize=16, fontweight='bold')
        plt.ylabel(f'{metric} Score', fontsize=12)
        plt.xlabel('Date', fontsize=12)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        plt.savefig(save_path / f'moving_average_{metric}_july.png', 
                   dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Moving average plot saved")
    
    def create_evolution_plot(self, data: pd.DataFrame, metric: str, date: str, save_path: Path):
        """Create line plot showing evolution of performance from 1 to 4 past days."""
        if data is None or metric not in data.columns or 'past_days' not in data.columns:
            print(f"    ❌ Cannot create evolution plot: missing data or columns")
            return
        
        plt.figure(figsize=(12, 8))
        
        data_sorted = data.sort_values('past_days')
        
        plt.plot(data_sorted['past_days'], data_sorted[metric], 
                'o-', linewidth=3, markersize=10, color='blue', alpha=0.8)
        
        for i, (days, value) in enumerate(zip(data_sorted['past_days'], data_sorted[metric])):
            plt.annotate(f'{value:.4f}', (days, value),
                        xytext=(0, 10), textcoords='offset points',
                        ha='center', fontsize=11, fontweight='bold')
        
        plt.title(f'Performance Evolution by Past Days - {metric}\n{date}', 
                 fontsize=16, fontweight='bold')
        plt.ylabel(f'{metric} Score', fontsize=12)
        plt.xlabel('Past Days', fontsize=12)
        plt.xticks(data_sorted['past_days'])
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        plt.savefig(save_path / f'evolution_plot_{metric}_{date}.png', 
                   dpi=300, bbox_inches='tight')
        plt.close()
        print(f"    ✓ Evolution plot saved")
    
    def generate_all_plots(self, metric: str):
        """Generate all three types of plots for the specified metric."""
        if metric not in self.available_metrics:
            print(f"❌ '{metric}' not in available metrics.")
            return
        
        print(f"\n📊 GENERATING PLOTS FOR: {metric}")
        print("="*50)
        
        all_model_data = {}
        
        for date in self.july_dates:
            print(f"\n📅 Processing date: {date}")
            
            date_output_path = self.output_path / date
            date_output_path.mkdir(exist_ok=True)
            
            model_data, days_data = self.load_data_for_date(date)
            
            if model_data is not None:
                self.create_bubble_plot(model_data, metric, date, date_output_path)
                all_model_data[date] = model_data
            else:
                print(f"  ❌ No model data found for {date}")
            
            if days_data is not None:
                self.create_evolution_plot(days_data, metric, date, date_output_path)
            else:
                print(f"  ❌ No past days data found for {date}")
        
        if all_model_data:
            self.create_moving_average_plot(all_model_data, metric, self.output_path)
        else:
            print(f"  ❌ No data available for moving average plot")
        
        print(f"\n✅ All plots for '{metric}' completed!")
    
    def list_available_metrics(self):
        """Display all available metrics."""
        print("\n📋 AVAILABLE METRICS:")
        for i, metric in enumerate(self.available_metrics, 1):
            print(f"{i:2d}. {metric}")


def main():
    """Main function with comprehensive debugging."""
    print("🚀 STARTING MODEL PERFORMANCE VISUALIZER")
    print("="*60)
    
    # Initialize with debugging
    visualizer = ModelPerformanceVisualizer()
    
    # Scan the actual structure
    visualizer.scan_actual_structure()
    
    # Show available metrics
    visualizer.list_available_metrics()
    
    # Try to generate plots
    print(f"\n📊 GENERATING SAMPLE PLOTS...")
    important_metrics = ['rougeL_f', 'bleu', 'bert_f1', 'meteor', 'jaccard_similarity']
    for metric in important_metrics:
        visualizer.generate_all_plots(metric)

if __name__ == "__main__":
    main()
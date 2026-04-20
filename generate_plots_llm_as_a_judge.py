import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from pathlib import Path
from datetime import datetime
import glob
from typing import List, Optional, Tuple

class LLMJudgePerformanceVisualizer:
    """
    Visualization system for LLM-as-a-judge model performance analysis.
    """
    
    def __init__(self, base_path: str = None, output_path: str = "plots_llm_as_a_judge"):
        """
        Initialize the LLM judge visualizer.
        """
        print(f"🔍 CURRENT WORKING DIRECTORY: {os.getcwd()}")
        
        # Try to auto-detect the correct base path
        if base_path is None:
            self.base_path = self.auto_detect_base_path()
        else:
            self.base_path = Path(base_path)
        
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)
        
        # Available July 2024 dates
        self.july_dates = [
            "2024-07-05", "2024-07-10", "2024-07-15", 
            "2024-07-20", "2024-07-25", "2024-07-30"
        ]
        
        print(f"🎯 Base path set to: {self.base_path.resolve()}")
        print(f"📁 Output path: {self.output_path.resolve()}")
    
    def auto_detect_base_path(self) -> Path:
        """
        Try to automatically detect the correct base path.
        """
        print(f"\n🔍 AUTO-DETECTING BASE PATH...")
        
        # Possible base paths to try
        possible_paths = [
            Path("."),  # Current directory
            Path("AI_disertatie"),  # If running from parent
            Path(".."),  # If running from inside AI_disertatie
            Path("../.."),  # If running from deeper
            Path(r"C:\Users\sateliti1\Desktop\Claudiu\AI_disertatie"),  # Your exact path
            Path(r"C:\Users\sateliti1\Desktop\Claudiu"),  # Parent of your path
        ]
        
        for path in possible_paths:
            test_path = path / "llm_as_a_judge" / "gpt-5-mini"
            print(f"Trying: {test_path.resolve()} -> {'EXISTS' if test_path.exists() else 'NOT FOUND'}")
            
            if test_path.exists():
                print(f"✅ Found correct base path: {path.resolve()}")
                return path
        
        print(f"❌ Could not auto-detect base path. Using current directory.")
        return Path(".")
    
    def verify_file_exists(self, date: str) -> bool:
        """
        Verify if the CSV file exists for a given date.
        """
        csv_path = (self.base_path / "llm_as_a_judge" / "gpt-5-mini" / 
                   date / "4_past_days" / "analysis" / "average_scores_models_vs_past_days.csv")
        
        print(f"\n🔍 VERIFYING FILE FOR {date}:")
        print(f"Looking for: {csv_path.resolve()}")
        print(f"File exists: {'YES ✅' if csv_path.exists() else 'NO ❌'}")
        
        if not csv_path.exists():
            # Show what actually exists in each directory level
            print(f"\n📂 DIRECTORY STRUCTURE CHECK:")
            
            # Check base path
            if not self.base_path.exists():
                print(f"❌ Base path doesn't exist: {self.base_path.resolve()}")
                return False
            
            # Check llm_as_a_judge
            llm_path = self.base_path / "llm_as_a_judge"
            if not llm_path.exists():
                print(f"❌ llm_as_a_judge doesn't exist: {llm_path.resolve()}")
                print(f"Contents of base directory:")
                for item in self.base_path.iterdir():
                    print(f"  {'📁' if item.is_dir() else '📄'} {item.name}")
                return False
            
            # Check gpt-5-mini
            gpt_path = llm_path / "gpt-5-mini"
            if not gpt_path.exists():
                print(f"❌ gpt-5-mini doesn't exist: {gpt_path.resolve()}")
                print(f"Contents of llm_as_a_judge:")
                for item in llm_path.iterdir():
                    print(f"  {'📁' if item.is_dir() else '📄'} {item.name}")
                return False
            
            # Check date folder
            date_path = gpt_path / date
            if not date_path.exists():
                print(f"❌ Date folder doesn't exist: {date_path.resolve()}")
                print(f"Contents of gpt-5-mini:")
                for item in gpt_path.iterdir():
                    print(f"  {'📁' if item.is_dir() else '📄'} {item.name}")
                return False
            
            # Check 4_past_days
            past_days_path = date_path / "4_past_days"
            if not past_days_path.exists():
                print(f"❌ 4_past_days doesn't exist: {past_days_path.resolve()}")
                print(f"Contents of {date}:")
                for item in date_path.iterdir():
                    print(f"  {'📁' if item.is_dir() else '📄'} {item.name}")
                return False
            
            # Check analysis
            analysis_path = past_days_path / "analysis"
            if not analysis_path.exists():
                print(f"❌ analysis doesn't exist: {analysis_path.resolve()}")
                print(f"Contents of 4_past_days:")
                for item in past_days_path.iterdir():
                    print(f"  {'📁' if item.is_dir() else '📄'} {item.name}")
                return False
            
            # Check CSV file
            print(f"❌ CSV file doesn't exist: {csv_path.resolve()}")
            print(f"Contents of analysis:")
            for item in analysis_path.iterdir():
                print(f"  {'📁' if item.is_dir() else '📄'} {item.name}")
            return False
        
        return True
    
    def load_data_for_date(self, date: str) -> Optional[pd.DataFrame]:
        """
        Load the CSV data for a specific date.
        """
        if not self.verify_file_exists(date):
            return None
        
        csv_path = (self.base_path / "llm_as_a_judge" / "gpt-5-mini" / 
                   date / "4_past_days" / "analysis" / "average_scores_models_vs_past_days.csv")
        
        try:
            data = pd.read_csv(csv_path)
            print(f"✅ Successfully loaded data:")
            print(f"   Rows: {len(data)}")
            print(f"   Columns: {len(data.columns)}")
            print(f"   Column names: {list(data.columns)}")
            print(f"   Past days values: {sorted(data['past_days'].unique())}")
            return data
        except Exception as e:
            print(f"❌ Error loading CSV file: {e}")
            return None
    
    def create_all_models_plot(self, data: pd.DataFrame, date: str, save_path: Path):
        """
        Create plot showing all models' performance evolution.
        """
        plt.figure(figsize=(16, 10))
        
        # Get model columns (exclude 'past_days')
        model_columns = [col for col in data.columns if col != 'past_days']
        print(f"📊 Creating plot with {len(model_columns)} models")
        
        # Create distinct colors
        colors = plt.cm.tab20(np.linspace(0, 1, len(model_columns)))
        
        # Plot each model
        for i, model in enumerate(model_columns):
            # Clean model name for display
            clean_name = model.replace('_', ' ').replace('-', ' ')
            
            plt.plot(data['past_days'], data[model], 
                    'o-', linewidth=3, markersize=8, 
                    color=colors[i], alpha=0.8, 
                    label=clean_name)
            
            # Add value annotations
            for days, value in zip(data['past_days'], data[model]):
                plt.annotate(f'{value:.3f}', 
                           (days, value),
                           xytext=(0, 15), 
                           textcoords='offset points',
                           ha='center',
                           fontsize=9,
                           alpha=0.7,
                           color=colors[i],
                           fontweight='bold')
        
        plt.title(f'All LLM Models Performance Evolution\n{date}', 
                 fontsize=18, fontweight='bold', pad=20)
        plt.ylabel('Average Score', fontsize=14)
        plt.xlabel('Past Days', fontsize=14)
        plt.xticks(data['past_days'])
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save plot
        filename = f'all_models_evolution_{date}.png'
        plt.savefig(save_path / filename, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ Saved: {filename}")
    
    def create_top_models_plot(self, data: pd.DataFrame, date: str, save_path: Path):
        """
        Create plot showing top 5 models only.
        """
        model_columns = [col for col in data.columns if col != 'past_days']
        
        # Calculate average performance
        model_averages = {model: data[model].mean() for model in model_columns}
        
        # Get top 5
        top_models = sorted(model_averages.items(), key=lambda x: x[1], reverse=True)[:5]
        
        plt.figure(figsize=(12, 8))
        colors = plt.cm.viridis(np.linspace(0, 1, 5))
        
        for i, (model, avg_score) in enumerate(top_models):
            clean_name = model.replace('_', ' ').replace('-', ' ')
            
            plt.plot(data['past_days'], data[model], 
                    'o-', linewidth=4, markersize=10, 
                    color=colors[i], alpha=0.9, 
                    label=f'{clean_name} (avg: {avg_score:.3f})')
            
            # Add annotations
            for days, value in zip(data['past_days'], data[model]):
                plt.annotate(f'{value:.3f}', 
                           (days, value),
                           xytext=(0, 15), 
                           textcoords='offset points',
                           ha='center',
                           fontsize=10,
                           color=colors[i],
                           fontweight='bold')
        
        plt.title(f'Top 5 Models Performance Comparison\n{date}', 
                 fontsize=16, fontweight='bold')
        plt.ylabel('Average Score', fontsize=12)
        plt.xlabel('Past Days', fontsize=12)
        plt.xticks(data['past_days'])
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save plot
        filename = f'top_5_models_{date}.png'
        plt.savefig(save_path / filename, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ Saved: {filename}")
    
    def process_date(self, date: str):
        """
        Process a single date - load data and create plots.
        """
        print(f"\n📅 PROCESSING {date}")
        print("=" * 40)
        
        # Create output directory
        date_output_path = self.output_path / date
        date_output_path.mkdir(exist_ok=True)
        
        # Load data
        data = self.load_data_for_date(date)
        
        if data is not None:
            # Create plots
            self.create_all_models_plot(data, date, date_output_path)
            self.create_top_models_plot(data, date, date_output_path)
            print(f"✅ Successfully processed {date}")
            return True
        else:
            print(f"❌ Failed to process {date}")
            return False
    
    def process_all_dates(self):
        """
        Process all July dates.
        """
        print(f"\n🎨 PROCESSING ALL DATES")
        print("=" * 50)
        
        successful = 0
        failed = 0
        
        for date in self.july_dates:
            if self.process_date(date):
                successful += 1
            else:
                failed += 1
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📁 Plots saved to: {self.output_path.resolve()}")
    
    def set_base_path_manually(self, new_base_path: str):
        """
        Manually set the base path if auto-detection fails.
        """
        self.base_path = Path(new_base_path)
        print(f"🔧 Base path manually set to: {self.base_path.resolve()}")


def main():
    """
    Main function.
    """
    print("🚀 LLM JUDGE PERFORMANCE VISUALIZER")
    print("=" * 60)
    
    # Try with auto-detection
    visualizer = LLMJudgePerformanceVisualizer()
    
    # If auto-detection fails, try manual paths
    if not (visualizer.base_path / "llm_as_a_judge").exists():
        print(f"\n⚠️  Auto-detection failed. Trying manual paths...")
        
        manual_paths = [
            r"C:\Users\sateliti1\Desktop\Claudiu\AI_disertatie",
            r"C:\Users\sateliti1\Desktop\Claudiu",
            "AI_disertatie",
            "."
        ]
        
        for path in manual_paths:
            test_visualizer = LLMJudgePerformanceVisualizer(base_path=path)
            if (test_visualizer.base_path / "llm_as_a_judge").exists():
                visualizer = test_visualizer
                break
    
    # Process all dates
    visualizer.process_all_dates()

def test_single_date():
    """
    Test with just one date (2024-07-10).
    """
    print("🧪 TESTING SINGLE DATE: 2024-07-10")
    print("=" * 40)
    
    visualizer = LLMJudgePerformanceVisualizer()
    visualizer.process_date("2024-07-10")

def use_exact_path():
    """
    Use the exact path you provided.
    """
    exact_base = r"C:\Users\sateliti1\Desktop\Claudiu\AI_disertatie"
    print(f"🎯 USING EXACT PATH: {exact_base}")
    
    visualizer = LLMJudgePerformanceVisualizer(base_path=exact_base)
    visualizer.process_all_dates()

if __name__ == "__main__":
    # Try the exact path first
    use_exact_path()
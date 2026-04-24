import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import Optional


class LLMJudgePerformanceVisualizer:
    """Visualization system for LLM-as-a-judge performance analysis."""

    def __init__(self, base_path: Optional[str] = None, output_path: str = "plots_llm_as_a_judge"):
        self.base_path = Path(base_path) if base_path else self.auto_detect_base_path()
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)

        self.july_dates = [
            "2024-07-05", "2024-07-10", "2024-07-15",
            "2024-07-20", "2024-07-25", "2024-07-30",
        ]

    def auto_detect_base_path(self) -> Path:
        for path in [
            Path("."),
            Path("AI_disertatie"),
            Path(".."),
            Path("../.."),
            Path(r"C:\Users\sateliti1\Desktop\Claudiu\AI_disertatie"),
            Path(r"C:\Users\sateliti1\Desktop\Claudiu"),
        ]:
            if (path / "llm_as_a_judge" / "gpt-5-mini").exists():
                return path
        return Path(".")

    def _csv_path_for_date(self, date: str) -> Path:
        return (self.base_path / "llm_as_a_judge" / "gpt-5-mini" /
                date / "4_past_days" / "analysis" / "average_scores_models_vs_past_days.csv")

    def load_data_for_date(self, date: str) -> Optional[pd.DataFrame]:
        """Load the averaged-scores CSV for a given date."""
        csv_path = self._csv_path_for_date(date)
        if not csv_path.exists():
            return None
        try:
            return pd.read_csv(csv_path)
        except Exception as e:
            print(f"Error loading {csv_path}: {e}")
            return None

    def _load_variance_summary(self, date: str) -> Optional[pd.DataFrame]:
        """Load variance_summary.csv from analysis/ (multi-index)."""
        path = (self.base_path / "llm_as_a_judge" / "gpt-5-mini" /
                date / "4_past_days" / "analysis" / "variance_summary.csv")
        if not path.exists():
            return None
        return pd.read_csv(path, header=[0, 1], index_col=[0, 1])

    def create_variance_plot(self, date: str, save_path: Path, metric: str = "average_score"):
        """
        Per-model line plot across past_days with ±1 std error bars derived
        from replicate judge runs (seed x judge_run). Shows whether model
        differences exceed the replicate noise floor.
        """
        variance = self._load_variance_summary(date)
        if variance is None or (metric, "mean") not in variance.columns:
            return

        means = variance[(metric, "mean")].unstack(level=0)
        stds = variance[(metric, "std")].unstack(level=0).fillna(0)
        counts = variance[(metric, "count")].unstack(level=0)

        models = list(means.columns)
        colors = plt.cm.tab20(np.linspace(0, 1, len(models)))

        plt.figure(figsize=(14, 9))
        for i, model in enumerate(models):
            clean = model.replace('_', ' ').replace('-', ' ')
            plt.errorbar(
                means.index, means[model], yerr=stds[model],
                fmt="o-", linewidth=2, markersize=7, capsize=4,
                color=colors[i], alpha=0.85, label=clean,
            )

        max_n = int(counts.max().max()) if not counts.empty else 0
        plt.title(
            f"Judge Score with Replicate Variance ({metric})\n{date} "
            f"(error bars: ±1 std, n≈{max_n} replicates per cell)",
            fontsize=15, fontweight="bold",
        )
        plt.ylabel("Average Judge Score", fontsize=12)
        plt.xlabel("Past Days", fontsize=12)
        plt.xticks(sorted(means.index))
        plt.grid(True, alpha=0.3)
        plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
        plt.tight_layout()

        out_file = save_path / f"judge_variance_{metric}_{date}.png"
        plt.savefig(out_file, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"Saved: {out_file}")

    def create_all_models_plot(self, data: pd.DataFrame, date: str, save_path: Path):
        """All models' performance evolution across past_days."""
        plt.figure(figsize=(16, 10))

        model_columns = [col for col in data.columns if col != 'past_days']
        colors = plt.cm.tab20(np.linspace(0, 1, len(model_columns)))

        for i, model in enumerate(model_columns):
            clean_name = model.replace('_', ' ').replace('-', ' ')
            plt.plot(data['past_days'], data[model],
                     'o-', linewidth=3, markersize=8,
                     color=colors[i], alpha=0.8, label=clean_name)

            for days, value in zip(data['past_days'], data[model]):
                plt.annotate(f'{value:.3f}', (days, value),
                             xytext=(0, 15), textcoords='offset points',
                             ha='center', fontsize=9, alpha=0.7,
                             color=colors[i], fontweight='bold')

        plt.title(f'All LLM Models Performance Evolution\n{date}',
                  fontsize=18, fontweight='bold', pad=20)
        plt.ylabel('Average Score', fontsize=14)
        plt.xlabel('Past Days', fontsize=14)
        plt.xticks(data['past_days'])
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        out_file = save_path / f'all_models_evolution_{date}.png'
        plt.savefig(out_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {out_file}")

    def create_top_models_plot(self, data: pd.DataFrame, date: str, save_path: Path):
        """Top 5 models by average performance."""
        model_columns = [col for col in data.columns if col != 'past_days']
        model_averages = {model: data[model].mean() for model in model_columns}
        top_models = sorted(model_averages.items(), key=lambda x: x[1], reverse=True)[:5]

        plt.figure(figsize=(12, 8))
        colors = plt.cm.viridis(np.linspace(0, 1, 5))

        for i, (model, avg_score) in enumerate(top_models):
            clean_name = model.replace('_', ' ').replace('-', ' ')
            plt.plot(data['past_days'], data[model],
                     'o-', linewidth=4, markersize=10,
                     color=colors[i], alpha=0.9,
                     label=f'{clean_name} (avg: {avg_score:.3f})')

            for days, value in zip(data['past_days'], data[model]):
                plt.annotate(f'{value:.3f}', (days, value),
                             xytext=(0, 15), textcoords='offset points',
                             ha='center', fontsize=10,
                             color=colors[i], fontweight='bold')

        plt.title(f'Top 5 Models Performance Comparison\n{date}',
                  fontsize=16, fontweight='bold')
        plt.ylabel('Average Score', fontsize=12)
        plt.xlabel('Past Days', fontsize=12)
        plt.xticks(data['past_days'])
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        out_file = save_path / f'top_5_models_{date}.png'
        plt.savefig(out_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {out_file}")

    def process_date(self, date: str) -> bool:
        """Load data and create plots for a single date."""
        date_output_path = self.output_path / date
        date_output_path.mkdir(exist_ok=True)

        data = self.load_data_for_date(date)
        if data is None:
            return False

        self.create_all_models_plot(data, date, date_output_path)
        self.create_top_models_plot(data, date, date_output_path)
        self.create_variance_plot(date, date_output_path)
        return True

    def process_all_dates(self):
        successful = failed = 0
        for date in self.july_dates:
            if self.process_date(date):
                successful += 1
            else:
                failed += 1
        print(f"\nDone. Successful: {successful}, failed: {failed}")
        print(f"Plots saved to: {self.output_path.resolve()}")


def main():
    visualizer = LLMJudgePerformanceVisualizer()
    print(f"Base path: {visualizer.base_path.resolve()}")
    print(f"Output path: {visualizer.output_path.resolve()}")

    if not (visualizer.base_path / "llm_as_a_judge").exists():
        for path in [
            r"C:\Users\sateliti1\Desktop\Claudiu\AI_disertatie",
            r"C:\Users\sateliti1\Desktop\Claudiu",
            "AI_disertatie", ".",
        ]:
            candidate = LLMJudgePerformanceVisualizer(base_path=path)
            if (candidate.base_path / "llm_as_a_judge").exists():
                visualizer = candidate
                break

    visualizer.process_all_dates()


if __name__ == "__main__":
    main()

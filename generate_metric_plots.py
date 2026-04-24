import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple


class ModelPerformanceVisualizer:
    """Visualization system for model performance across dates and metrics."""

    def __init__(self, base_path: str = "AI_disertatie", output_path: str = "plots"):
        self.base_path = Path(base_path)
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)

        if not self.base_path.exists():
            self.auto_detect_base_path()

        self.july_dates = [
            "2024-07-05", "2024-07-10", "2024-07-15",
            "2024-07-20", "2024-07-25", "2024-07-30",
        ]

        self.available_metrics = [
            'rouge1_f', 'rouge1_p', 'rouge1_r', 'rouge2_f', 'rouge2_p', 'rouge2_r',
            'rougeL_f', 'rougeL_p', 'rougeL_r', 'bleu', 'bert_precision',
            'bert_recall', 'bert_f1', 'meteor', 'jaccard_similarity',
            'reference_coverage', 'response_coverage',
        ]

    def auto_detect_base_path(self) -> bool:
        for path in [Path('.'), Path('AI_disertatie'), Path('../AI_disertatie'), Path('../../AI_disertatie')]:
            if (path / 'results').exists():
                self.base_path = path
                return True
        return False

    def load_data_for_date(self, date: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Load summary_by_model.csv and summary_by_past_days.csv for a date."""
        summary_by_model_df = None
        summary_by_past_days_df = None

        for path in [self.base_path / "results" / date,
                     self.base_path / "results" / date / "4_past_days"]:
            if not path.exists():
                continue
            model_file = path / "summary_by_model.csv"
            days_file = path / "summary_by_past_days.csv"
            if model_file.exists() and summary_by_model_df is None:
                summary_by_model_df = pd.read_csv(model_file)
            if days_file.exists() and summary_by_past_days_df is None:
                summary_by_past_days_df = pd.read_csv(days_file)

        return summary_by_model_df, summary_by_past_days_df

    def _load_per_model_std(self, metric: str, date: str) -> Optional[pd.DataFrame]:
        """Load table2_<metric>_mean_per_model.csv (columns: mean, std, count)."""
        for candidate in [
            self.base_path / "results" / date / "4_past_days" / f"table2_{metric}_mean_per_model.csv",
            self.base_path / "results" / date / f"table2_{metric}_mean_per_model.csv",
        ]:
            if candidate.exists():
                return pd.read_csv(candidate, index_col=0)
        return None

    def _load_per_past_days_std(self, metric: str, date: str) -> Optional[pd.DataFrame]:
        """Load table3_<metric>_mean_per_past_days.csv (columns: mean, std, count)."""
        for candidate in [
            self.base_path / "results" / date / "4_past_days" / f"table3_{metric}_mean_per_past_days.csv",
            self.base_path / "results" / date / f"table3_{metric}_mean_per_past_days.csv",
        ]:
            if candidate.exists():
                return pd.read_csv(candidate, index_col=0)
        return None

    def _load_variance_summary(self, date: str) -> Optional[pd.DataFrame]:
        """Load variance_summary.csv (multi-index: model,past_days x metric,{mean,std,count})."""
        for candidate in [
            self.base_path / "results" / date / "4_past_days" / "variance_summary.csv",
            self.base_path / "results" / date / "variance_summary.csv",
        ]:
            if candidate.exists():
                return pd.read_csv(candidate, header=[0, 1], index_col=[0, 1])
        return None

    def create_bubble_plot(self, data: pd.DataFrame, metric: str, date: str, save_path: Path):
        """Bubble plot with seed-variance error bars when available."""
        if data is None or metric not in data.columns:
            return

        plt.figure(figsize=(12, 8))

        bubble_sizes = (data[metric] - data[metric].min() + 0.1) * 500
        colors = plt.cm.Set3(np.linspace(0, 1, len(data)))

        plt.scatter(
            range(len(data)), data[metric], s=bubble_sizes, c=colors,
            alpha=0.7, edgecolors='black', linewidth=1,
        )

        std_df = self._load_per_model_std(metric, date)
        variance_note = ""
        if std_df is not None and "std" in std_df.columns:
            stds = [
                std_df.loc[m, "std"] if m in std_df.index and pd.notna(std_df.loc[m, "std"]) else 0.0
                for m in data["model"]
            ]
            n_seeds = int(std_df["count"].max()) if "count" in std_df.columns else None
            plt.errorbar(
                range(len(data)), data[metric], yerr=stds,
                fmt="none", ecolor="black", elinewidth=1.5, capsize=6, alpha=0.9,
            )
            variance_note = f" (error bars: ±1 std across {n_seeds} seeds)" if n_seeds else " (±1 std)"

        for i, model in enumerate(data['model']):
            plt.annotate(
                model, (i, data[metric].iloc[i]),
                xytext=(5, 5), textcoords='offset points',
                fontsize=10, fontweight='bold',
            )

        plt.title(f'Model Performance Comparison - {metric}\n{date}{variance_note}',
                  fontsize=16, fontweight='bold')
        plt.ylabel(f'{metric} Score', fontsize=12)
        plt.xlabel('Models', fontsize=12)
        plt.xticks(range(len(data)), data['model'], rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        out_file = save_path / f'bubble_plot_{metric}_{date}.png'
        plt.savefig(out_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {out_file}")

    def create_moving_average_plot(self, all_data: dict, metric: str, save_path: Path):
        """Moving average across July dates."""
        if not all_data:
            return

        dates, metric_values = [], []
        for date in sorted(all_data.keys()):
            if all_data[date] is not None and metric in all_data[date].columns:
                dates.append(datetime.strptime(date, '%Y-%m-%d'))
                metric_values.append(all_data[date][metric].mean())

        if len(dates) < 2:
            return

        plt.figure(figsize=(12, 8))
        window_size = min(3, len(metric_values))
        moving_avg = pd.Series(metric_values).rolling(window=window_size, center=True).mean()

        plt.plot(dates, metric_values, 'o-', label=f'Original {metric}',
                 linewidth=2, markersize=8, alpha=0.7)
        plt.plot(dates, moving_avg, 's-', label=f'Moving Average (window={window_size})',
                 linewidth=3, markersize=10)

        plt.title(f'Moving Average Trend - {metric}\nJuly 2024', fontsize=16, fontweight='bold')
        plt.ylabel(f'{metric} Score', fontsize=12)
        plt.xlabel('Date', fontsize=12)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        out_file = save_path / f'moving_average_{metric}_july.png'
        plt.savefig(out_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {out_file}")

    def create_evolution_plot(self, data: pd.DataFrame, metric: str, date: str, save_path: Path):
        """Line plot across past_days with ±1 std shaded band (when multi-seed)."""
        if data is None or metric not in data.columns or 'past_days' not in data.columns:
            return

        plt.figure(figsize=(12, 8))
        data_sorted = data.sort_values('past_days')

        plt.plot(data_sorted['past_days'], data_sorted[metric],
                 'o-', linewidth=3, markersize=10, color='blue', alpha=0.8, label=metric)

        std_df = self._load_per_past_days_std(metric, date)
        variance_note = ""
        if std_df is not None and "std" in std_df.columns:
            means = std_df["mean"].reindex(data_sorted["past_days"]).values
            stds = std_df["std"].reindex(data_sorted["past_days"]).fillna(0).values
            plt.fill_between(
                data_sorted["past_days"], means - stds, means + stds,
                color="blue", alpha=0.15, label="±1 std (across seeds)",
            )
            n_seeds = int(std_df["count"].max()) if "count" in std_df.columns else None
            variance_note = f" (shaded: ±1 std across {n_seeds} seeds)" if n_seeds else " (±1 std)"
            plt.legend(fontsize=11)

        for days, value in zip(data_sorted['past_days'], data_sorted[metric]):
            plt.annotate(f'{value:.4f}', (days, value),
                         xytext=(0, 10), textcoords='offset points',
                         ha='center', fontsize=11, fontweight='bold')

        plt.title(f'Performance Evolution by Past Days - {metric}\n{date}{variance_note}',
                  fontsize=16, fontweight='bold')
        plt.ylabel(f'{metric} Score', fontsize=12)
        plt.xlabel('Past Days', fontsize=12)
        plt.xticks(data_sorted['past_days'])
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        out_file = save_path / f'evolution_plot_{metric}_{date}.png'
        plt.savefig(out_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {out_file}")

    def create_model_comparison_plot(self, metric: str, date: str, save_path: Path):
        """
        Per-model line plot across past_days with ±1 std error bars from
        variance_summary.csv — shows whether model differences exceed
        seed-level noise.
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
            plt.errorbar(
                means.index, means[model], yerr=stds[model],
                fmt="o-", linewidth=2, markersize=7, capsize=4,
                color=colors[i], alpha=0.85, label=model,
            )

        max_n = int(counts.max().max()) if not counts.empty else 0
        plt.title(
            f"Model Comparison with Seed Variance - {metric}\n{date} "
            f"(error bars: ±1 std, n≈{max_n} per cell)",
            fontsize=15, fontweight="bold",
        )
        plt.ylabel(f"{metric} Score", fontsize=12)
        plt.xlabel("Past Days", fontsize=12)
        plt.xticks(sorted(means.index))
        plt.grid(True, alpha=0.3)
        plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
        plt.tight_layout()

        out_file = save_path / f"model_comparison_{metric}_{date}.png"
        plt.savefig(out_file, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"Saved: {out_file}")

    def generate_all_plots(self, metric: str):
        """Generate all plots for the specified metric across all July dates."""
        if metric not in self.available_metrics:
            print(f"Skipping unknown metric: {metric}")
            return

        print(f"\n=== Generating plots for metric: {metric} ===")
        all_model_data = {}

        for date in self.july_dates:
            date_output_path = self.output_path / date
            date_output_path.mkdir(exist_ok=True)

            model_data, days_data = self.load_data_for_date(date)

            if model_data is not None:
                self.create_bubble_plot(model_data, metric, date, date_output_path)
                all_model_data[date] = model_data

            if days_data is not None:
                self.create_evolution_plot(days_data, metric, date, date_output_path)

            self.create_model_comparison_plot(metric, date, date_output_path)

        if all_model_data:
            self.create_moving_average_plot(all_model_data, metric, self.output_path)


def main():
    visualizer = ModelPerformanceVisualizer()
    print(f"Base path: {visualizer.base_path.resolve()}")
    print(f"Output path: {visualizer.output_path.resolve()}")

    important_metrics = ['rougeL_f', 'bleu', 'bert_f1', 'meteor', 'jaccard_similarity']
    for metric in important_metrics:
        visualizer.generate_all_plots(metric)

    print(f"\nDone. Plots saved under: {visualizer.output_path.resolve()}")


if __name__ == "__main__":
    main()

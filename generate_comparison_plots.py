"""
Three-way comparison plotter: fine-tuned (few-shot) vs fine-tuned
(zero-shot) vs base untrained model.

Reads variance_summary.csv files produced by response_evaluation and
judge_evaluation for each of the three series and draws per-metric line
plots across past_days, per date, with +/-1 std error bars.

Data sources:
  Fine-tuned few-shot (stats):  results/{date}/{N}_past_days/variance_summary.csv
                                 row: Llama-3.1-8B-Instruct-qlora
  Fine-tuned zero-shot (stats): fine_tuned_llm/results/zero-shot/{date}/{N}_past_days/variance_summary.csv
                                 row: Llama-3.1-8B-Instruct-qlora
  Base untrained (stats):       results/{date}/{N}_past_days/variance_summary.csv
                                 row: llama3.1_8b-instruct-q4_K_M
  Fine-tuned few-shot (judge):  llm_as_a_judge/gpt-5-mini/{date}/{N}_past_days/analysis/variance_summary.csv
  Fine-tuned zero-shot (judge): fine_tuned_llm/results/zero-shot/{date}/{N}_past_days/judge/analysis/variance_summary.csv
  Base untrained (judge):       same as few-shot judge, different row

Quantization caveat: the base model runs under Ollama's Q4_K_M
quantization while the QLoRA fine-tune runs under NF4 base + bf16
adapter via HF. The base-vs-fine-tuned delta therefore includes a
quantization component in addition to the training effect. The plot
title footnotes this.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Optional, Tuple


_FINETUNED_MODEL = "Llama-3.1-8B-Instruct-qlora"
_BASE_MODEL = "llama3.1_8b-instruct-q4_K_M"

_STATS_METRICS = ("rougeL_f", "bleu", "bert_f1", "meteor", "jaccard_similarity")
_JUDGE_METRIC = "average_score"

_COLORS = {
    "finetuned_fewshot": "#1f77b4",
    "finetuned_zeroshot": "#ff7f0e",
    "base_untrained": "#2ca02c",
}
_LABELS = {
    "finetuned_fewshot": "Fine-tuned (few-shot)",
    "finetuned_zeroshot": "Fine-tuned (zero-shot)",
    "base_untrained": "Base llama3.1:8b (Q4_K_M, untrained)",
}


def _load_variance_summary(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path, header=[0, 1], index_col=[0, 1])
    except Exception as e:
        print(f"WARNING: failed to load {path}: {e}")
        return None


def _extract_series(
    variance: Optional[pd.DataFrame],
    model_name: str,
    metric: str,
) -> Optional[Tuple[pd.Series, pd.Series]]:
    """Return (mean, std) indexed by past_days for the given model+metric."""
    if variance is None:
        return None
    if (metric, "mean") not in variance.columns:
        return None
    try:
        means = variance[(metric, "mean")].unstack(level=0)
        stds = variance[(metric, "std")].unstack(level=0).fillna(0)
    except Exception:
        return None
    if model_name not in means.columns:
        return None
    return means[model_name], stds[model_name]


def _plot_three_series(
    series: dict,
    metric: str,
    date: str,
    ylabel: str,
    title_suffix: str,
    out_file: Path,
) -> None:
    """Draw one figure with up to three error-barred lines."""
    if not any(v is not None for v in series.values()):
        return

    plt.figure(figsize=(11, 7))

    for key, data in series.items():
        if data is None:
            continue
        mean, std = data
        xs = sorted(mean.index)
        mean = mean.reindex(xs)
        std = std.reindex(xs)
        plt.errorbar(
            xs, mean.values, yerr=std.values,
            fmt="o-", linewidth=2.2, markersize=8, capsize=5,
            color=_COLORS[key], alpha=0.9, label=_LABELS[key],
        )

    plt.title(
        f"Three-way comparison - {metric}\n{date} {title_suffix}\n"
        "Note: base model runs Q4_K_M (Ollama); fine-tuned runs NF4+bf16 adapter (HF)",
        fontsize=13, fontweight="bold",
    )
    plt.ylabel(ylabel, fontsize=11)
    plt.xlabel("Past Days", fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10, loc="best")
    plt.tight_layout()

    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_file}")


def _comparison_stats_path(date: str, past_days: int) -> Path:
    return Path("results") / date / f"{past_days}_past_days" / "variance_summary.csv"


def _zero_shot_stats_path(date: str, past_days: int) -> Path:
    return (
        Path("fine_tuned_llm") / "results" / "zero-shot" / date
        / f"{past_days}_past_days" / "variance_summary.csv"
    )


def _comparison_judge_path(date: str, past_days: int, judge_model: str = "gpt-5-mini") -> Path:
    return (
        Path("llm_as_a_judge") / judge_model / date
        / f"{past_days}_past_days" / "analysis" / "variance_summary.csv"
    )


def _zero_shot_judge_path(date: str, past_days: int) -> Path:
    return (
        Path("fine_tuned_llm") / "results" / "zero-shot" / date
        / f"{past_days}_past_days" / "judge" / "analysis" / "variance_summary.csv"
    )


def plot_stats_for_date(date: str, past_days: int, output_root: Path) -> None:
    """Emit one comparison PNG per stats metric for a given date."""
    fewshot = _load_variance_summary(_comparison_stats_path(date, past_days))
    zeroshot = _load_variance_summary(_zero_shot_stats_path(date, past_days))

    out_dir = output_root / date / "stats"
    out_dir.mkdir(parents=True, exist_ok=True)

    for metric in _STATS_METRICS:
        series = {
            "finetuned_fewshot": _extract_series(fewshot, _FINETUNED_MODEL, metric),
            "finetuned_zeroshot": _extract_series(zeroshot, _FINETUNED_MODEL, metric),
            "base_untrained": _extract_series(fewshot, _BASE_MODEL, metric),
        }
        _plot_three_series(
            series=series,
            metric=metric,
            date=date,
            ylabel=f"{metric} score",
            title_suffix="(statistical metrics)",
            out_file=out_dir / f"comparison_{metric}_{date}.png",
        )


def plot_judge_for_date(date: str, past_days: int, output_root: Path) -> None:
    """Emit one comparison PNG for the judge average_score on a given date."""
    fewshot_judge = _load_variance_summary(_comparison_judge_path(date, past_days))
    zeroshot_judge = _load_variance_summary(_zero_shot_judge_path(date, past_days))

    out_dir = output_root / date / "judge"
    out_dir.mkdir(parents=True, exist_ok=True)

    series = {
        "finetuned_fewshot": _extract_series(fewshot_judge, _FINETUNED_MODEL, _JUDGE_METRIC),
        "finetuned_zeroshot": _extract_series(zeroshot_judge, _FINETUNED_MODEL, _JUDGE_METRIC),
        "base_untrained": _extract_series(fewshot_judge, _BASE_MODEL, _JUDGE_METRIC),
    }
    _plot_three_series(
        series=series,
        metric=_JUDGE_METRIC,
        date=date,
        ylabel="Judge average score",
        title_suffix="(LLM-as-a-judge)",
        out_file=out_dir / f"comparison_judge_{_JUDGE_METRIC}_{date}.png",
    )


def main():
    july_dates = [
        "2024-01-30", "2024-03-30", "2024-05-30",
        "2024-07-30", "2024-09-30", "2024-11-30",
    ]
    past_days = 4
    output_root = Path("plots_comparison")
    output_root.mkdir(exist_ok=True)

    for date in july_dates:
        plot_stats_for_date(date, past_days, output_root)
        plot_judge_for_date(date, past_days, output_root)

    print(f"\nComparison plots saved under: {output_root.resolve()}")


if __name__ == "__main__":
    main()

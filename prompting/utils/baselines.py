"""
Time-series forecasting baselines on the (T, C) county-day mean
temperature matrix produced by `check_data_availability county_matrix`.

Five baselines, selectable via --baseline:

  - mean (closed-form): predict per-channel mean of the input window
  - persistence (closed-form): predict the last input timestep
  - linear_regression (trained): direct multi-output linear
  - nbeats (trained): generic N-BEATS (FC stacks with backcast residuals)
  - itransformer (trained): inverted transformer (Liu et al., ICLR 2024)
    - each county is a single token embedded from its W-step series;
    self-attention runs across the C variate tokens, learning
    multivariate correlations; a linear head projects each token to its
    H-step forecast. Direct multi-output by construction.
  - patchtst (trained): channel-independent patched transformer (Nie et
    al., ICLR 2023). Each county's W-step series is split into
    overlapping patches of size patch_len with the given stride; each
    patch is a token; self-attention runs across the temporal patches;
    a flatten + linear head emits the H-step forecast. Channel
    independence: the same transformer weights process each county
    separately, so cross-county correlations are NOT modelled - the
    architectural contrast with iTransformer is deliberate.

The trained baselines optimise an exponential horizon-weighted Huber
loss:

    w_t  = exp(-decay * t)                    for t in {0, ..., H-1}
    h(a) = 0.5*a^2        if |a| <= delta
         = delta*(|a| - 0.5*delta)  otherwise   per-cell elementwise
    loss = (w_t * h(pred - target)).mean()

so the gradient prioritises near-term forecast accuracy AND is bounded
in magnitude for large errors (Huber transitions from quadratic to
linear at |a| = delta - default 1.0, i.e. one z-score std). MSE-style
when errors are small, MAE-style when they're large; smooth everywhere.

Inputs and targets are z-score normalised per channel using stats fit
on the training fold only (no leakage). Predictions are denormalised
back to degC before metrics. Closed-form baselines bypass the scaler
since both Mean and Persistence are scale-equivariant.

Walk-forward (expanding-window) cross-validation with --folds folds:
the windowed sample axis is sliced into (folds + 1) approximately equal
chunks; fold i trains on chunks 0..i and tests on chunk i+1. Each fold's
trained model is fit from scratch.

Only per-fold plots are produced. The last fold has the largest
training-set size, so its row in the figure represents the model that
would be deployed for future predictions. The mean-across-folds
aggregate is still in the JSON for inspection but no longer plotted -
averaging hides the training-set-size effect we want to see.

Metrics (always unweighted, for reporting):
  - RMSE / MAE overall (across all samples, horizons, counties)
  - RMSE / MAE per horizon step
  - RMSE per county
Aggregated across folds by simple mean.

Training and plotting are decoupled. Training writes one JSON per
baseline under --output_dir; plotting is a separate invocation that
reads those JSONs and produces both aggregate and per-fold figures.

CLI:
    # Train (no plots produced)
    python -m prompting.utils.baselines \\
        --baseline {mean|persistence|linear_regression|nbeats|itransformer|patchtst|all} \\
        --window 10 --horizon 10 --folds 4 --decay 0.05 --epochs 500

    # Plot - regenerate PNGs from existing JSONs
    python -m prompting.utils.baselines --plot_only

    # Plot - same PNGs, plus open interactive zoomable matplotlib
    # windows (use the toolbar's zoom-rect tool to drill into regions
    # where baselines intersect)
    python -m prompting.utils.baselines --plot_only --show
"""

import argparse
import json
import random
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def _label_from_filename(filename: str) -> str:
    """
    Derive a short variable label from a per-county matrix CSV filename.

        daily_county_mean.csv         -> 'mean_temp'
        daily_county_precip.csv       -> 'precip'
        daily_county_wind.csv         -> 'wind'
        daily_county_nebulosity.csv   -> 'nebulosity'

    Any other filename uses its stem with a 'daily_county_' prefix
    stripped, falling back to the stem itself.
    """
    stem = Path(filename).stem
    if stem.startswith("daily_county_"):
        stem = stem[len("daily_county_"):]
    if stem == "mean":
        return "mean_temp"
    return stem


def load_county_matrix(
    date_folder: str = "date",
    csv_filename: str = "daily_county_mean.csv",
    extra_csv_filenames: Optional[list] = None,
) -> Tuple[np.ndarray, np.ndarray, pd.DatetimeIndex, list, list]:
    """
    Load one or more per-county-day variable matrices.

    The first CSV (`csv_filename`) is the TARGET variable - temperature
    by default - and is always included as the first block of the
    input tensor so the model has access to its own past readings.
    Optional `extra_csv_filenames` are stacked along the channel axis
    after the target block, in the order given. The output (Y) tensor
    later in the pipeline is built from the TARGET matrix only.

    Channel layout in the returned input_matrix:

        [ target (C columns)
          extra_1 (C columns)
          extra_2 (C columns)
          ... ]

    All matrices must share the same county set (column ordering is
    preserved from the target file). The date axis is intersected
    across every file, so e.g. precip's `2023-12-31..2024-12-31`
    backshifted span and temp's `2024-01-01..2025-01-01` reduce to a
    common `2024-01-01..2024-12-31` window in the multivariate case.

    Returns:
        input_matrix:    (T, C*K) where K = 1 + len(extra_csv_filenames)
        target_matrix:   (T, C)   - the first variable, used as Y later
        dates:           DatetimeIndex (T,) of intersected dates
        counties:        list of county codes (C,)
        variable_labels: list of K strings, one per variable block in
                         input_matrix. Index 0 is always the target.
    """
    folder = Path(date_folder)
    extras = list(extra_csv_filenames or [])

    target_path = folder / csv_filename
    if not target_path.is_file():
        raise FileNotFoundError(
            f"{target_path} not found. Generate it with:\n"
            f"  python -m prompting.utils.check_data_availability county_matrix"
        )
    target_df = pd.read_csv(target_path, index_col=0, parse_dates=True)
    counties = list(target_df.columns)
    if target_df.isna().any().any():
        raise ValueError(
            f"{target_path} contains NaN cells; regenerate it"
        )

    extra_dfs: list = []
    for fname in extras:
        path = folder / fname
        if not path.is_file():
            raise FileNotFoundError(
                f"{path} not found. Generate it with the matching "
                f"`county_*` subcommand of check_data_availability."
            )
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        if list(df.columns) != counties:
            raise ValueError(
                f"{fname} has a different county set than {csv_filename}; "
                f"regenerate both with the same regions JSON"
            )
        if df.isna().any().any():
            raise ValueError(f"{fname} contains NaN cells; regenerate it")
        extra_dfs.append((fname, df))

    # Intersect date axes (precip is backshifted by 1 day so its first
    # date precedes temp's and its last date precedes temp's by one).
    common_index = target_df.index
    for _, df in extra_dfs:
        common_index = common_index.intersection(df.index)
    if len(common_index) == 0:
        raise ValueError(
            "the date intersection across the loaded matrices is empty"
        )

    target_aligned = target_df.loc[common_index]
    blocks = [target_aligned.to_numpy(dtype=np.float32)]
    labels = [_label_from_filename(csv_filename)]
    for fname, df in extra_dfs:
        blocks.append(df.loc[common_index].to_numpy(dtype=np.float32))
        labels.append(_label_from_filename(fname))

    input_matrix = np.concatenate(blocks, axis=1)   # (T, C*K)
    target_matrix = blocks[0]                        # (T, C)
    return input_matrix, target_matrix, common_index, counties, labels


def make_windows(
    input_matrix: np.ndarray,
    window: int,
    horizon: int,
    dates: pd.DatetimeIndex,
    target_matrix: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    """
    Slide a (window, horizon) pair along the time axis.

    Args:
        input_matrix:  (T, C_in)   features that go into X
        window:        W
        horizon:       H
        dates:         DatetimeIndex (T,)
        target_matrix: (T, C_out) - what goes into Y. If None, uses
            `input_matrix` (legacy single-variable behaviour where
            input and target are the same temperature matrix).

    Returns:
        X: (N, W, C_in)
        Y: (N, H, C_out)
        anchor_dates: (N,) marking the last input day of each sample.
    """
    if target_matrix is None:
        target_matrix = input_matrix
    if input_matrix.shape[0] != target_matrix.shape[0]:
        raise ValueError(
            f"input_matrix and target_matrix disagree on length: "
            f"{input_matrix.shape[0]} vs {target_matrix.shape[0]}"
        )
    T = input_matrix.shape[0]
    N = T - window - horizon + 1
    if N <= 0:
        raise ValueError(
            f"Not enough timesteps for window={window} + horizon={horizon}: T={T}"
        )
    X = np.stack([input_matrix[i:i + window] for i in range(N)])
    Y = np.stack([target_matrix[i + window:i + window + horizon] for i in range(N)])
    anchor_dates = dates[window - 1:window - 1 + N]
    return X, Y, anchor_dates


def walk_forward_folds(n_samples: int, n_folds: int):
    """
    Yield (train_idx, test_idx) for `n_folds` expanding-window splits.

    Splits the sample axis into (n_folds + 1) near-equal slices; fold i
    uses slices 0..i as the train set and slice i+1 as the test set.
    Fold 1 has the smallest train set, fold N the largest.
    """
    if n_folds < 1:
        raise ValueError("n_folds must be >= 1")
    edges = np.linspace(0, n_samples, n_folds + 2, dtype=int)
    for i in range(n_folds):
        train_idx = np.arange(edges[0], edges[i + 1])
        test_idx = np.arange(edges[i + 1], edges[i + 2])
        yield train_idx, test_idx


class WindowedDataset(Dataset):
    """Thin wrapper turning (X, Y) numpy arrays into a PyTorch Dataset."""

    def __init__(self, X: np.ndarray, Y: np.ndarray):
        self.X = torch.from_numpy(np.asarray(X, dtype=np.float32))
        self.Y = torch.from_numpy(np.asarray(Y, dtype=np.float32))

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, i: int):
        return self.X[i], self.Y[i]


# ---------------------------------------------------------------------------
# Per-variable transform + per-county z-score normalisation
# ---------------------------------------------------------------------------
#
# Each county is centred and scaled independently: (mu_i, sigma_i) are
# computed for county i over ALL (sample, timestep) pairs in the
# training fold only. Test inputs/targets are then expressed in the same
# standardised space (mean ~= 0, std ~= 1 per county). Predictions are
# multiplied back by sigma_i and shifted by mu_i before metrics, so all
# reported numbers are in original units (degC).
#
# Spatial identity is carried by tensor position (channel index 0 == AB,
# 40 == VS); the per-county z-score handles the temperature scale.
#
# For multi-variable input, each variable block of C channels can be
# preceded by a variable-specific transform before z-score. The current
# scheme:
#
#   mean_temp    -> identity
#   precip       -> log1p   (R24 in mm is heavily right-skewed with a
#                            zero-mass at every dry day; log1p compresses
#                            the long tail while keeping zeros at zero)
#   wind         -> identity
#   nebulosity   -> identity
#
# The target block (always the first C channels by load_county_matrix's
# stacking order) is never log1p'd here because temperature is the
# target. Predictions therefore need only the z-score reversed before
# metrics.

_PER_VARIABLE_TRANSFORM = {
    "mean_temp":  "identity",
    "precip":     "log1p",
    "wind":       "identity",
    "nebulosity": "identity",
}


def fit_scaler(
    X_train: np.ndarray,
    variable_labels: list,
    n_channels_per_var: int,
) -> Tuple[np.ndarray, np.ndarray, list]:
    """
    Fit per-county z-score with per-variable transforms.

    `X_train` has shape (N, W, C * K) where C = `n_channels_per_var`
    and K = `len(variable_labels)`. Each variable block of C channels
    is transformed per `_PER_VARIABLE_TRANSFORM` before fitting; the
    z-score is then computed per channel over all (sample, timestep)
    pairs in the training fold.

    Returns:
        mean: (C * K,) per-channel means after the transform
        std:  (C * K,) per-channel stds (clamped to >= 1e-6)
        transforms: list of K transform names, one per variable block
    """
    C = n_channels_per_var
    K = len(variable_labels)
    if X_train.shape[-1] != C * K:
        raise ValueError(
            f"fit_scaler: X_train last dim {X_train.shape[-1]} != C*K = {C * K} "
            f"(C={C}, K={K})"
        )

    transforms: list = []
    X_t = X_train.astype(np.float32, copy=True)
    for k, label in enumerate(variable_labels):
        t = _PER_VARIABLE_TRANSFORM.get(label, "identity")
        transforms.append(t)
        if t == "log1p":
            X_t[..., k * C:(k + 1) * C] = np.log1p(
                np.maximum(X_t[..., k * C:(k + 1) * C], 0.0)
            )

    flat = X_t.reshape(-1, C * K)
    mean = flat.mean(axis=0).astype(np.float32)
    std = flat.std(axis=0).astype(np.float32)
    std = np.maximum(std, 1e-6)
    return mean, std, transforms


def apply_scaler(
    arr: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
    transforms: list,
    n_channels_per_var: int,
) -> np.ndarray:
    """
    Apply per-variable transforms followed by per-channel z-score.
    Broadcasts (..., C * K) over X (N, W, C * K).
    """
    C = n_channels_per_var
    out = arr.astype(np.float32, copy=True)
    for k, t in enumerate(transforms):
        if t == "log1p":
            out[..., k * C:(k + 1) * C] = np.log1p(
                np.maximum(out[..., k * C:(k + 1) * C], 0.0)
            )
    return (out - mean) / std


def inverse_scaler(
    arr: np.ndarray, mean: np.ndarray, std: np.ndarray,
) -> np.ndarray:
    """
    Reverse the per-county z-score for the target block. The target
    variable (temperature) uses the identity transform, so no inverse
    of log1p is needed here. `mean` and `std` should already be the
    slice of the input scaler covering only the target's C channels.
    """
    return arr * std + mean


# ---------------------------------------------------------------------------
# Loss
# ---------------------------------------------------------------------------

def make_horizon_weights(horizon: int, decay: float, device=None) -> torch.Tensor:
    """w_t = exp(-decay * t) for t in 0..H-1. Higher weight on near-term steps."""
    w = torch.exp(-decay * torch.arange(horizon, dtype=torch.float32))
    if device is not None:
        w = w.to(device)
    return w


def horizon_weighted_huber(
    pred: torch.Tensor, target: torch.Tensor, weights: torch.Tensor,
    delta: float = 1.0,
) -> torch.Tensor:
    """
    pred, target: (B, H, C). weights: (H,). The per-cell Huber loss is
    weighted by w_t along the horizon axis before averaging.

    Huber:
        h(a) = 0.5 * a^2                    if |a| <= delta
             = delta * (|a| - 0.5 * delta)  otherwise

    Reduces to MSE for |a| <= delta and to a shifted L1 above it.
    Robust to occasional large errors without losing the smooth
    quadratic basin around zero.
    """
    diff = pred - target
    abs_diff = diff.abs()
    quadratic = 0.5 * diff.pow(2)
    linear = delta * (abs_diff - 0.5 * delta)
    elementwise = torch.where(abs_diff <= delta, quadratic, linear)  # (B, H, C)
    weighted = elementwise * weights.view(1, -1, 1)
    return weighted.mean()


# ---------------------------------------------------------------------------
# Metrics (always unweighted) + temperature classification
# ---------------------------------------------------------------------------
#
# In addition to the regression metrics, every fold also records a
# 32-class temperature histogram on both predictions and targets. Class
# definition: one outlier class below TEMP_CLASS_MIN, a sequence of
# 2-degC wide regular bins from TEMP_CLASS_MIN up to TEMP_CLASS_MAX
# (30 bins), one outlier class at or above TEMP_CLASS_MAX. Used by
# `plot_class_distributions` to compare predicted vs observed class
# frequencies per fold and per baseline.

TEMP_CLASS_MIN = -20.0
TEMP_CLASS_MAX = 40.0
TEMP_CLASS_WIDTH = 2.0


def temp_class_edges() -> np.ndarray:
    """Bin edges: [-inf, -20, -18, ..., 38, 40, +inf]. 33 edges -> 32 bins."""
    inner = np.arange(
        TEMP_CLASS_MIN, TEMP_CLASS_MAX + TEMP_CLASS_WIDTH / 2.0, TEMP_CLASS_WIDTH,
    )
    return np.concatenate(([-np.inf], inner.astype(np.float64), [np.inf]))


def temp_class_labels() -> list:
    """Short string labels per bin, e.g. '<-20', '[-20,-18)', ..., '>=40'."""
    edges = temp_class_edges()
    labels: list = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if np.isinf(lo):
            labels.append(f"<{TEMP_CLASS_MIN:.0f}")
        elif np.isinf(hi):
            labels.append(f">={TEMP_CLASS_MAX:.0f}")
        else:
            labels.append(f"[{lo:.0f},{hi:.0f})")
    return labels


def temp_class_counts(values: np.ndarray) -> list:
    """
    Bin every value in `values` (flattened) into the 32-class scheme
    and return per-class counts as a list of Python ints.
    """
    edges = temp_class_edges()
    counts, _ = np.histogram(np.asarray(values).ravel(), bins=edges)
    return counts.astype(int).tolist()


def compute_metrics(pred: np.ndarray, target: np.ndarray, counties: list) -> dict:
    """
    pred, target: (N, H, C). Returns RMSE/MAE overall, per-horizon, and
    per-county, plus the 32-bin classification histograms for both
    arrays. All numeric values are in original temperature units (degC).
    """
    diff = pred - target
    rmse_overall = float(np.sqrt(np.mean(diff ** 2)))
    mae_overall = float(np.mean(np.abs(diff)))
    rmse_per_horizon = np.sqrt(np.mean(diff ** 2, axis=(0, 2))).tolist()
    mae_per_horizon = np.mean(np.abs(diff), axis=(0, 2)).tolist()
    rmse_per_county = np.sqrt(np.mean(diff ** 2, axis=(0, 1)))
    return {
        "rmse_overall": rmse_overall,
        "mae_overall": mae_overall,
        "rmse_per_horizon": rmse_per_horizon,
        "mae_per_horizon": mae_per_horizon,
        "rmse_per_county": dict(zip(counties, rmse_per_county.tolist())),
        "target_class_counts": temp_class_counts(target),
        "prediction_class_counts": temp_class_counts(pred),
    }


# ---------------------------------------------------------------------------
# Closed-form baselines
# ---------------------------------------------------------------------------

class MeanBaseline:
    """
    Predict the per-channel mean of the **target block** of the input
    window, repeated H times. When the input is multivariate (W, C*K),
    only the first C channels (the target variable, by load_county_matrix's
    stacking convention) are used; the auxiliary variables are ignored
    because predicting "wind from precip" makes no sense for this closed-
    form baseline.
    """

    def __init__(self, horizon: int, n_output_channels: int):
        self.horizon = horizon
        self.n_output = n_output_channels

    def predict(self, X: np.ndarray) -> np.ndarray:
        target_block = X[..., :self.n_output]     # (N, W, n_out)
        mu = target_block.mean(axis=1, keepdims=True)
        return np.repeat(mu, self.horizon, axis=1)


class PersistenceBaseline:
    """
    Predict the last input timestep of the **target block**, repeated H
    times. Same slicing convention as MeanBaseline for multivariate input.
    """

    def __init__(self, horizon: int, n_output_channels: int):
        self.horizon = horizon
        self.n_output = n_output_channels

    def predict(self, X: np.ndarray) -> np.ndarray:
        last = X[:, -1:, :self.n_output]          # (N, 1, n_out)
        return np.repeat(last, self.horizon, axis=1)


# ---------------------------------------------------------------------------
# Trained baselines
# ---------------------------------------------------------------------------

class LinearBaseline(nn.Module):
    """
    Direct multi-output linear regression. Flatten (W, n_in) input ->
    single linear layer -> (H, n_out) output. The simplest trained
    baseline; serves as a regression-strength floor for the deeper
    models. When n_in == n_out this is the single-variable case; when
    n_in > n_out the model can map the auxiliary input channels to the
    target output through one bias term per output position.
    """

    def __init__(
        self, window: int, horizon: int,
        n_input_channels: int, n_output_channels: int,
    ):
        super().__init__()
        self.window = window
        self.horizon = horizon
        self.n_input = n_input_channels
        self.n_output = n_output_channels
        self.fc = nn.Linear(window * n_input_channels, horizon * n_output_channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B = x.shape[0]
        flat = x.reshape(B, -1)
        out = self.fc(flat)
        return out.reshape(B, self.horizon, self.n_output)


class NBEATSBlock(nn.Module):
    """
    A generic N-BEATS block. FC stack produces a hidden vector; two
    heads project it to a backcast (over the input window, n_in
    channels) and a forecast (over the horizon, n_out channels). No
    trend/seasonality basis functions - generic blocks only.
    """

    def __init__(
        self, window: int, horizon: int,
        n_input_channels: int, n_output_channels: int,
        n_layers: int = 4, hidden: int = 128,
    ):
        super().__init__()
        self.window = window
        self.horizon = horizon
        self.n_input = n_input_channels
        self.n_output = n_output_channels
        layers = []
        in_dim = window * n_input_channels
        for _ in range(n_layers):
            layers += [nn.Linear(in_dim, hidden), nn.ReLU()]
            in_dim = hidden
        self.fc_stack = nn.Sequential(*layers)
        self.backcast_head = nn.Linear(hidden, window * n_input_channels)
        self.forecast_head = nn.Linear(hidden, horizon * n_output_channels)

    def forward(self, x_flat: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.fc_stack(x_flat)
        return self.backcast_head(h), self.forecast_head(h)


class NBEATSBaseline(nn.Module):
    """
    Stack of generic N-BEATS blocks with backcast residuals. Each block
    sees the residual left by previous blocks; forecasts are summed.
    Residual lives in the input space (n_in channels); forecast accumulates
    in the output space (n_out channels).
    """

    def __init__(
        self, window: int, horizon: int,
        n_input_channels: int, n_output_channels: int,
        n_blocks: int = 3, n_layers: int = 4, hidden: int = 128,
    ):
        super().__init__()
        self.window = window
        self.horizon = horizon
        self.n_input = n_input_channels
        self.n_output = n_output_channels
        self.blocks = nn.ModuleList([
            NBEATSBlock(
                window, horizon, n_input_channels, n_output_channels,
                n_layers, hidden,
            )
            for _ in range(n_blocks)
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B = x.shape[0]
        residual = x.reshape(B, -1)
        forecast = torch.zeros(B, self.horizon * self.n_output, device=x.device)
        for blk in self.blocks:
            bc, fc = blk(residual)
            residual = residual - bc
            forecast = forecast + fc
        return forecast.reshape(B, self.horizon, self.n_output)


class ITransformerBaseline(nn.Module):
    """
    Inverted Transformer (iTransformer; Liu et al., "iTransformer:
    Inverted Transformers Are Effective for Time Series Forecasting",
    ICLR 2024).

    The architectural inversion: in a vanilla transformer for time
    series each timestep is a token and self-attention runs across
    time. Here each *variate* (county channel) becomes a single token,
    embedded from its entire W-step input series via a linear
    projection (W -> d_model). Self-attention then runs across the
    n_in variate tokens, learning multivariate correlations across BOTH
    counties and (in the multi-variable case) variables - because the
    auxiliary variables are concatenated along the channel axis they
    appear as additional tokens that the temperature variate tokens
    can attend to. A per-token feed-forward learns variate-specific
    temporal structure, and a final linear head projects each token
    back to its own H-step forecast (d_model -> H).

    Output decoupling: the head produces (B, n_in, H) but we only need
    forecasts for the target variates (the first n_out tokens by
    load_county_matrix's stacking convention - target first, then
    extras). Auxiliary forecasts are computed and then discarded; this
    is wasteful in compute but keeps the architecture clean and lets
    the encoder learn richer cross-variable structure than a hard
    early-slice would allow.

    Direct multi-output by construction, so no decoder, no causal
    masking, and no scheduled sampling.

    Args:
        window, horizon: data shape.
        n_input_channels, n_output_channels: input variate count (C*K)
            and output variate count (C). Equal in the single-variable
            case.
        d_model: token embedding dimension.
        n_heads: attention heads (must divide d_model).
        n_layers: number of encoder layers.
        ff: feed-forward dimension inside each encoder layer.
        dropout: dropout rate applied after embedding and inside each
            encoder layer.
    """

    def __init__(
        self, window: int, horizon: int,
        n_input_channels: int, n_output_channels: int,
        d_model: int = 128, n_heads: int = 4, n_layers: int = 3,
        ff: int = 256, dropout: float = 0.1,
    ):
        super().__init__()
        self.window = window
        self.horizon = horizon
        self.n_input = n_input_channels
        self.n_output = n_output_channels
        self.d_model = d_model
        self.embed = nn.Linear(window, d_model)
        self.embed_dropout = nn.Dropout(dropout)
        enc_layer = nn.TransformerEncoderLayer(
            d_model, n_heads, ff, dropout, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, n_layers)
        self.head = nn.Linear(d_model, horizon)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, W, n_in). Transpose so variates become the token axis.
        x = x.transpose(1, 2)                  # (B, n_in, W)
        h = self.embed(x)                       # (B, n_in, d_model)
        h = self.embed_dropout(h)
        h = self.encoder(h)                     # (B, n_in, d_model)
        out = self.head(h)                      # (B, n_in, H)
        out = out.transpose(1, 2)               # (B, H, n_in)
        return out[:, :, :self.n_output]        # slice target block


class PatchTSTBaseline(nn.Module):
    """
    PatchTST (Nie et al., "A Time Series is Worth 64 Words: Long-term
    Forecasting with Transformers", ICLR 2023).

    Two architectural commitments:

      1. Patching - each county's W-step series is unfolded into
         n_patches patches of length `patch_len` with the given
         `stride`. Each patch becomes one token via a linear
         projection (patch_len -> d_model). For W=10 with the default
         patch_len=4, stride=2 we get 4 patches per county.

      2. Channel independence - the same transformer encoder weights
         process EVERY county separately. The batch and channel axes
         are merged into the model's leading dimension, so attention
         only ever runs across the n_patches temporal tokens of a
         single county. Cross-county correlations are not modelled.
         This is the defining hypothesis of the paper, and the
         deliberate contrast with iTransformer which is variate-
         mixing.

    A flatten + linear head projects the encoder output (n_patches *
    d_model) to the H-step forecast per channel. Direct multi-output,
    no decoder.

    Output decoupling: every input channel produces an H-step
    forecast, but only the first n_out channels (the target block by
    load_county_matrix's convention) are returned. Auxiliary forecasts
    are computed and then discarded; this is wasteful in compute but
    cleaner architecturally and lets the shared encoder learn from
    every channel.

    Args:
        window, horizon: data shape.
        n_input_channels, n_output_channels: input/output channel counts.
        patch_len: tokens per patch (4 by default; must be <= window).
        stride: stride between consecutive patches (2 by default).
        d_model: token embedding dim.
        n_heads: attention heads.
        n_layers: encoder layers.
        ff: feed-forward dim inside encoder layers.
        dropout: dropout in embedding and encoder.
    """

    def __init__(
        self, window: int, horizon: int,
        n_input_channels: int, n_output_channels: int,
        patch_len: int = 4, stride: int = 2,
        d_model: int = 128, n_heads: int = 4, n_layers: int = 3,
        ff: int = 256, dropout: float = 0.1,
    ):
        super().__init__()
        if patch_len <= 0 or patch_len > window:
            raise ValueError(
                f"patch_len={patch_len} must satisfy 1 <= patch_len <= window={window}"
            )
        if stride < 1:
            raise ValueError(f"stride={stride} must be >= 1")
        n_patches = (window - patch_len) // stride + 1
        if n_patches <= 0:
            raise ValueError(
                f"patchify produced no tokens: window={window}, "
                f"patch_len={patch_len}, stride={stride}"
            )

        self.window = window
        self.horizon = horizon
        self.n_input = n_input_channels
        self.n_output = n_output_channels
        self.patch_len, self.stride, self.n_patches = patch_len, stride, n_patches
        self.d_model = d_model

        self.patch_embed = nn.Linear(patch_len, d_model)
        # Learnable positional embedding across the n_patches tokens.
        # n_patches is small (~5 on W=10 with default settings), so a
        # learnt table is fine; no sinusoidal needed.
        self.pos_embed = nn.Parameter(torch.zeros(1, n_patches, d_model))
        nn.init.trunc_normal_(self.pos_embed, std=0.02)
        self.embed_dropout = nn.Dropout(dropout)

        enc_layer = nn.TransformerEncoderLayer(
            d_model, n_heads, ff, dropout, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, n_layers)

        self.head = nn.Linear(n_patches * d_model, horizon)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, W, n_in) -> (B, n_in, W) so the time axis can be unfolded
        x = x.transpose(1, 2)
        B, n_in, _ = x.shape
        # Patch via sliding window: (B, n_in, n_patches, patch_len)
        patches = x.unfold(dimension=-1, size=self.patch_len, step=self.stride)
        # Channel independence: merge batch and channel so each variate
        # is processed independently by the SAME transformer weights.
        patches = patches.reshape(B * n_in, self.n_patches, self.patch_len)
        h = self.patch_embed(patches) + self.pos_embed   # (B*n_in, n_patches, d_model)
        h = self.embed_dropout(h)
        h = self.encoder(h)                              # (B*n_in, n_patches, d_model)
        h_flat = h.reshape(B * n_in, self.n_patches * self.d_model)
        out = self.head(h_flat)                          # (B*n_in, H)
        out = out.reshape(B, n_in, self.horizon).transpose(1, 2)  # (B, H, n_in)
        return out[:, :, :self.n_output]                 # slice target block


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    *,
    epochs: int,
    lr: float,
    weight_decay: float,
    decay: float,
    huber_delta: float,
    horizon: int,
    device: str,
    verbose_every: int = 10,
) -> list:
    """
    Generic training loop for the trained baselines (linear_regression,
    nbeats, itransformer, patchtst). Uses AdamW with the given learning
    rate and weight decay, optimising the horizon-weighted Huber loss
    on z-score-normalised data.
    """
    model = model.to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    weights = make_horizon_weights(horizon, decay, device=device)
    losses: list = []
    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        n = 0
        for X, Y in train_loader:
            X = X.to(device)
            Y = Y.to(device)
            optim.zero_grad()
            pred = model(X)
            loss = horizon_weighted_huber(pred, Y, weights, delta=huber_delta)
            loss.backward()
            optim.step()
            epoch_loss += loss.item() * X.size(0)
            n += X.size(0)
        avg = epoch_loss / max(n, 1)
        losses.append(avg)
        if verbose_every and (epoch == 0 or (epoch + 1) % verbose_every == 0 or epoch == epochs - 1):
            print(f"    epoch {epoch + 1:3d}/{epochs}: loss={avg:.4f}")
    return losses


def predict_torch(model: nn.Module, X: np.ndarray, device: str) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        X_t = torch.from_numpy(np.asarray(X, dtype=np.float32)).to(device)
        pred = model(X_t)
        return pred.cpu().numpy()


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------

_MODEL_CLASS_MAP = {
    "LinearBaseline": "LinearBaseline",
    "NBEATSBaseline": "NBEATSBaseline",
    "ITransformerBaseline": "ITransformerBaseline",
    "PatchTSTBaseline": "PatchTSTBaseline",
}


def _build_model_init_kwargs(
    baseline: str, *,
    window: int, horizon: int,
    n_input_channels: int, n_output_channels: int,
    hidden: int, n_blocks: int, n_layers: int,
    d_model: int, n_heads: int, n_enc_layers: int,
    ff: int, dropout: float,
    patch_len: int, stride: int,
) -> dict:
    """
    Collect only the model-specific keyword arguments the constructor
    needs for this baseline. Used both to instantiate during training
    and to persist into the checkpoint so the model can be rehydrated
    without re-passing all CLI flags.
    """
    base = {
        "window": window, "horizon": horizon,
        "n_input_channels": n_input_channels,
        "n_output_channels": n_output_channels,
    }
    if baseline == "linear_regression":
        return base
    if baseline == "nbeats":
        return {**base, "n_blocks": n_blocks, "n_layers": n_layers, "hidden": hidden}
    if baseline == "itransformer":
        return {**base,
                "d_model": d_model, "n_heads": n_heads, "n_layers": n_enc_layers,
                "ff": ff, "dropout": dropout}
    if baseline == "patchtst":
        return {**base,
                "patch_len": patch_len, "stride": stride,
                "d_model": d_model, "n_heads": n_heads, "n_layers": n_enc_layers,
                "ff": ff, "dropout": dropout}
    raise ValueError(f"unknown trained baseline: {baseline!r}")


def save_fold_checkpoint(
    path: Path,
    *,
    baseline: str,
    label: str,
    fold: int,
    model: nn.Module,
    model_init_kwargs: dict,
    scaler: Optional[dict],
    variable_labels: list,
    counties: list,
    window: int,
    horizon: int,
    epochs: int,
    seed: int,
    train_date_range: Optional[list],
) -> None:
    """
    Save a per-fold checkpoint that fully captures what's needed to
    rerun inference: model class identifier + constructor kwargs +
    state_dict + scaler stats + a metadata block (variable labels,
    counties, training-set date range).

    Closed-form baselines (mean, persistence) have nothing to save and
    do not call this function.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "baseline": baseline,
        "label": label,
        "fold": fold,
        "model_class": type(model).__name__,
        "model_init_kwargs": model_init_kwargs,
        "model_state_dict": model.state_dict(),
        "scaler": scaler,
        "metadata": {
            "variable_labels": variable_labels,
            "counties": counties,
            "window": window,
            "horizon": horizon,
            "epochs": epochs,
            "seed": seed,
            "train_date_range": train_date_range,
        },
    }
    torch.save(payload, path)


def load_fold_checkpoint(path: Path) -> Tuple[nn.Module, Optional[dict], dict]:
    """
    Load a checkpoint written by `save_fold_checkpoint`. Returns
    (model, scaler_dict_or_None, payload_dict). The model has the
    weights already loaded and is in eval mode.
    """
    payload = torch.load(path, map_location="cpu", weights_only=False)
    cls_name = payload["model_class"]
    if cls_name not in _MODEL_CLASS_MAP:
        raise ValueError(
            f"checkpoint references unknown model class {cls_name!r}; "
            f"known classes: {sorted(_MODEL_CLASS_MAP.keys())}"
        )
    cls = globals()[_MODEL_CLASS_MAP[cls_name]]
    model = cls(**payload["model_init_kwargs"])
    model.load_state_dict(payload["model_state_dict"])
    model.eval()
    return model, payload.get("scaler"), payload


# ---------------------------------------------------------------------------
# Autoregressive rollout
# ---------------------------------------------------------------------------
#
# A trained model produces an H-step direct forecast. To extend to a
# longer horizon (e.g. 30 days when H=10), we feed the model's own
# predictions back as input and call it again, repeating until the
# requested total_steps is reached. The first chunk is the model's
# "initial" forecast; the subsequent chunks are the autoregressive
# extensions.
#
# Auxiliary-variable handling: the model's output covers only the
# target block (temperature). When the model has auxiliary input
# channels (precip, wind, nebulosity), those need values for every
# day in the rolled-forward window. We use the GROUND-TRUTH aux values
# from the data matrix - this isolates the autoregressive degradation
# to the target prediction alone, which is the most informative
# experiment. (If you wanted a "no future knowledge at all" rollout
# the aux channels would need to be forecast too, which the current
# pipeline doesn't support.)


def autoregressive_rollout(
    model: nn.Module,
    scaler: Optional[dict],
    init_window: np.ndarray,
    total_steps: int,
    H: int,
    n_input_channels: int,
    n_output_channels: int,
    device: str,
    aux_truth: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Rolling H-step prediction starting from a known window.

    Args:
        model: trained model with forward(x) -> (B, H, n_out).
        scaler: scaler dict from load_fold_checkpoint, or None when
            training ran with --no_normalize.
        init_window: (W, n_in) - the known initial input window in
            ORIGINAL units (degC for temp, mm for precip, ...).
        total_steps: number of prediction steps to roll forward.
        H: the model's trained horizon (single forward-pass output
            length).
        n_input_channels, n_output_channels: usually C*K and C.
        device: torch device.
        aux_truth: (total_steps, n_in - n_out) - optional ground-truth
            aux-channel values for the prediction range. Required when
            n_in > n_out; otherwise aux is held at the last-known value
            from `init_window[-1]`.

    Returns:
        predictions: (total_steps, n_out) - autoregressively predicted
            target values in original units.
    """
    model.eval()
    _, n_in = init_window.shape
    if n_in != n_input_channels:
        raise ValueError(
            f"init_window has {n_in} channels but model expects {n_input_channels}"
        )
    n_aux = n_in - n_output_channels
    if n_aux > 0 and aux_truth is None:
        last_known_aux = init_window[-1, n_output_channels:].copy()

    predictions = np.zeros((total_steps, n_output_channels), dtype=np.float32)
    window = init_window.astype(np.float32, copy=True)
    steps_done = 0

    while steps_done < total_steps:
        if scaler is not None:
            window_n = apply_scaler(
                window[np.newaxis],
                scaler["x_mean"], scaler["x_std"],
                scaler["transforms"], scaler["n_channels_per_var"],
            )[0]
        else:
            window_n = window

        with torch.no_grad():
            X_t = torch.from_numpy(window_n[np.newaxis]).to(device)
            pred_n = model(X_t).cpu().numpy()[0]   # (H, n_out)

        if scaler is not None:
            pred = pred_n * scaler["y_std"] + scaler["y_mean"]
        else:
            pred = pred_n

        take = min(H, total_steps - steps_done)
        predictions[steps_done:steps_done + take] = pred[:take]

        if steps_done + take >= total_steps:
            break

        # Slide the window: drop the oldest `take` rows, append `take`
        # new rows containing (predicted target) + (aux from truth or
        # held last value).
        new_rows = np.zeros((take, n_in), dtype=np.float32)
        new_rows[:, :n_output_channels] = pred[:take]
        if n_aux > 0:
            if aux_truth is not None:
                new_rows[:, n_output_channels:] = aux_truth[
                    steps_done:steps_done + take
                ]
            else:
                new_rows[:, n_output_channels:] = last_known_aux

        window = np.concatenate([window[take:], new_rows], axis=0)
        steps_done += take

    return predictions


def run_autoregressive(
    *,
    output_dir: str,
    date_folder: str,
    csv_filename: str,
    extra_csv_filenames: Optional[list],
    start_date: str,
    total_days: int,
    fold: int,
    device: str,
) -> None:
    """
    For every per-fold trained-baseline checkpoint matching `fold`,
    roll forward `total_days` predictions starting on `start_date`
    and write a comparison figure. Each figure overlays:

      - the ground-truth temperature trajectory (averaged across counties)
      - the model's INITIAL single-forward-pass prediction (first H days)
      - the model's AUTOREGRESSIVE trajectory (entire total_days span,
        feeding predictions back as input every H steps)

    Vertical guide lines mark every H-step chunk boundary so the
    autoregressive degradation is visible as a typical step-and-drift
    pattern.

    Args:
        output_dir: directory holding checkpoints/ and where the
            figures are written.
        date_folder, csv_filename, extra_csv_filenames: same semantics
            as the training pipeline. The auxiliary CSVs supply the
            ground-truth aux channels for multi-variable checkpoints.
        start_date: YYYY-MM-DD, the first day of the initial input
            window. The model's input is days
            [start_date, start_date + W - 1] (W is read from the
            checkpoint), and predictions extend over
            [start_date + W, start_date + W + total_days - 1].
        total_days: number of autoregressive prediction days.
        fold: which fold's checkpoint to use (typically 4 = deployable).
        device: torch device.
    """
    import matplotlib.pyplot as plt

    input_matrix, target_matrix, dates, _, _ = load_county_matrix(
        date_folder, csv_filename, extra_csv_filenames=extra_csv_filenames,
    )
    out_dir = Path(output_dir)
    ckpt_dir = out_dir / "checkpoints"
    if not ckpt_dir.is_dir():
        raise FileNotFoundError(
            f"no checkpoints/ dir under {out_dir}; train with --save_weights first"
        )

    try:
        start_idx = dates.get_loc(pd.Timestamp(start_date))
    except KeyError:
        raise ValueError(
            f"start_date {start_date} not in the data matrix "
            f"(range {dates[0].date()}..{dates[-1].date()})"
        )

    # All checkpoints for this fold. Closed-form baselines have no
    # checkpoints (and no learned state), so they're naturally excluded.
    ckpts = sorted(ckpt_dir.glob(f"*_fold{fold}.pt"))
    if not ckpts:
        raise FileNotFoundError(
            f"no fold-{fold} checkpoints under {ckpt_dir}; "
            f"re-run training with --save_weights"
        )

    print(f"Autoregressive rollout: start_date={start_date}, "
          f"total_days={total_days}, fold={fold}")
    print(f"Loaded {len(ckpts)} checkpoints from {ckpt_dir}")

    for ckpt_path in ckpts:
        model, scaler, payload = load_fold_checkpoint(ckpt_path)
        model = model.to(device)
        baseline = payload["baseline"]
        label = payload.get("label", "")
        W = payload["model_init_kwargs"]["window"]
        H = payload["model_init_kwargs"]["horizon"]
        n_in = payload["model_init_kwargs"]["n_input_channels"]
        n_out = payload["model_init_kwargs"]["n_output_channels"]

        end_idx = start_idx + W + total_days
        if end_idx > len(dates):
            print(
                f"  WARNING: skipping {ckpt_path.name} - not enough "
                f"matrix data after start_date for W={W} + "
                f"total_days={total_days}; need {W + total_days} days, "
                f"have {len(dates) - start_idx}"
            )
            continue

        # Initial input window in ORIGINAL units (the scaler handles
        # transforms internally per the multi-variable convention).
        init_window = input_matrix[start_idx:start_idx + W]
        # Ground-truth aux for the prediction range (used only when
        # n_in > n_out, i.e. multi-variable models)
        aux_truth = None
        if n_in > n_out:
            aux_truth = input_matrix[
                start_idx + W:start_idx + W + total_days,
                n_out:,
            ]

        # Initial single-shot prediction (just the first chunk's worth).
        init_pred = autoregressive_rollout(
            model, scaler, init_window, total_steps=H, H=H,
            n_input_channels=n_in, n_output_channels=n_out,
            device=device, aux_truth=(aux_truth[:H] if aux_truth is not None else None),
        )
        # Full autoregressive rollout.
        ar_pred = autoregressive_rollout(
            model, scaler, init_window, total_steps=total_days, H=H,
            n_input_channels=n_in, n_output_channels=n_out,
            device=device, aux_truth=aux_truth,
        )

        # Ground-truth trajectory.
        gt = target_matrix[start_idx + W:start_idx + W + total_days]   # (total_days, n_out)

        # Average across counties for a single-line trajectory plot.
        gt_mean = gt.mean(axis=1)
        init_mean = init_pred.mean(axis=1)
        ar_mean = ar_pred.mean(axis=1)

        # Per-step RMSE (across counties) for both predictions.
        init_rmse = np.sqrt(((init_pred - gt[:H]) ** 2).mean(axis=1))
        ar_rmse = np.sqrt(((ar_pred - gt) ** 2).mean(axis=1))

        # Per-baseline figure: two side-by-side subplots.
        fig, (ax_init, ax_ar) = plt.subplots(1, 2, figsize=(14, 5))

        # --- LEFT: initial single-shot prediction (first H days) ---
        x_init = np.arange(1, H + 1)
        ax_init.plot(x_init, gt_mean[:H], "-", color="black",
                     linewidth=2.0, label="ground truth")
        ax_init.plot(x_init, init_mean, "--", color="C0",
                     linewidth=2.0, label="initial prediction")
        ax_init.set_title(
            f"Initial single-shot prediction (1 forward pass, {H} days)\n"
            f"RMSE = {init_rmse.mean():.2f} degC"
        )
        ax_init.set_xlabel("day ahead")
        ax_init.set_ylabel("temperature (degC) — mean across counties")
        ax_init.set_xticks(x_init)
        ax_init.grid(True, alpha=0.3)
        ax_init.legend()

        # --- RIGHT: full autoregressive trajectory ---
        x_ar = np.arange(1, total_days + 1)
        ax_ar.plot(x_ar, gt_mean, "-", color="black",
                   linewidth=2.0, label="ground truth")
        ax_ar.plot(x_ar, ar_mean, "-", color="C1",
                   linewidth=2.0, label="autoregressive prediction")
        # Chunk boundaries: vertical lines at H, 2H, 3H, ...
        n_chunks = (total_days + H - 1) // H
        for k in range(1, n_chunks):
            ax_ar.axvline(k * H + 0.5, color="gray", linestyle=":", alpha=0.6)
            ax_ar.text(k * H + 0.5, ax_ar.get_ylim()[1], f"chunk {k + 1}",
                       rotation=90, va="top", ha="right",
                       fontsize=8, color="gray")
        ax_ar.set_title(
            f"Autoregressive rollout ({n_chunks} chunks of {H} days, "
            f"total {total_days} days)\n"
            f"RMSE = {ar_rmse.mean():.2f} degC overall, "
            f"first-chunk = {ar_rmse[:H].mean():.2f}, "
            f"last-chunk = {ar_rmse[-H:].mean():.2f}"
        )
        ax_ar.set_xlabel("day ahead")
        ax_ar.set_ylabel("temperature (degC) — mean across counties")
        ax_ar.grid(True, alpha=0.3)
        ax_ar.legend()

        # Standardise y-axis across both subplots so visual comparison is fair.
        y_min = float(min(gt_mean.min(), init_mean.min(), ar_mean.min())) - 1.0
        y_max = float(max(gt_mean.max(), init_mean.max(), ar_mean.max())) + 1.0
        ax_init.set_ylim(y_min, y_max)
        ax_ar.set_ylim(y_min, y_max)

        label_suffix = f"_{label}" if label else ""
        title_name = f"{baseline}{f' [{label}]' if label else ''}"
        fig.suptitle(
            f"Autoregressive forecasting: {title_name}, fold {fold}\n"
            f"start_date={start_date}, W={W}, H={H}, total_days={total_days}",
            fontsize=13, y=1.04,
        )
        fig.tight_layout()
        out_path = out_dir / (
            f"autoregressive_{baseline}{label_suffix}_fold{fold}_"
            f"{start_date}_{total_days}d.png"
        )
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  {baseline}{label_suffix:>10s}: initial RMSE={init_rmse.mean():.2f}, "
              f"AR RMSE={ar_rmse.mean():.2f}, "
              f"AR first-chunk={ar_rmse[:H].mean():.2f}, "
              f"AR last-chunk={ar_rmse[-H:].mean():.2f}    -> {out_path.name}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

_TRAINED_BASELINES = {"linear_regression", "nbeats", "itransformer", "patchtst"}
_CLOSED_FORM_BASELINES = {"mean", "persistence"}
_ALL_BASELINES = [
    "mean", "persistence",
    "linear_regression", "nbeats", "itransformer", "patchtst",
]


def run_baseline(
    baseline: str,
    *,
    date_folder: str,
    csv_filename: str,
    extra_csv_filenames: Optional[list],
    window: int,
    horizon: int,
    folds: int,
    decay: float,
    epochs: int,
    lr: float,
    weight_decay: float,
    huber_delta: float,
    batch_size: int,
    normalize: bool,
    hidden: int,
    n_blocks: int,
    n_layers: int,
    d_model: int,
    n_heads: int,
    n_enc_layers: int,
    ff: int,
    dropout: float,
    patch_len: int,
    stride: int,
    device: str,
    seed: int,
    output_dir: str,
    label: str = "",
    save_weights: bool = False,
) -> dict:
    input_matrix, target_matrix, dates, counties, variable_labels = load_county_matrix(
        date_folder, csv_filename, extra_csv_filenames=extra_csv_filenames,
    )
    X_all, Y_all, anchor_dates = make_windows(
        input_matrix, window, horizon, dates, target_matrix=target_matrix,
    )
    n_samples = X_all.shape[0]
    n_input_channels = X_all.shape[2]
    n_output_channels = Y_all.shape[2]
    n_channels_per_var = n_output_channels  # C = number of counties
    print(f"Loaded {input_matrix.shape[0]} days x {n_channels_per_var} counties")
    print(f"Input variables ({len(variable_labels)}): {variable_labels}")
    print(f"Windowed: {n_samples} samples of shape ({window}, {n_input_channels}) "
          f"-> ({horizon}, {n_output_channels})")
    if baseline in _TRAINED_BASELINES:
        if normalize:
            applied = [
                f"{lab}:{_PER_VARIABLE_TRANSFORM.get(lab, 'identity')}"
                for lab in variable_labels
            ]
            print(f"Normalisation: per-county z-score (fit per fold). "
                  f"Per-variable transforms before z-score: {applied}")
        else:
            print("Normalisation: off")

    set_seed(seed)
    fold_results = []
    for fi, (tr, te) in enumerate(walk_forward_folds(n_samples, folds), start=1):
        print(f"\nFold {fi}/{folds}: train={len(tr)} samples, test={len(te)} samples")

        if baseline == "mean":
            pred = MeanBaseline(horizon, n_output_channels).predict(X_all[te])
        elif baseline == "persistence":
            pred = PersistenceBaseline(horizon, n_output_channels).predict(X_all[te])
        elif baseline in _TRAINED_BASELINES:
            set_seed(seed + fi)  # fold-specific seed for trainable variance
            X_tr, Y_tr = X_all[tr], Y_all[tr]
            X_te = X_all[te]
            if normalize:
                x_mean, x_std, transforms = fit_scaler(
                    X_tr, variable_labels, n_channels_per_var,
                )
                # Target uses the first n_output channels of the input
                # scaler. The target variable's transform is "identity"
                # so no inverse-transform of log1p is needed at predict
                # time.
                y_mean = x_mean[:n_output_channels]
                y_std = x_std[:n_output_channels]
                X_tr_in = apply_scaler(X_tr, x_mean, x_std, transforms, n_channels_per_var)
                Y_tr_in = (Y_tr - y_mean) / y_std
                X_te_in = apply_scaler(X_te, x_mean, x_std, transforms, n_channels_per_var)
            else:
                X_tr_in, Y_tr_in, X_te_in = X_tr, Y_tr, X_te
                y_mean = y_std = None

            model_init_kwargs = _build_model_init_kwargs(
                baseline,
                window=window, horizon=horizon,
                n_input_channels=n_input_channels, n_output_channels=n_output_channels,
                hidden=hidden, n_blocks=n_blocks, n_layers=n_layers,
                d_model=d_model, n_heads=n_heads, n_enc_layers=n_enc_layers,
                ff=ff, dropout=dropout,
                patch_len=patch_len, stride=stride,
            )
            model_cls = {
                "linear_regression": LinearBaseline,
                "nbeats": NBEATSBaseline,
                "itransformer": ITransformerBaseline,
                "patchtst": PatchTSTBaseline,
            }[baseline]
            model: nn.Module = model_cls(**model_init_kwargs)
            train_loader = DataLoader(
                WindowedDataset(X_tr_in, Y_tr_in),
                batch_size=batch_size, shuffle=True, drop_last=False,
            )
            train_model(
                model, train_loader,
                epochs=epochs, lr=lr, weight_decay=weight_decay,
                decay=decay, huber_delta=huber_delta,
                horizon=horizon, device=device,
            )
            pred_n = predict_torch(model, X_te_in, device)
            pred = inverse_scaler(pred_n, y_mean, y_std) if normalize else pred_n

            # Optional per-fold checkpoint with scaler + metadata so the
            # exact trained instance can be rehydrated for later
            # inspection or re-evaluation.
            if save_weights:
                suffix = f"_{label}" if label else ""
                ckpt_path = (
                    Path(output_dir) / "checkpoints"
                    / f"{baseline}{suffix}_fold{fi}.pt"
                )
                scaler_payload = None
                if normalize:
                    scaler_payload = {
                        "x_mean": x_mean,
                        "x_std": x_std,
                        "transforms": transforms,
                        "n_channels_per_var": n_channels_per_var,
                        "y_mean": y_mean,
                        "y_std": y_std,
                    }
                train_date_range_for_ckpt = [
                    anchor_dates[tr[0]].strftime("%Y-%m-%d"),
                    anchor_dates[tr[-1]].strftime("%Y-%m-%d"),
                ] if len(tr) else None
                save_fold_checkpoint(
                    ckpt_path,
                    baseline=baseline, label=label, fold=fi,
                    model=model, model_init_kwargs=model_init_kwargs,
                    scaler=scaler_payload,
                    variable_labels=variable_labels,
                    counties=counties,
                    window=window, horizon=horizon,
                    epochs=epochs, seed=seed + fi,
                    train_date_range=train_date_range_for_ckpt,
                )
                print(f"    saved checkpoint: {ckpt_path}")
        else:
            raise ValueError(f"unknown baseline: {baseline!r}")

        metrics = compute_metrics(pred, Y_all[te], counties)
        metrics["fold"] = fi
        metrics["n_train_samples"] = int(len(tr))
        metrics["n_test_samples"] = int(len(te))
        metrics["train_date_range"] = [
            anchor_dates[tr[0]].strftime("%Y-%m-%d"),
            anchor_dates[tr[-1]].strftime("%Y-%m-%d"),
        ] if len(tr) else None
        metrics["test_date_range"] = [
            anchor_dates[te[0]].strftime("%Y-%m-%d"),
            anchor_dates[te[-1]].strftime("%Y-%m-%d"),
        ] if len(te) else None
        fold_results.append(metrics)
        print(f"  RMSE={metrics['rmse_overall']:.3f} degC, "
              f"MAE={metrics['mae_overall']:.3f} degC")

    overall_rmse = float(np.mean([f["rmse_overall"] for f in fold_results]))
    overall_mae = float(np.mean([f["mae_overall"] for f in fold_results]))
    per_h_rmse = np.mean(
        np.stack([f["rmse_per_horizon"] for f in fold_results]), axis=0
    ).tolist()
    per_h_mae = np.mean(
        np.stack([f["mae_per_horizon"] for f in fold_results]), axis=0
    ).tolist()

    result = {
        "baseline": baseline,
        "label": label,
        "variable_labels": variable_labels,
        "window": window,
        "horizon": horizon,
        "folds": folds,
        "decay": decay,
        "n_input_channels": n_input_channels,
        "n_output_channels": n_output_channels,
        "counties": counties,
        "n_samples_total": n_samples,
        "aggregate_across_folds": {
            "rmse_overall_mean": overall_rmse,
            "mae_overall_mean": overall_mae,
            "rmse_per_horizon_mean": per_h_rmse,
            "mae_per_horizon_mean": per_h_mae,
        },
        "per_fold": fold_results,
    }
    if baseline in _TRAINED_BASELINES:
        result["training"] = {
            "epochs": epochs, "lr": lr, "weight_decay": weight_decay,
            "loss": "horizon_weighted_huber", "huber_delta": huber_delta,
            "batch_size": batch_size, "normalize": normalize, "seed": seed,
        }
        if baseline == "nbeats":
            result["training"].update({
                "n_blocks": n_blocks, "n_layers": n_layers, "hidden": hidden,
            })
        if baseline == "itransformer":
            result["training"].update({
                "d_model": d_model, "n_heads": n_heads,
                "n_layers": n_enc_layers, "ff": ff, "dropout": dropout,
            })
        if baseline == "patchtst":
            result["training"].update({
                "patch_len": patch_len, "stride": stride,
                "d_model": d_model, "n_heads": n_heads,
                "n_layers": n_enc_layers, "ff": ff, "dropout": dropout,
            })

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    label_suffix = f"_{label}" if label else ""
    out_path = out_dir / f"{baseline}{label_suffix}_metrics.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {out_path}")
    print(f"Mean across folds: RMSE={overall_rmse:.3f} degC, MAE={overall_mae:.3f} degC")
    return result


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _load_baseline_runs(output_dir: str) -> list:
    """
    Read every {baseline}_metrics.json in `output_dir`, return the
    parsed dicts sorted with closed-form baselines first (so they
    appear at the top of plot legends).
    """
    out_dir = Path(output_dir)
    paths = sorted(out_dir.glob("*_metrics.json"))
    runs: list = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            runs.append(json.load(f))
    runs.sort(
        key=lambda r: (
            r["baseline"] not in _CLOSED_FORM_BASELINES,
            r["baseline"],
            r.get("label", ""),
        )
    )
    return runs


def _legend_name(r: dict) -> str:
    """
    Build the legend / file-level display name for a metrics run.
    Suffixes the label (if non-empty) in square brackets so multiple
    runs of the same baseline can be distinguished on the same plot.
    """
    base = r["baseline"]
    lbl = r.get("label", "")
    return f"{base} [{lbl}]" if lbl else base


def plot_per_fold(output_dir: str, save: bool = True, keep_open: bool = False) -> None:
    """
    Per-fold per-horizon visualisation. One figure per metric (RMSE,
    MAE); within each figure a grid of subplots, one subplot per fold,
    each showing every baseline's per-horizon curve on that fold's
    test slice. Subplots share both x and y axes so absolute error
    levels are comparable across folds.

    For trained baselines, fold N's curve comes from a model trained
    from scratch on fold N's train slice - so the differences across
    subplots reflect training-set-size effects, while differences
    within a subplot reflect model-architecture effects.

    Writes:
        per_horizon_rmse_per_fold.png
        per_horizon_mae_per_fold.png
    """
    import matplotlib.pyplot as plt

    runs = _load_baseline_runs(output_dir)
    if not runs:
        print(f"No baseline metrics found in {output_dir}; skipping per-fold plot.")
        return
    out_dir = Path(output_dir)

    n_folds = runs[0]["folds"]
    if any(r["folds"] != n_folds for r in runs):
        print("WARNING: baselines disagree on fold count; using "
              f"{n_folds} from {runs[0]['baseline']}")

    # Grid layout: pair up folds where possible (2 cols for <=4 folds).
    cols = min(2, n_folds) if n_folds <= 4 else 3
    rows = (n_folds + cols - 1) // cols

    for metric_label, h_key in [("RMSE", "rmse_per_horizon"),
                                ("MAE", "mae_per_horizon")]:
        # Scan every run + every fold once up front so the y-axis is a
        # SHARED, EXPLICIT range across all subplots (and across re-runs
        # with different baseline sets). Adding a small headroom multiplier
        # so the worst curve isn't pinned to the top edge.
        global_y_max = max(
            max(fold[h_key]) for r in runs for fold in r["per_fold"]
        )
        y_top = global_y_max * 1.08
        # Round up to a whole number of degC for tick-friendliness.
        y_top = float(np.ceil(y_top))

        fig, axes = plt.subplots(
            rows, cols,
            figsize=(6.5 * cols, 4.5 * rows),
            sharex=True, sharey=True,
            squeeze=False,
        )
        axes_flat = axes.flatten()

        for fi in range(n_folds):
            ax = axes_flat[fi]
            max_h = 0
            n_train = None
            for r in runs:
                fold = r["per_fold"][fi]
                curve = fold[h_key]
                if n_train is None:
                    n_train = fold["n_train_samples"]
                x = list(range(1, len(curve) + 1))
                style = "--" if r["baseline"] in _CLOSED_FORM_BASELINES else "-"
                ax.plot(x, curve, style, linewidth=2, label=_legend_name(r))
                max_h = max(max_h, len(curve))
            ax.set_title(f"Fold {fi + 1}   (train n={n_train})")
            ax.set_xticks(range(1, max_h + 1))
            ax.set_ylim(0.0, y_top)
            ax.grid(True, alpha=0.3)
            # Only the leftmost column carries the y-label, only the
            # bottom row carries the x-label - cleaner with sharex/sharey.
            if fi % cols == 0:
                ax.set_ylabel(f"{metric_label} (degC)")
            if fi // cols == rows - 1:
                ax.set_xlabel("Horizon step (days ahead)")

        # Hide any unused subplot cells (when n_folds doesn't divide evenly).
        for i in range(n_folds, len(axes_flat)):
            axes_flat[i].set_visible(False)

        # Single shared legend at the top - the baseline list is the
        # same in every subplot.
        handles, labels = axes_flat[0].get_legend_handles_labels()
        fig.legend(
            handles, labels,
            loc="upper center", ncol=min(len(runs), 6),
            bbox_to_anchor=(0.5, 1.02),
            frameon=False,
        )
        fig.suptitle(
            f"Per-fold per-horizon {metric_label}",
            y=1.06, fontsize=14,
        )
        fig.tight_layout()

        if save:
            out_path = out_dir / f"per_horizon_{metric_label.lower()}_per_fold.png"
            fig.savefig(out_path, dpi=150, bbox_inches="tight")
            print(f"Wrote {out_path}")
        if not keep_open:
            plt.close(fig)


def plot_fold_distributions(
    output_dir: str = "baselines",
    date_folder: str = "date",
    csv_filename: str = "daily_county_mean.csv",
    window: int = 10,
    horizon: int = 10,
    folds: int = 4,
    save: bool = True,
    keep_open: bool = False,
) -> None:
    """
    Visualise how the train and test temperature distributions shift
    across the walk-forward folds. Produces a grid of subplots (one
    per fold) showing the train and test value histograms overlaid,
    with date ranges and sample counts in the subplot titles and the
    overall data span in the figure title.

    The values pooled into each (fold, split) histogram are all
    temperatures across X and Y of every windowed sample in that
    split (all counties, all timesteps), in original units (degC).
    This is the raw data the model is fit to vs the raw data it is
    evaluated against - useful for spotting distribution shift
    between train and test (e.g. fold 1 trains on winter and tests
    on spring; fold 4 covers most of the year for training and
    tests on autumn-winter).

    Reads the matrix directly via `load_county_matrix` rather than
    the metrics JSONs, so it works before any baseline has been run
    (useful for sanity-checking the fold structure up front).
    """
    import matplotlib.pyplot as plt

    # Single-variable view for the fold-distribution plot: ignore
    # `extra_csv_filenames` here; this figure is always about the
    # target variable's value distribution per fold.
    loaded = load_county_matrix(date_folder, csv_filename, extra_csv_filenames=None)
    matrix, dates = loaded[1], loaded[2]   # target_matrix, dates
    X_all, Y_all, _ = make_windows(matrix, window, horizon, dates)
    n_samples = X_all.shape[0]

    cols = min(2, folds) if folds <= 4 else 3
    rows = (folds + cols - 1) // cols

    fig, axes = plt.subplots(
        rows, cols,
        figsize=(6.5 * cols, 4.5 * rows),
        sharex=True, sharey=True,
        squeeze=False,
    )
    axes_flat = axes.flatten()

    fold_iter = list(walk_forward_folds(n_samples, folds))
    # Shared bin edges across all subplots so the histograms are visually comparable.
    bins = np.linspace(matrix.min(), matrix.max(), 50)

    # Total raw-data span this plot summarises, for the suptitle.
    overall_first = dates[0]
    overall_last = dates[-1]

    # Helper: for a contiguous block of sample indices, return the
    # actual first/last calendar dates covered by the pooled X+Y values
    # of those samples. Sample i spans dates[i .. i+W+H-1] (input
    # window + target window), so the block's raw-data span is
    # dates[indices[0]] .. dates[indices[-1] + W + H - 1].
    def _block_date_range(indices):
        first_day = dates[indices[0]]
        last_day = dates[indices[-1] + window + horizon - 1]
        return first_day, last_day

    for fi, (tr, te) in enumerate(fold_iter):
        ax = axes_flat[fi]

        # Pool X and Y for each split. We use both because the loss is
        # computed over both during training; for the test split, Y is
        # the evaluation target while X is what the model sees - both
        # define the (fold, split) data regime.
        train_vals = np.concatenate([X_all[tr].ravel(), Y_all[tr].ravel()])
        test_vals = np.concatenate([X_all[te].ravel(), Y_all[te].ravel()])

        tr_first, tr_last = _block_date_range(tr)
        te_first, te_last = _block_date_range(te)

        ax.hist(train_vals, bins=bins, alpha=0.5, density=True,
                color="steelblue",
                label=f"train: {len(tr)} samples, "
                      f"mean = {train_vals.mean():.1f} degC")
        ax.hist(test_vals, bins=bins, alpha=0.5, density=True,
                color="firebrick",
                label=f"test:  {len(te)} samples, "
                      f"mean = {test_vals.mean():.1f} degC")
        # Mean markers
        ax.axvline(train_vals.mean(), color="steelblue", linestyle=":", linewidth=1.2)
        ax.axvline(test_vals.mean(), color="firebrick", linestyle=":", linewidth=1.2)

        ax.set_title(
            f"Fold {fi + 1}\n"
            f"train data span: {tr_first.strftime('%Y-%m-%d')} .. "
            f"{tr_last.strftime('%Y-%m-%d')}\n"
            f"test data span:  {te_first.strftime('%Y-%m-%d')} .. "
            f"{te_last.strftime('%Y-%m-%d')}",
            fontsize=10,
        )
        if fi % cols == 0:
            ax.set_ylabel("Density")
        if fi // cols == rows - 1:
            ax.set_xlabel("Temperature (degC)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9, loc="upper left")

    # Hide unused subplot cells if folds doesn't fill the grid.
    for i in range(folds, len(axes_flat)):
        axes_flat[i].set_visible(False)

    fig.suptitle(
        f"Train vs test value distributions per fold\n"
        f"Data span: {overall_first.strftime('%Y-%m-%d')} "
        f".. {overall_last.strftime('%Y-%m-%d')}  "
        f"({len(dates)} days, {n_samples} windowed samples)   |   "
        f"W={window}, H={horizon}, {folds} folds",
        fontsize=13, y=1.04,
    )
    fig.tight_layout()

    if save:
        out_path = Path(output_dir) / "fold_distributions.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        print(f"Wrote {out_path}")
    if not keep_open:
        plt.close(fig)


def plot_class_distributions(
    output_dir: str, save: bool = True, keep_open: bool = False,
) -> None:
    """
    For every metrics JSON in `output_dir` that carries class counts,
    produce a per-fold figure of the temperature-class distribution
    of predictions vs targets.

    Layout (per metrics file):
        2 x ceil(folds/2) grid of subplots, one per fold. In each
        subplot, the 32 bins from `temp_class_labels()` are drawn
        side-by-side: a colour-coded solid bar for the target counts
        and a hatched bar for the prediction counts. The colour
        palette is `matplotlib.cm.RdYlBu_r` so cold (blue) -> warm
        (yellow) -> hot (red) reads naturally.

    Output naming:
        class_distribution_{baseline}{_label}.png  for every JSON
        class_distribution_target.png              once, for the
            target-only reference (target counts are identical across
            baselines that share the same window/horizon/folds).

    Newer pipeline runs include target_class_counts and
    prediction_class_counts in every per_fold[i] block; files written
    before step 9 skip silently.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    runs = _load_baseline_runs(output_dir)
    if not runs:
        print(f"No baseline metrics found in {output_dir}; skipping class plot.")
        return
    out_dir = Path(output_dir)

    labels = temp_class_labels()
    n_bins = len(labels)
    x = np.arange(n_bins)
    cmap = plt.get_cmap("RdYlBu_r", n_bins)
    colors = [cmap(i) for i in range(n_bins)]

    # Target counts are baseline-agnostic; emit a reference figure from
    # the first JSON that has them, then move on to per-baseline plots.
    ref = next(
        (r for r in runs
         if r.get("per_fold") and "target_class_counts" in r["per_fold"][0]),
        None,
    )
    if ref is None:
        print("Class counts not present in any metrics file - skipping. "
              "Re-run training so the step-9 fields land in the JSON.")
        return
    n_folds = ref["folds"]
    cols = min(2, n_folds) if n_folds <= 4 else 3
    rows = (n_folds + cols - 1) // cols

    # Compute one global y-max across every fold of every loaded run, so
    # every figure produced below (target reference + per-baseline ones)
    # shares the same y-axis. Bars are colour-coded by class, so a
    # fixed scale makes 'this baseline over-predicts the [0, 2) bin
    # versus that one' read off at a glance.
    global_count_max = 0
    for r in runs:
        if not r.get("per_fold") or "target_class_counts" not in r["per_fold"][0]:
            continue
        for fold in r["per_fold"]:
            global_count_max = max(
                global_count_max,
                max(fold["target_class_counts"]),
                max(fold["prediction_class_counts"]),
            )
    y_top = float(np.ceil(global_count_max * 1.05 / 100.0) * 100)  # round up to a 100

    # --- target-only reference figure ---
    fig, axes = plt.subplots(
        rows, cols, figsize=(8 * cols, 4 * rows),
        sharex=True, sharey=True, squeeze=False,
    )
    axes_flat = axes.flatten()
    for fi in range(n_folds):
        ax = axes_flat[fi]
        counts = np.asarray(ref["per_fold"][fi]["target_class_counts"])
        ax.bar(x, counts, width=0.85, color=colors,
               edgecolor="black", linewidth=0.4)
        n_train = ref["per_fold"][fi].get("n_train_samples", "?")
        ax.set_title(f"Fold {fi + 1}  (train n={n_train})", fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=90, fontsize=7)
        ax.set_ylim(0.0, y_top)
        ax.grid(True, alpha=0.3, axis="y")
        if fi % cols == 0:
            ax.set_ylabel("count")
    for i in range(n_folds, len(axes_flat)):
        axes_flat[i].set_visible(False)
    fig.suptitle(
        "Test-set target class distribution per fold\n"
        f"Classes: <{TEMP_CLASS_MIN:.0f}, "
        f"{TEMP_CLASS_WIDTH:.0f}-degC bins from "
        f"{TEMP_CLASS_MIN:.0f} to {TEMP_CLASS_MAX:.0f}, "
        f">={TEMP_CLASS_MAX:.0f}",
        fontsize=13, y=1.02,
    )
    fig.tight_layout()
    if save:
        out_path = out_dir / "class_distribution_target.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        print(f"Wrote {out_path}")
    if not keep_open:
        plt.close(fig)

    # --- per (baseline, label) target-vs-prediction figures ---
    for r in runs:
        if not r.get("per_fold"):
            continue
        if "target_class_counts" not in r["per_fold"][0]:
            continue
        name = _legend_name(r)
        n_folds_r = r["folds"]
        fig, axes = plt.subplots(
            rows, cols, figsize=(8 * cols, 4 * rows),
            sharex=True, sharey=True, squeeze=False,
        )
        axes_flat = axes.flatten()
        for fi in range(n_folds_r):
            ax = axes_flat[fi]
            t_counts = np.asarray(r["per_fold"][fi]["target_class_counts"])
            p_counts = np.asarray(r["per_fold"][fi]["prediction_class_counts"])
            width = 0.4
            ax.bar(x - width / 2, t_counts, width, color=colors,
                   edgecolor="black", linewidth=0.4, label="_target")
            ax.bar(x + width / 2, p_counts, width, color=colors,
                   edgecolor="black", linewidth=0.4, alpha=0.55,
                   hatch="///", label="_prediction")
            n_train = r["per_fold"][fi].get("n_train_samples", "?")
            ax.set_title(f"Fold {fi + 1}  (train n={n_train})", fontsize=10)
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=90, fontsize=7)
            ax.set_ylim(0.0, y_top)
            ax.grid(True, alpha=0.3, axis="y")
            if fi % cols == 0:
                ax.set_ylabel("count")
        for i in range(n_folds_r, len(axes_flat)):
            axes_flat[i].set_visible(False)

        legend_elems = [
            Patch(facecolor="gray", edgecolor="black", label="target"),
            Patch(facecolor="gray", edgecolor="black", alpha=0.55,
                  hatch="///", label="prediction"),
        ]
        fig.legend(
            handles=legend_elems, loc="upper center", ncol=2,
            bbox_to_anchor=(0.5, 1.02), frameon=False,
        )
        fig.suptitle(
            f"Class distribution: {name}",
            fontsize=13, y=1.06,
        )
        fig.tight_layout()
        if save:
            label_part = r.get("label", "")
            label_suffix = f"_{label_part}" if label_part else ""
            out_path = out_dir / f"class_distribution_{r['baseline']}{label_suffix}.png"
            fig.savefig(out_path, dpi=150, bbox_inches="tight")
            print(f"Wrote {out_path}")
        if not keep_open:
            plt.close(fig)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Run forecasting baselines on the (T, C) county-day mean "
            "temperature matrix, or regenerate the comparison plots "
            "from existing metrics JSONs. Training and plotting are "
            "decoupled: --baseline trains and writes JSONs; --plot_only "
            "reads the JSONs and (re)writes the figures. Add --show to "
            "open interactive zoomable matplotlib windows."
        )
    )
    p.add_argument(
        "--baseline", default=None,
        choices=_ALL_BASELINES + ["all"],
        help="Which baseline to run, or 'all' to run every baseline in "
             "sequence. Required unless --plot_only is set.",
    )
    p.add_argument("--window", type=int, default=10,
                   help="Input window length W (default 10).")
    p.add_argument("--horizon", type=int, default=10,
                   help="Forecast horizon H (default 10).")
    p.add_argument("--folds", type=int, default=4,
                   help="Walk-forward folds (default 4).")
    p.add_argument("--decay", type=float, default=0.05,
                   help="Loss horizon decay rate; w_t = exp(-decay*t). "
                        "Set to 0 for unweighted MSE (default 0.05).")

    # Training (ignored by closed-form baselines)
    p.add_argument("--epochs", type=int, default=300,
                   help="Training epochs per fold (default 300).")
    p.add_argument("--lr", type=float, default=1e-3,
                   help="AdamW learning rate (default 1e-3).")
    p.add_argument("--weight_decay", type=float, default=1e-4,
                   help="AdamW weight decay (default 1e-4).")
    p.add_argument("--huber_delta", type=float, default=1.0,
                   help="Huber-loss transition threshold delta. Errors "
                        "with |a| <= delta use the quadratic branch "
                        "(MSE-like); larger errors use the linear "
                        "branch (MAE-like). Default 1.0 - one z-score "
                        "std, since the loss is computed on normalised "
                        "data. Raise toward 2.0 for more MSE-like "
                        "behaviour, lower toward 0.5 for more MAE-like.")
    p.add_argument("--batch_size", type=int, default=32,
                   help="Training batch size (default 32).")
    p.add_argument("--no_normalize", action="store_true",
                   help="Disable per-county z-score normalisation. "
                        "Normalisation is on by default; (mu_i, sigma_i) are "
                        "fit per training fold and reversed before metrics.")
    p.add_argument("--seed", type=int, default=42,
                   help="RNG seed for reproducibility (default 42). Fold "
                        "i uses seed+i for trained baselines.")

    # N-BEATS
    p.add_argument("--hidden", type=int, default=128,
                   help="[nbeats] hidden dim of the FC stack (default 128).")
    p.add_argument("--n_blocks", type=int, default=3,
                   help="[nbeats] number of generic blocks (default 3).")
    p.add_argument("--n_layers", type=int, default=4,
                   help="[nbeats] FC layers per block (default 4).")

    # iTransformer + PatchTST share the encoder hyperparameters
    p.add_argument("--d_model", type=int, default=128,
                   help="[itransformer/patchtst] model dim (default 128).")
    p.add_argument("--n_heads", type=int, default=4,
                   help="[itransformer/patchtst] attention heads (default 4).")
    p.add_argument("--n_enc_layers", type=int, default=3,
                   help="[itransformer/patchtst] encoder layers (default 3).")
    p.add_argument("--ff", type=int, default=256,
                   help="[itransformer/patchtst] feedforward dim (default 256).")
    p.add_argument("--dropout", type=float, default=0.1,
                   help="[itransformer/patchtst] dropout rate (default 0.1).")

    # PatchTST patching
    p.add_argument("--patch_len", type=int, default=4,
                   help="[patchtst] tokens per patch (default 4; must be "
                        "<= --window).")
    p.add_argument("--stride", type=int, default=2,
                   help="[patchtst] stride between consecutive patches "
                        "(default 2). Together with --patch_len controls "
                        "the number of temporal tokens per county: "
                        "n_patches = (window - patch_len) // stride + 1. "
                        "For W=10 the defaults give 4 patches.")

    # I/O
    p.add_argument("--date_folder", type=str, default="date",
                   help="Folder holding the daily_county_mean.csv input.")
    p.add_argument("--csv_filename", type=str, default="daily_county_mean.csv",
                   help="Target-variable matrix CSV filename inside "
                        "--date_folder. The first variable; always also "
                        "included as the first channel block of the input.")
    p.add_argument("--extra_csvs", type=str, nargs="*", default=None,
                   help="Optional list of additional per-county-day "
                        "variable CSVs inside --date_folder (e.g. "
                        "'daily_county_precip.csv daily_county_wind.csv "
                        "daily_county_nebulosity.csv'). Each is stacked "
                        "along the channel axis after the target, giving "
                        "an input tensor of shape (W, C*K). The output "
                        "remains (H, C) and covers only the target. "
                        "Per-variable normalisation transforms are applied "
                        "before z-score (precip -> log1p; others -> identity).")
    p.add_argument("--output_dir", type=str, default="baselines",
                   help="Where to write {baseline}_metrics.json and plots.")
    p.add_argument("--device", type=str, default="auto",
                   choices=["auto", "cpu", "cuda"],
                   help="Compute device for trained baselines.")
    p.add_argument("--plot_only", action="store_true",
                   help="Skip the run loop entirely and just regenerate "
                        "the comparison plots from existing "
                        "{baseline}_metrics.json files in --output_dir. "
                        "Always (re)writes the PNGs. Combine with --show "
                        "to also open interactive zoomable windows.")
    p.add_argument("--show", action="store_true",
                   help="In --plot_only mode, open interactive matplotlib "
                        "windows after saving the PNGs. Each window has "
                        "the standard zoom/pan/home toolbar so you can "
                        "drill into regions where baselines cross. The "
                        "command blocks until you close every window.")
    p.add_argument("--label", type=str, default="",
                   help="Optional suffix appended to the metrics JSON "
                        "filename and any saved checkpoints, so before/"
                        "after runs (e.g. 'temp_only' vs 'with_aux') can "
                        "coexist under --output_dir without overwriting "
                        "each other. Empty (default) keeps the original "
                        "'{baseline}_metrics.json' name.")
    p.add_argument("--save_weights", action="store_true",
                   help="Save a per-(baseline, fold) checkpoint under "
                        "{output_dir}/checkpoints/ containing the model's "
                        "state_dict, the per-fold scaler stats, and the "
                        "constructor kwargs needed to rehydrate the model "
                        "later for inference. Disabled by default - "
                        "checkpoints grow with model size and aren't "
                        "needed for the comparison plot.")
    p.add_argument("--autoregressive_total_days", type=int, default=None,
                   help="Mode switch: run autoregressive multi-step "
                        "rollout instead of training. Loads every "
                        "trained-baseline checkpoint matching "
                        "--autoregressive_fold from "
                        "{output_dir}/checkpoints/, feeds each model's "
                        "predictions back as input for the next chunk, "
                        "and writes one comparison figure per checkpoint. "
                        "Requires --save_weights to have been used at "
                        "training time, plus --autoregressive_start_date.")
    p.add_argument("--autoregressive_start_date", type=str, default=None,
                   help="YYYY-MM-DD date for the first day of the initial "
                        "input window in autoregressive mode. Days "
                        "[start_date, start_date + W - 1] are the known "
                        "input; days [start_date + W, "
                        "start_date + W + total_days - 1] are predicted.")
    p.add_argument("--autoregressive_fold", type=int, default=4,
                   help="Which fold's checkpoint to use for the "
                        "autoregressive rollout (default 4 - the "
                        "largest-training-set / deployable model).")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    if args.plot_only:
        print(f"Plot-only mode: regenerating figures from {args.output_dir}")
        plot_per_fold(args.output_dir, keep_open=args.show)
        plot_fold_distributions(
            output_dir=args.output_dir,
            date_folder=args.date_folder,
            csv_filename=args.csv_filename,
            window=args.window,
            horizon=args.horizon,
            folds=args.folds,
            keep_open=args.show,
        )
        plot_class_distributions(args.output_dir, keep_open=args.show)
        if args.show:
            import matplotlib.pyplot as plt
            print("Opening interactive windows. Close them to exit.")
            plt.show()
        return

    if args.autoregressive_total_days is not None:
        if args.autoregressive_start_date is None:
            raise SystemExit(
                "ERROR: --autoregressive_total_days requires "
                "--autoregressive_start_date YYYY-MM-DD as well."
            )
        device = args.device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        run_autoregressive(
            output_dir=args.output_dir,
            date_folder=args.date_folder,
            csv_filename=args.csv_filename,
            extra_csv_filenames=args.extra_csvs,
            start_date=args.autoregressive_start_date,
            total_days=args.autoregressive_total_days,
            fold=args.autoregressive_fold,
            device=device,
        )
        return

    if args.baseline is None:
        raise SystemExit(
            "ERROR: --baseline is required unless --plot_only is set. "
            "Choose one of: " + ", ".join(_ALL_BASELINES + ["all"])
        )

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    print(f"Window={args.window}, Horizon={args.horizon}, Folds={args.folds}, "
          f"Decay={args.decay}")

    targets = _ALL_BASELINES if args.baseline == "all" else [args.baseline]
    if args.extra_csvs:
        # Closed-form baselines slice X[..., :n_output] before computing
        # their statistic, so the auxiliary channels never reach them and
        # their predictions are essentially identical between temp_only
        # and with_aux runs (modulo a 1-sample fold-edge shift from the
        # date intersection). Skipping them keeps the comparison plot
        # uncluttered.
        skipped = [b for b in targets if b in _CLOSED_FORM_BASELINES]
        if skipped:
            print(
                f"Note: skipping closed-form baselines {skipped} for this "
                f"multi-variable run. They are scale-equivariant by design "
                f"and ignore --extra_csvs, so their numbers come from the "
                f"matching temp_only run (the comparison plot picks up "
                f"both files automatically)."
            )
        targets = [b for b in targets if b not in _CLOSED_FORM_BASELINES]
        if not targets:
            print(
                "ERROR: no trainable baselines remain after filtering "
                "closed-form ones. Pick a trained baseline by name, or "
                "run without --extra_csvs."
            )
            return

    for name in targets:
        print(f"\n{'=' * 60}\nBaseline: {name}\n{'=' * 60}")
        run_baseline(
            name,
            date_folder=args.date_folder,
            csv_filename=args.csv_filename,
            extra_csv_filenames=args.extra_csvs,
            window=args.window,
            horizon=args.horizon,
            folds=args.folds,
            decay=args.decay,
            epochs=args.epochs,
            lr=args.lr,
            weight_decay=args.weight_decay,
            huber_delta=args.huber_delta,
            batch_size=args.batch_size,
            normalize=not args.no_normalize,
            hidden=args.hidden,
            n_blocks=args.n_blocks,
            n_layers=args.n_layers,
            d_model=args.d_model,
            n_heads=args.n_heads,
            n_enc_layers=args.n_enc_layers,
            ff=args.ff,
            dropout=args.dropout,
            patch_len=args.patch_len,
            stride=args.stride,
            device=device,
            seed=args.seed,
            output_dir=args.output_dir,
            label=args.label,
            save_weights=args.save_weights,
        )

    print(
        f"\nTraining complete. To view the per-fold plots, run:\n"
        f"  python -m prompting.utils.baselines --plot_only             "
        f"# regenerate PNGs only\n"
        f"  python -m prompting.utils.baselines --plot_only --show      "
        f"# also open interactive zoomable windows\n"
        f"\nFold 4 represents the largest-training-set model and is the "
        f"closest match to what would be deployed for future predictions."
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Plot the three theory-neutral macroeconomic regularities.

The figure intentionally follows the visual format of
``validate_1994-2003_smoothed.py``: a three-panel hexbin layout, red fitted
relationships, individual count colorbars, and a two-line overall title.

The default analysis window is tick 401--1000 (inclusive): all 600 observations
after the model's explicitly configured 400-tick burn-in.
R-squared and correlation coefficients are deliberately omitted. Each panel
reports the complete fitted equation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm
from scipy import stats
from scipy.optimize import curve_fit


CSV_NAME = "1994-2003-theory.csv"
OUTPUT_NAME = "fig06_theory_neutral_regularities.png"
START_TICK = 401
END_TICK = 1000
EXPECTED_RUNS = 100
HEXBIN_GRIDSIZE = 52
FIT_COLOUR = "#D7191C"
DENSITY_CMAP = "YlGnBu_r"


def locate_project_root(script_path: Path) -> Path:
    """Return the project root when this script is stored in analysis/."""
    return script_path.parent.parent


def locate_default_input(script_path: Path) -> Path:
    """Return <project root>/data/validation/1994-2003-theory.csv."""
    project_root = locate_project_root(script_path)
    return project_root / "data" / "validation" / CSV_NAME


def locate_default_output(script_path: Path) -> Path:
    """Return <project root>/outputs/fig06_theory_neutral_regularities.png."""
    project_root = locate_project_root(script_path)
    return project_root / "outputs" / OUTPUT_NAME


def exp_curve(x: np.ndarray, a: float, b: float) -> np.ndarray:
    """Exponential Beveridge-curve specification used in the earlier figure."""
    return a * np.exp(b * x)


def load_analysis_window(
    csv_path: Path,
    start_tick: int,
    end_tick: int,
    expected_runs: int,
) -> pd.DataFrame:
    """Read the NetLogo table and retain the requested post-burn-in window."""
    data = pd.read_csv(csv_path, skiprows=6, low_memory=False)
    required = [
        "[run number]",
        "ticks",
        "delta-unemployment",
        "total-unemployment",
        "vacancy-rate",
        "gdp-growth",
        "inflation",
    ]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    for column in required:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    window = data.loc[data["ticks"].between(start_tick, end_tick), required].copy()
    window = window.dropna().sort_values(["[run number]", "ticks"])

    run_sizes = window.groupby("[run number]")["ticks"].nunique()
    expected_ticks = end_tick - start_tick + 1
    if len(run_sizes) != expected_runs or not run_sizes.eq(expected_ticks).all():
        raise ValueError(
            f"Expected {expected_runs} complete runs with "
            f"{expected_ticks} ticks each; observed {len(run_sizes)} runs with "
            f"tick counts from {run_sizes.min()} to {run_sizes.max()}."
        )
    return window


def add_count_colorbar(fig: plt.Figure, axis: plt.Axes, hexbin) -> None:
    colourbar = fig.colorbar(hexbin, ax=axis, fraction=0.038, pad=0.018)
    colourbar.set_label("Count", fontsize=8)
    colourbar.ax.tick_params(labelsize=8)


def linear_equation_label(intercept: float, slope: float) -> str:
    """Format a complete linear equation in the conventional y = ax + b order."""
    operator = "+" if intercept >= 0 else "-"
    return rf"Fit: $y = {slope:.4f}x {operator} {abs(intercept):.4f}$"


def exponential_equation_label(a: float, b: float) -> str:
    """Format a complete exponential fitted equation for a plot legend."""
    return rf"Exp. fit: $y = {a:.4f}\mathrm{{e}}^{{{b:.4f}x}}$"


def make_figure(
    data: pd.DataFrame,
    output_path: Path,
    start_tick: int,
    end_tick: int,
) -> dict[str, float]:
    """Create and save the three-panel theory-neutral figure."""
    x_okun = data["delta-unemployment"].to_numpy()
    y_okun = data["gdp-growth"].to_numpy()
    x_unemployment = data["total-unemployment"].to_numpy()
    y_vacancy = data["vacancy-rate"].to_numpy()
    y_inflation = data["inflation"].to_numpy()

    okun_fit = stats.linregress(x_okun, y_okun)
    phillips_fit = stats.linregress(x_unemployment, y_inflation)
    beveridge_params, _ = curve_fit(
        exp_curve,
        x_unemployment,
        y_vacancy,
        p0=[float(np.median(y_vacancy)), -5.0],
        maxfev=20_000,
    )
    beveridge_a, beveridge_b = map(float, beveridge_params)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.7,
        }
    )
    figure, axes = plt.subplots(1, 3, figsize=(15.5, 4.9))
    n_runs = int(data["[run number]"].nunique())
    n_ticks = end_tick - start_tick + 1
    figure.suptitle(
        "Macroeconomic Regularities — Theory-Neutral Long Run\n"
        f"(N = {n_runs} runs × {n_ticks} post-burn-in ticks, "
        f"tick {start_tick}–{end_tick})",
        fontsize=11,
        fontweight="bold",
        y=1.02,
    )

    # Okun's law
    axis = axes[0]
    density = axis.hexbin(
        x_okun,
        y_okun,
        gridsize=HEXBIN_GRIDSIZE,
        cmap=DENSITY_CMAP,
        mincnt=1,
        linewidths=0,
        alpha=0.94,
        norm=LogNorm(),
    )
    x_line = np.linspace(float(x_okun.min()), float(x_okun.max()), 300)
    axis.plot(
        x_line,
        okun_fit.intercept + okun_fit.slope * x_line,
        color=FIT_COLOUR,
        linewidth=2,
        label=linear_equation_label(okun_fit.intercept, okun_fit.slope),
    )
    axis.set_title("Okun's Law", fontweight="bold")
    axis.set_xlabel("Δ Unemployment Rate")
    axis.set_ylabel("GDP Growth")
    axis.legend(
        loc="best", fontsize=8, frameon=True, framealpha=0.96,
        edgecolor="#CFCFCF", borderpad=0.4
    )
    add_count_colorbar(figure, axis, density)

    # Beveridge curve: retain the exponential fitted form from the reference figure.
    axis = axes[1]
    density = axis.hexbin(
        x_unemployment,
        y_vacancy,
        gridsize=HEXBIN_GRIDSIZE,
        cmap=DENSITY_CMAP,
        mincnt=1,
        linewidths=0,
        alpha=0.94,
        norm=LogNorm(),
    )
    x_line = np.linspace(float(x_unemployment.min()), float(x_unemployment.max()), 300)
    axis.plot(
        x_line,
        exp_curve(x_line, beveridge_a, beveridge_b),
        color=FIT_COLOUR,
        linewidth=2,
        label=exponential_equation_label(beveridge_a, beveridge_b),
    )
    axis.set_title("Beveridge Curve", fontweight="bold")
    axis.set_xlabel("Unemployment Rate")
    axis.set_ylabel("Vacancy Rate")
    axis.legend(
        loc="best", fontsize=8, frameon=True, framealpha=0.96,
        edgecolor="#CFCFCF", borderpad=0.4
    )
    add_count_colorbar(figure, axis, density)

    # Phillips curve
    axis = axes[2]
    density = axis.hexbin(
        x_unemployment,
        y_inflation,
        gridsize=HEXBIN_GRIDSIZE,
        cmap=DENSITY_CMAP,
        mincnt=1,
        linewidths=0,
        alpha=0.94,
        norm=LogNorm(),
    )
    x_line = np.linspace(float(x_unemployment.min()), float(x_unemployment.max()), 300)
    axis.plot(
        x_line,
        phillips_fit.intercept + phillips_fit.slope * x_line,
        color=FIT_COLOUR,
        linewidth=2,
        label=linear_equation_label(phillips_fit.intercept, phillips_fit.slope),
    )
    axis.set_title("Phillips Curve", fontweight="bold")
    axis.set_xlabel("Unemployment Rate")
    axis.set_ylabel("Inflation Rate")
    axis.legend(
        loc="best", fontsize=8, frameon=True, framealpha=0.96,
        edgecolor="#CFCFCF", borderpad=0.4
    )
    add_count_colorbar(figure, axis, density)

    figure.tight_layout(rect=(0, 0, 1, 0.95), w_pad=2.0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)

    return {
        "okun_intercept": float(okun_fit.intercept),
        "okun_slope": float(okun_fit.slope),
        "beveridge_a": beveridge_a,
        "beveridge_exponent_b": beveridge_b,
        "phillips_intercept": float(phillips_fit.intercept),
        "phillips_slope": float(phillips_fit.slope),
    }


def parse_args() -> argparse.Namespace:
    script_path = Path(__file__).resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=locate_default_input(script_path),
        help=(
            "BehaviorSpace table CSV "
            "(default: <project root>/data/validation/1994-2003-theory.csv)"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=locate_default_output(script_path),
        help=(
            "Destination PNG path "
            "(default: <project root>/outputs/fig06_theory_neutral_regularities.png)"
        ),
    )
    parser.add_argument(
        "--start-tick",
        type=int,
        default=START_TICK,
        help=f"First included tick (default: {START_TICK})",
    )
    parser.add_argument(
        "--end-tick",
        type=int,
        default=END_TICK,
        help=f"Last included tick (default: {END_TICK})",
    )
    parser.add_argument(
        "--expected-runs",
        type=int,
        default=EXPECTED_RUNS,
        help=f"Required number of complete runs (default: {EXPECTED_RUNS})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_tick > args.end_tick:
        raise ValueError("--start-tick must not exceed --end-tick")
    analysis_data = load_analysis_window(
        args.input.resolve(),
        args.start_tick,
        args.end_tick,
        args.expected_runs,
    )
    results = make_figure(
        analysis_data,
        args.output.resolve(),
        args.start_tick,
        args.end_tick,
    )

    print(f"Saved: {args.output.resolve()}")
    print(f"Observations: {len(analysis_data):,}")
    print(
        "Okun: "
        f"y = {results['okun_slope']:.6f}x "
        f"{results['okun_intercept']:+.6f}"
    )
    print(
        "Beveridge: "
        f"y = {results['beveridge_a']:.6f} "
        f"exp({results['beveridge_exponent_b']:.6f}x)"
    )
    print(
        "Phillips: "
        f"y = {results['phillips_slope']:.6f}x "
        f"{results['phillips_intercept']:+.6f}"
    )


if __name__ == "__main__":
    main()

"""Build the M4 vector figures from the checked-in benchmark CSVs."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter

RESULTS = Path("evaluation/m4")
REPORTS = Path("reports")
LEVELS = ["L0", "L1", "L2", "L3", "L4"]
LEVEL_LABELS = ["L0\nOriginal", "L1\nHeaders", "L2\nFormats", "L3\nNoise", "L4\nMeaning"]
FULL = "normalised_coma"
WITHOUT_NUMBERS = f"{FULL}_without_numbers_and_units"
INK = "#172b3a"
MUTED = "#435a69"
TEAL = "#006c66"
ORANGE = "#a64b14"
PAPER = "#f5f8f7"
MATCHERS = (
    (FULL, "NormalisedComa", TEAL, "-", "o"),
    ("coma", "Valentine COMA", "#375e96", "--", "s"),
    ("jaccard", "Valentine Jaccard", ORANGE, ":", "^"),
)


def read_runs(mode: str) -> pd.DataFrame:
    runs = pd.read_csv(RESULTS / f"results_{mode}.csv")
    return runs.loc[runs.status.eq("ok") & ~runs.recovery_at_1_degenerate]


def level_means(runs: pd.DataFrame) -> pd.DataFrame:
    return runs.pivot_table(
        index="level", columns="matcher", values="recovery_at_1", aggfunc="mean"
    ).loc[LEVELS]


def comparison(fig, cumulative, attribution):
    cumulative_ax = fig.add_axes([.10, .19, .38, .51])
    attribution_ax = fig.add_axes([.57, .19, .38, .51], sharey=cumulative_ax)
    for ax, data, title in (
        (cumulative_ax, cumulative, "Cumulative noise"),
        (attribution_ax, attribution, "One level at a time"),
    ):
        for key, label, color, style, marker in MATCHERS:
            ax.plot(LEVELS, data[key], style, label=label, color=color, marker=marker,
                    linewidth=2.6, markersize=7)
        style_axis(ax, title)
    cumulative_ax.set_ylabel("Mean Recovery@1 across table pairs", color=INK, fontsize=11)
    attribution_ax.tick_params(labelleft=False)
    handles, labels = cumulative_ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(.54, .81),
               frameon=False, ncols=3, fontsize=13, labelcolor=INK)


def numeric_ablation(fig, cumulative, attribution):
    ax = fig.add_axes([.12, .19, .77, .52])
    ax.plot(LEVELS, cumulative[FULL], label="All four steps", color=TEAL,
            marker="o", linewidth=3, markersize=8)
    ax.plot(LEVELS, cumulative[WITHOUT_NUMBERS], "--", label="Without numeric and unit cleanup",
            color=ORANGE, marker="s", linewidth=2.5, markersize=7)
    style_axis(ax, "Cumulative noise")
    ax.set_ylabel("Mean Recovery@1 across table pairs", color=INK, fontsize=11)
    fig.legend(loc="upper center", bbox_to_anchor=(.5, .81), frameon=False,
               fontsize=13, ncols=2, labelcolor=INK)
    delta = (cumulative.loc["L2", FULL] - cumulative.loc["L2", WITHOUT_NUMBERS]) * 100
    attribution_delta = (attribution[FULL] - attribution[WITHOUT_NUMBERS]).abs().max() * 100
    fig.text(.09, .105, f"L2 difference  +{delta:.1f} pp    •    "
             f"Largest difference with one level at a time  {attribution_delta:.1f} pp",
             color=INK, fontsize=13)


def style_axis(ax, title):
    ax.set_title(title, loc="left", fontweight="bold", color=INK, fontsize=14, pad=10)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0, .25, .5, .75, 1])
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_xticks(LEVELS, LEVEL_LABELS)
    ax.tick_params(length=0, labelsize=11, colors=MUTED, pad=6)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#d6e2df", linewidth=1)
    for spine in ax.spines.values():
        spine.set_visible(False)


def page(kicker: str, title: str):
    fig = plt.figure(figsize=(13.33, 7.5), facecolor=PAPER)
    fig.text(.07, .925, kicker.upper(), size=12, weight="bold", color=TEAL)
    fig.text(.07, .845, title, size=29, weight="bold", color=INK)
    return fig


def build():
    cumulative_runs = read_runs("cumulative")
    cumulative = level_means(cumulative_runs)
    attribution = level_means(read_runs("attribution"))
    figures = REPORTS / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    charts = (
        (comparison, "Recovery across the corruption ladder", "m4_recovery"),
        (numeric_ablation, "Effect of numeric and unit normalisation", "m4_numeric_ablation"),
    )
    for draw, title, filename in charts:
        fig = page("Olist and Instacart · 12 documented table pairs", title)
        draw(fig, cumulative, attribution)
        for suffix in ("pdf", "svg"):
            fig.savefig(figures / f"{filename}.{suffix}")
        plt.close(fig)


if __name__ == "__main__":
    build()

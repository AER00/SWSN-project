"""The four figures for the M2 EDA report, as vector PDF + SVG.

    python -m swsn.figures

Every figure is generated from an artefact (``evaluation/results_*.csv``, the profiler, the
D8 diagnostics) rather than drawn by hand, so a number in the report and a number in a
figure cannot drift apart. Vector output because a rasterised heatmap of a 7 x 9 grid is
unreadable at print size.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from .benchmark import d8_quadrants
from .profile import dimension_flags, profile_table, table_summary
from .schema_doc import load_schema
from .tables import load_tables

DIMENSIONS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
DIMENSION_LABELS = {
    "D1": "D1 header",
    "D2": "D2 types",
    "D3": "D3 missing",
    "D4": "D4 formats",
    "D5": "D5 categorical",
    "D6": "D6 texture",
    "D7": "D7 shape",
}
MATCHER_LABELS = {
    "coma": "COMA",
    "cupid": "Cupid",
    "jaccard": "Jaccard",
    "similarity_flooding": "SimFlooding",
    "distribution_based": "DistributionBased",
}

DEFAULT_FIG_DIR = Path("reports/figures")


def _save(fig, out_dir: Path, name: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for suffix in ("pdf", "svg"):
        path = out_dir / f"{name}.{suffix}"
        fig.savefig(path, bbox_inches="tight")
        paths.append(path)
    plt.close(fig)
    return paths


def figure_dirtiness(tables_by_dataset: dict[str, dict[str, pd.DataFrame]], out_dir: Path):
    """F1 — which of D1-D7 each table exhibits, before any corruption is applied."""
    rows = []
    for dataset, tables in tables_by_dataset.items():
        for table, df in tables.items():
            flags = dimension_flags(table_summary(profile_table(df)))
            rows.append({"table": f"{dataset}/{table}", **{d: int(v) for d, v in flags.items()}})
    frame = pd.DataFrame(rows).set_index("table")
    frame = frame[DIMENSIONS]

    fig, ax = plt.subplots(figsize=(5.4, 0.155 * len(frame) + 1.05))
    ax.imshow(frame.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(DIMENSIONS)))
    ax.set_xticklabels([DIMENSION_LABELS[d] for d in DIMENSIONS], rotation=40, ha="right", fontsize=6)
    ax.set_yticks(range(len(frame)))
    ax.set_yticklabels(frame.index, fontsize=5.6)
    for i in range(len(frame)):
        for j in range(len(DIMENSIONS)):
            if frame.iloc[i, j]:
                ax.text(j, i, "·", ha="center", va="center", color="white", fontsize=9)
    ax.set_title("Dirtiness profile at L0", fontsize=8)
    return _save(fig, out_dir, "f1_dirtiness")


def figure_quadrants(
    df_a: pd.DataFrame, df_b: pd.DataFrame, table_a: str, table_b: str,
    schema: dict, out_dir: Path,
):
    """F2 — D8: name similarity against value overlap for every column pair."""
    frame = d8_quadrants(df_a, df_b, table_a, table_b, schema)
    fig, ax = plt.subplots(figsize=(3.7, 3.3))
    styles = {
        "S1": ("#1f77b4", "o", "S1 documented key"),
        "S2": ("#2ca02c", "s", "S2 renamed"),
        "S3": ("#ff7f0e", "^", "S3 format/grain"),
        "S4": ("#d62728", "x", "S4 trap"),
        "": ("#cccccc", ".", "unrelated"),
    }
    for stratum, (colour, marker, label) in styles.items():
        subset = frame[frame["stratum"] == stratum]
        if subset.empty:
            continue
        ax.scatter(
            subset["name_sim"], subset["value_sim"], c=colour, marker=marker,
            s=34 if stratum else 10, label=label, alpha=0.9 if stratum else 0.45,
            linewidths=1.4 if stratum == "S4" else 0.8,
        )
    ax.axvline(0.5, color="grey", lw=0.6, ls="--")
    ax.axhline(0.5, color="grey", lw=0.6, ls="--")
    ax.set_xlabel("column-name similarity", fontsize=8)
    ax.set_ylabel("value-set overlap (exact Jaccard)", fontsize=8)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.tick_params(labelsize=7)
    ax.set_title(f"D8 — {table_a} × {table_b}", fontsize=7.5)
    ax.legend(fontsize=6.5, loc="upper left", frameon=False)
    return _save(fig, out_dir, "f2_quadrants")


def figure_degradation(results: pd.DataFrame, out_dir: Path):
    """F3 — recovery@1 by ladder level, one line per matcher."""
    ok = results[(results["status"] == "ok") & (~results["recovery_at_1_degenerate"])]
    means = ok.pivot_table(index="level", columns="matcher", values="recovery_at_1", aggfunc="mean")
    means = means.sort_index()

    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    for matcher in means.columns:
        ax.plot(
            means.index, means[matcher], marker="o", ms=4,
            label=MATCHER_LABELS.get(matcher, matcher),
        )
    ax.set_ylim(0, 1.02)
    ax.set_ylabel("recovery@1", fontsize=8)
    ax.set_xlabel("corruption level (cumulative)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25, lw=0.5)
    ax.legend(fontsize=6.5, frameon=False, ncol=2)
    ax.set_title("Recovery@1 as corruption accumulates", fontsize=9)
    return _save(fig, out_dir, "f3_degradation")


def figure_strata(results: pd.DataFrame, out_dir: Path, matcher: str = "coma"):
    """F4 — recovery@1 by stratum, holding the matcher fixed."""
    columns = {
        "S1": "recovery_at_1_S1",
        "S2": "recovery_at_1_S2",
        "S3": "recovery_at_1_S3",
    }
    ok = results[(results["status"] == "ok") & (results["matcher"] == matcher)]
    present = {k: v for k, v in columns.items() if v in ok.columns and ok[v].notna().any()}
    if not present:
        return []

    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    width = 0.8 / max(len(present), 1)
    levels = sorted(ok["level"].unique())
    for i, (stratum, column) in enumerate(present.items()):
        values = [ok[ok["level"] == lvl][column].mean() for lvl in levels]
        ax.bar(
            [x + i * width - 0.4 for x in range(len(levels))],
            values, width=width, label=stratum,
        )
    ax.set_xticks(range(len(levels)))
    ax.set_xticklabels(levels, fontsize=7)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("recovery@1", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, frameon=False, title="stratum", title_fontsize=7, loc="upper right")
    if "S3" in present and float(ok[present["S3"]].fillna(0).abs().max()) == 0.0:
        # An absent bar reads as a plotting bug. Say it is the result.
        ax.annotate(
            "S3 (Portuguese↔English category name):\nrecovered at no level — 0.0",
            xy=(0.30, 0.62), xycoords="axes fraction", va="top", fontsize=6.5,
            color="#b35c00",
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "none",
                  "alpha": 0.85},
        )
    ax.set_title(f"Recovery@1 by stratum — {MATCHER_LABELS.get(matcher, matcher)}", fontsize=9)
    return _save(fig, out_dir, f"f4_strata_{matcher}")


def build_all(out_dir: Path = DEFAULT_FIG_DIR, sample_rows: int = 20000) -> list[Path]:
    written: list[Path] = []

    tables_by_dataset = {
        "olist": load_tables(
            "olist",
            ["olist_orders_dataset", "olist_order_items_dataset", "olist_order_payments_dataset",
             "olist_order_reviews_dataset", "olist_products_dataset", "olist_customers_dataset",
             "olist_sellers_dataset", "olist_geolocation_dataset"],
            nrows=sample_rows,
        ),
        "instacart": load_tables(
            "instacart",
            ["orders", "order_products__prior", "products", "aisles", "departments"],
            nrows=sample_rows,
        ),
    }
    written += figure_dirtiness(tables_by_dataset, out_dir)

    schema = load_schema("ground_truth/schema/olist.yaml")
    written += figure_quadrants(
        tables_by_dataset["olist"]["olist_products_dataset"],
        load_tables("olist", ["product_category_name_translation"])["product_category_name_translation"],
        "olist_products_dataset", "product_category_name_translation", schema, out_dir,
    )

    results_path = Path("evaluation/results_cumulative.csv")
    if results_path.exists():
        results = pd.read_csv(results_path)
        written += figure_degradation(results, out_dir)
        written += figure_strata(results, out_dir, matcher="coma")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_FIG_DIR)
    args = parser.parse_args(argv)
    for path in build_all(args.out):
        print("[fig ]", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

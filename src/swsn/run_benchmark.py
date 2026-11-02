"""Run the ladder benchmark over every declared pair that has ground truth.

    python -m swsn.run_benchmark --protocol evaluation/protocol.yaml
    python -m swsn.run_benchmark --modes attribution      # one dimension at a time
    python -m swsn.run_benchmark --datasets olist         # restrict to one dataset

Two modes, and the difference matters:

  attribution  each level's operators are applied to the original frame. Answers "which
               dimension of dirt breaks which matcher signal". A later level is not
               necessarily worse than an earlier one, because the corruptions do not stack.
  cumulative   levels 0..n are applied in order. Answers "how does recovery decay as dirt
               accumulates". This is the curve for the notebook-06 figure.

Pairs with no transcribed schema (every C-nat pair, until the annotation round lands) are
skipped and counted, not silently dropped.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .benchmark import drop_degenerate_recovery, run_pair
from .probe import load_protocol
from .registry import load_registry
from .schema_doc import SCHEMA_DIR, load_schema
from .tables import load_table

DEFAULT_OUT = Path("evaluation")


def _schema_for(dataset_id: str, schema_dir: Path) -> dict | None:
    path = schema_dir / f"{dataset_id}.yaml"
    return load_schema(path) if path.exists() else None


def run(
    protocol_path: Path = Path("evaluation/protocol.yaml"),
    registry_path: Path = Path("data/datasets.yaml"),
    schema_dir: Path = SCHEMA_DIR,
    modes: list[str] | None = None,
    datasets: list[str] | None = None,
    out_dir: Path = DEFAULT_OUT,
) -> dict[str, pd.DataFrame]:
    protocol = load_protocol(protocol_path)
    registry = load_registry(registry_path)

    matchers = [m["id"] for m in protocol.get("matchers") or []]
    levels = list((protocol.get("sets", {}).get("c_syn", {}) or {}).get("levels") or [])
    seed = int(protocol.get("seed", 42))
    max_rows = int((protocol.get("sampling") or {}).get("max_rows_per_table", 5000))
    modes = modes or ["attribution", "cumulative"]

    results: dict[str, pd.DataFrame] = {}
    skipped: list[str] = []

    for pair in registry.pairs:
        if datasets and pair.a.dataset not in datasets and pair.b.dataset not in datasets:
            continue
        schema = _schema_for(pair.a.dataset, schema_dir)
        if schema is None:
            skipped.append(f"{pair.id} (no transcribed schema for {pair.a.dataset})")
            continue

        try:
            tables = {
                pair.a.table: load_table(pair.a.dataset, pair.a.table),
                pair.b.table: load_table(pair.b.dataset, pair.b.table),
            }
        except FileNotFoundError as exc:
            skipped.append(f"{pair.id} (not downloaded: {exc})")
            continue

        for mode in modes:
            frame = run_pair(
                dataset_id=pair.a.dataset,
                table_a=pair.a.table,
                table_b=pair.b.table,
                schema=schema,
                tables=tables,
                matcher_ids=matchers,
                levels=levels,
                max_rows=max_rows,
                seed=seed,
                join_key=pair.join_key,
                cumulative=(mode == "cumulative"),
            )
            if frame.empty:
                continue
            frame["pair_id"] = pair.id
            frame["pair_type"] = pair.pair_type.value
            results.setdefault(mode, pd.DataFrame())
            results[mode] = pd.concat([results[mode], frame], ignore_index=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    for mode in list(results):
        frame = drop_degenerate_recovery(results[mode])
        results[mode] = frame  # the flags have to survive into `summary`
        path = out_dir / f"results_{mode}.csv"
        frame.to_csv(path, index=False)
        print(f"[out ] {path}  ({len(frame)} runs, {int((frame.status != 'ok').sum())} errors)")

    if skipped:
        print("\n[skip] pairs without ground truth or data:")
        for item in skipped:
            print("       -", item)

    return results


def summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Recovery@1 by level and matcher, excluding degenerate pairs."""
    ok = frame[(frame.status == "ok") & (~frame.recovery_at_1_degenerate)]
    return ok.pivot_table(
        index="level", columns="matcher", values="recovery_at_1", aggfunc="mean"
    ).round(3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=Path("evaluation/protocol.yaml"))
    parser.add_argument("--registry", type=Path, default=Path("data/datasets.yaml"))
    parser.add_argument("--schema-dir", type=Path, default=SCHEMA_DIR)
    parser.add_argument("--modes", nargs="*", default=["attribution", "cumulative"])
    parser.add_argument("--datasets", nargs="*", help="restrict to these dataset ids")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    results = run(
        protocol_path=args.protocol,
        registry_path=args.registry,
        schema_dir=args.schema_dir,
        modes=args.modes,
        datasets=args.datasets,
        out_dir=args.out,
    )
    for mode, frame in results.items():
        print(f"\n=== {mode}: recovery@1 by level ===")
        print(summary(frame).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

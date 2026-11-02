"""Ladder x matcher x table-pair benchmark.

This is the module that turns the schema, the ladder and Valentine into the numbers the
report is built on. It answers, for one documented table pair:

    at corruption level L, with matcher M, how many of the correspondences the publisher
    documented are recovered — overall and per stratum, and how many of the declared traps
    are wrongly proposed?

Design decisions that matter:

* **One-sided corruption.** Only table A is corrupted; table B stays clean. That is what
  makes the degradation attributable to a dimension rather than to "both sides got worse".
* **Ground truth is composed through the rename map.** A header operator renames columns,
  so the GT for the corrupted run is the documented pair with A's column name passed
  through ``Corrupted.rename_map``. Without this the recall would drop to zero at L1 for a
  reason that has nothing to do with matching.
* **Failures are recorded, not raised.** A matcher that raises on a duplicated header is a
  result (``status="error"``), not a reason to lose the rest of the grid.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd

from .corrupt import Corrupted, apply_level, load_ladder
from .pairdiag import annotate_quadrants, column_pairs
from .probe import as_pairs, build_matcher, precision_recall_f1, recovery_at_k, run_matcher
from .sampling import sample_pair
from .schema_doc import (
    Correspondence,
    documented_correspondences,
    negative_correspondences,
    pairs_for_tables,
)


@dataclass
class PairRun:
    dataset: str
    table_a: str
    table_b: str
    level: str
    matcher: str
    n_gt: int
    mode: str = "attribution"
    n_gt_by_stratum: dict[str, int] = field(default_factory=dict)
    recovery_at_1: float = 0.0
    recovery_at_3: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    trap_hits: int = 0
    n_predicted: int = 0
    n_target_columns: int = 0
    runtime_s: float = 0.0
    status: str = "ok"
    error: str = ""
    recovery_by_stratum: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "table_a": self.table_a,
            "table_b": self.table_b,
            "level": self.level,
            "matcher": self.matcher,
            "mode": self.mode,
            "n_gt": self.n_gt,
            "recovery_at_1": self.recovery_at_1,
            "recovery_at_3": self.recovery_at_3,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "trap_hits": self.trap_hits,
            "n_predicted": self.n_predicted,
            "n_target_columns": self.n_target_columns,
            "runtime_s": self.runtime_s,
            "status": self.status,
            "error": self.error,
            **{f"n_gt_{k}": v for k, v in self.n_gt_by_stratum.items()},
            **{f"recovery_at_1_{k}": v for k, v in self.recovery_by_stratum.items()},
        }


def _oriented_pairs(
    correspondences: list[Correspondence], table_a: str, table_b: str
) -> list[tuple[str, str, str]]:
    """(col_a, col_b, stratum) for one pair, in A->B orientation."""
    out = []
    for c in pairs_for_tables(correspondences, table_a, table_b):
        if c.table_a == table_a:
            out.append((c.col_a, c.col_b, c.stratum.value))
        else:
            out.append((c.col_b, c.col_a, c.stratum.value))
    return out


def _trap_pairs(
    traps: list[Correspondence], table_a: str, table_b: str
) -> set[tuple[str, str]]:
    out = set()
    for c in traps:
        if {c.table_a, c.table_b} != {table_a, table_b}:
            continue
        out.add((c.col_a, c.col_b) if c.table_a == table_a else (c.col_b, c.col_a))
    return out


def _recovery_by_stratum(
    predicted: list[tuple[str, str, float]],
    gt: list[tuple[str, str, str]],
    k: int,
) -> dict[str, float]:
    by_stratum: dict[str, set[tuple[str, str]]] = {}
    for col_a, col_b, stratum in gt:
        by_stratum.setdefault(stratum, set()).add((col_a, col_b))
    return {
        stratum: recovery_at_k(predicted, pairs, k)
        for stratum, pairs in sorted(by_stratum.items())
    }


def run_pair(
    dataset_id: str,
    table_a: str,
    table_b: str,
    schema: dict,
    tables: dict[str, pd.DataFrame],
    matcher_ids: list[str],
    levels: list[str],
    max_rows: int = 5000,
    seed: int = 42,
    join_key: tuple[str, str] | None = None,
    ladder: dict | None = None,
    cumulative: bool = False,
) -> pd.DataFrame:
    """Run the full grid for one documented table pair and return tidy results."""
    ladder = ladder if ladder is not None else load_ladder()
    correspondences = documented_correspondences(schema)
    traps = negative_correspondences(schema)
    gt = _oriented_pairs(correspondences, table_a, table_b)
    trap_set = _trap_pairs(traps, table_a, table_b)
    if not gt:
        return pd.DataFrame()

    df_a_full, df_b_full = tables[table_a], tables[table_b]
    if join_key:
        df_a_full, df_b_full = sample_pair(
            df_a_full, df_b_full, join_key[0], join_key[1], max_rows=max_rows, seed=seed
        )
    else:
        df_a_full = df_a_full.head(max_rows).reset_index(drop=True)
        df_b_full = df_b_full.head(max_rows).reset_index(drop=True)

    runs: list[PairRun] = []
    for level in levels:
        corrupted: Corrupted = apply_level(
            df_a_full, level, ladder=ladder, seed=seed, cumulative=cumulative
        )
        df_a = corrupted.df
        gt_remapped = [
            (corrupted.remap_column(col_a), col_b, stratum)
            for col_a, col_b, stratum in gt
        ]
        gt_set = {(a, b) for a, b, _ in gt_remapped}

        for matcher_id in matcher_ids:
            run = PairRun(
                dataset=dataset_id,
                table_a=table_a,
                table_b=table_b,
                level=level,
                matcher=matcher_id,
                n_gt=len(gt_set),
                mode="cumulative" if cumulative else "attribution",
            )
            for col_a, _, stratum in gt_remapped:
                run.n_gt_by_stratum[stratum] = run.n_gt_by_stratum.get(stratum, 0) + 1
            # The matcher is run as (clean B, corrupted A), so A is the target side and its
            # column count decides whether recovery@k is informative at all (see below).
            run.n_target_columns = len(df_a.columns)
            start = time.perf_counter()
            try:
                matcher = build_matcher(matcher_id)
                # Match clean B against corrupted A, so the orientation is B -> A.
                results = run_matcher([df_b_full, df_a], matcher, [table_b, table_a])
                predicted = [(b, a, s) for a, b, s in as_pairs(results)]
                run.n_predicted = len(predicted)
                run.recovery_at_1 = recovery_at_k(predicted, gt_set, 1)
                run.recovery_by_stratum = _recovery_by_stratum(predicted, gt_remapped, 1)
                run.recovery_at_3 = recovery_at_k(predicted, gt_set, 3)
                scored = precision_recall_f1(predicted, gt_set)
                run.precision = scored["precision"]
                run.recall = scored["recall"]
                run.f1 = scored["f1"]
                run.trap_hits = len({(a, b) for a, b, _ in predicted} & trap_set)
            except Exception as exc:  # noqa: BLE001 - a matcher crash is a result
                run.status = "error"
                run.error = f"{type(exc).__name__}: {exc}"[:300]
            run.runtime_s = time.perf_counter() - start
            runs.append(run)

    return pd.DataFrame([r.as_dict() for r in runs])


def drop_degenerate_recovery(results: pd.DataFrame) -> pd.DataFrame:
    """Mark runs where recovery@3 is trivially 1.0.

    ``recovery_at_k`` asks whether the right target column is in the top k proposed for a
    source column. When the target table has fewer than k columns, *every* candidate is in
    the top k and the metric returns 1.0 without the matcher having done anything. Olist's
    products -> category-translation pair has exactly two target columns, so recovery@3 is
    1.0 for every matcher at every level — which would have appeared in the report as
    "the translation is recovered perfectly" when in fact only recovery@1 says anything.

    Runs with ``n_target_columns <= 3`` are flagged rather than deleted, so the table can
    still show them with the caveat attached.
    """
    out = results.copy()
    out["recovery_at_1_degenerate"] = out["n_target_columns"] <= 1
    out["recovery_at_3_degenerate"] = out["n_target_columns"] <= 3
    return out


def stratum_summary(results: pd.DataFrame) -> pd.DataFrame:
    """Per (dataset, level, matcher): mean recovery@1/@3 and summed trap hits.

    Degenerate pairs are excluded from the means — averaging in a column of 1.0s that the
    matcher did not earn would flatter every matcher equally and hide the differences
    between them, which is the only thing this table exists to show.
    """
    if results.empty:
        return results
    ok = results[results["status"] == "ok"]
    usable = ok[~ok["recovery_at_3_degenerate"]]
    grouped = usable.groupby(["dataset", "level", "matcher"], as_index=False).agg(
        pairs=("table_a", "size"),
        recovery_at_1=("recovery_at_1", "mean"),
        recovery_at_3=("recovery_at_3", "mean"),
        trap_hits=("trap_hits", "sum"),
        runtime_s=("runtime_s", "sum"),
    )
    return grouped.sort_values(["dataset", "level", "recovery_at_1"], ascending=[True, True, False])


def d8_quadrants(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    table_a: str,
    table_b: str,
    schema: dict,
    threshold: float = 0.5,
) -> pd.DataFrame:
    """Name-similarity x value-overlap for every column pair across two tables.

    This is D8 in the plan: it locates which documented correspondences are easy (Q1),
    which are synonyms (Q2), which are traps (Q3) and which are unrelated (Q4) *before*
    any matcher runs, so a matcher's failure can be attributed to the signal it needed.

    Sampled frames only — ``value_similarity`` builds exact value sets, so a million-row
    table would be both slow and pointless here.
    """
    pairs = column_pairs(df_a, df_b)
    out = annotate_quadrants(pairs, threshold)

    gt = {(a, b): s for a, b, s in _oriented_pairs(documented_correspondences(schema), table_a, table_b)}
    trap_set = _trap_pairs(negative_correspondences(schema), table_a, table_b)
    out["stratum"] = [
        gt.get((a, b)) or ("S4" if (a, b) in trap_set else "")
        for a, b in zip(out["col_a"], out["col_b"])
    ]
    return out

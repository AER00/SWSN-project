"""D8 — the cross-table diagnostic (milestone2-plan.md §3.2).

For every pair of columns between two tables compute:

    name_sim   token Jaccard over canonicalised column names
    value_sim  Jaccard over lightly normalised value sets

Plotting the two against each other, coloured by ground truth, separates easy matches
from the two failure regimes: renamed/synonym columns (low name, high value) and traps
(high name, low value). No matcher has to run for this to work.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from itertools import product

import pandas as pd

STOPWORDS = {"id", "ids", "the", "a", "of", "no", "col", "column"}


def name_tokens(name: str | Iterable[str]) -> set[str]:
    if not isinstance(name, str):
        name = " ".join(map(str, name))
    tokens = re.split(r"[^0-9a-zA-Z]+", str(name).lower())
    return {t for t in tokens if t and t not in STOPWORDS}


def token_jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def name_similarity(a: str, b: str) -> float:
    return token_jaccard(name_tokens(a), name_tokens(b))


def light_normalise(value: object) -> str:
    """The baseline cleaning only: trim and casefold. Deliberately weak — anything
    stronger would hide the effect the ladder is meant to measure."""
    return str(value).strip().casefold()


def value_set(
    series: pd.Series, max_distinct: int | None = None, seed: int = 42
) -> set[str]:
    """Distinct normalised values.

    ``max_distinct`` exists only for pathological columns (a million distinct floats).
    Leave it at the default: downsampling distinct values before computing Jaccard is not
    scale-invariant and silently turns identical 100k-element sets into a near-zero
    overlap. See docs/findings.md (2026-11-02).
    """
    values = series.dropna().astype(str).map(light_normalise)
    distinct = values.drop_duplicates()
    if max_distinct is not None and len(distinct) > max_distinct:
        distinct = distinct.sample(n=max_distinct, random_state=seed)
    return set(distinct)


def value_similarity(
    a: pd.Series,
    b: pd.Series,
    max_distinct: int | None = None,
    seed: int = 42,
) -> float:
    """Exact Jaccard over distinct value sets (see ``value_set`` for the caveat)."""
    sa = value_set(a, max_distinct, seed)
    sb = value_set(b, max_distinct, seed)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def column_pairs(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    max_distinct: int | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """One row per candidate column pair with both signals."""
    rows = []
    for col_a, col_b in product(df_a.columns, df_b.columns):
        rows.append(
            {
                "col_a": str(col_a),
                "col_b": str(col_b),
                "name_sim": name_similarity(str(col_a), str(col_b)),
                "value_sim": value_similarity(df_a[col_a], df_b[col_b], max_distinct, seed),
            }
        )
    return pd.DataFrame(rows)


def quadrant(name_sim: float, value_sim: float, threshold: float = 0.5) -> str:
    """Q1 easy · Q2 renamed/synonym · Q3 trap · Q4 non-match."""
    high_name = name_sim >= threshold
    high_value = value_sim >= threshold
    if high_name and high_value:
        return "Q1_easy"
    if not high_name and high_value:
        return "Q2_synonym"
    if high_name and not high_value:
        return "Q3_trap"
    return "Q4_nonmatch"


def annotate_quadrants(pairs: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    out = pairs.copy()
    out["quadrant"] = [
        quadrant(n, v, threshold) for n, v in zip(out["name_sim"], out["value_sim"])
    ]
    return out

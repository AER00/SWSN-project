"""Join-aware row sampling.

Sampling each table independently destroys the very thing schema matching is supposed to
find. Taking the first 5,000 rows of `orders` and the first 5,000 rows of
`order_payments` gives two disjoint sets of order ids, so their value overlap collapses to
zero and a trivially matched key column looks like a trap. That happened on 2026-11-02 and
is recorded in docs/findings.md.

Rule: sample on a *shared key*, never per table.
"""

from __future__ import annotations

import pandas as pd

DEFAULT_MAX_ROWS = 5000


def sample_by_key(
    df: pd.DataFrame,
    key: str,
    max_rows: int = DEFAULT_MAX_ROWS,
    seed: int = 42,
) -> pd.DataFrame:
    """Take at most ``max_rows`` distinct key values and keep every row for them."""
    if key not in df.columns:
        raise KeyError(f"sampling key {key!r} not in {list(df.columns)}")
    keys = df[key].dropna().drop_duplicates()
    if len(keys) > max_rows:
        keys = keys.sample(n=max_rows, random_state=seed)
    return df[df[key].isin(keys)].reset_index(drop=True)


def sample_pair(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    key_a: str,
    key_b: str,
    max_rows: int = DEFAULT_MAX_ROWS,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sample both tables on the same set of key values, preserving the correspondence."""
    if key_a not in df_a.columns or key_b not in df_b.columns:
        raise KeyError(f"join key missing: {key_a!r} in A, {key_b!r} in B")

    keys = df_a[key_a].dropna().drop_duplicates()
    if len(keys) > max_rows:
        keys = keys.sample(n=max_rows, random_state=seed)

    a = df_a[df_a[key_a].isin(keys)].reset_index(drop=True)
    b = df_b[df_b[key_b].isin(keys)].reset_index(drop=True)
    return a, b


def sample_independent(
    df: pd.DataFrame,
    max_rows: int = DEFAULT_MAX_ROWS,
    seed: int = 42,
) -> pd.DataFrame:
    """For single-table profiling only. Never use this before a matching run."""
    if len(df) <= max_rows:
        return df.reset_index(drop=True)
    return df.sample(n=max_rows, random_state=seed).reset_index(drop=True)

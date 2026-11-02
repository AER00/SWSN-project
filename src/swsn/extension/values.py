"""Canonical value sets per column — M3 implementation target.

A column becomes a set of canonical values (sampled, seeded). Two columns match on the
instance signal in proportion to the Jaccard overlap of their sets. Everything downstream
— the matcher, the D8 diagnostic, the ablation report — uses this one representation.
"""

from __future__ import annotations

import pandas as pd

from .canonicalise import canonicalise_value
from .config import CanonicalisationConfig

DEFAULT_MAX_DISTINCT = 1000


def canonical_value_set(
    series: pd.Series,
    config: CanonicalisationConfig | None = None,
    max_distinct: int = DEFAULT_MAX_DISTINCT,
    seed: int = 42,
) -> frozenset[str]:
    """Return the canonical distinct values of a column.

    Sampling is deterministic: same series, config and seed give the same set, which is
    what makes the ablation comparable across runs.
    """
    config = config or CanonicalisationConfig()
    values = [canonicalise_value(v, config) for v in series.dropna().astype(str)]
    distinct = sorted({v for v in values if v})
    if len(distinct) > max_distinct:
        distinct = list(pd.Series(distinct).sample(n=max_distinct, random_state=seed))
    return frozenset(distinct)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)

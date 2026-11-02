"""Value canonicalisation — M3 implementation target.

Contract (frozen in M2): every function is pure, takes a scalar, returns ``str``, and is
idempotent — ``f(f(x)) == f(x)``. Idempotence matters because the matcher may see already
canonicalised values from a preprocessing run.

Do not implement these in M2. The body is M3's preprocessing deliverable, and the plan's
scope guard keeps it there. What is fixed now is the shape and the ordering, because the
M4 ablation depends on it.
"""

from __future__ import annotations

from collections.abc import Callable

from .config import CanonicalisationConfig


def canonicalise_case_and_punctuation(value: object) -> str:
    """casefold, unify unicode dashes/quotes, collapse whitespace and punctuation runs."""
    raise NotImplementedError("M3: implement case/punctuation canonicalisation")


def canonicalise_dates(value: object) -> str:
    """Parse the common date encodings to ISO 8601; leave unparseable values untouched."""
    raise NotImplementedError("M3: implement date canonicalisation")


def canonicalise_numbers_and_units(value: object) -> str:
    """Normalise separators, currency, units, zero padding and identifier prefixes."""
    raise NotImplementedError("M3: implement number/unit canonicalisation")


def canonicalise_sentinels_and_nulls(value: object) -> str:
    """Map sentinel tokens (N/A, -, unknown, 999) to the empty string; strip mixed types."""
    raise NotImplementedError("M3: implement sentinel/null canonicalisation")


_STEPS: tuple[tuple[str, Callable[[object], str]], ...] = (
    ("sentinels_and_nulls", canonicalise_sentinels_and_nulls),
    ("dates", canonicalise_dates),
    ("numbers_and_units", canonicalise_numbers_and_units),
    ("case_and_punctuation", canonicalise_case_and_punctuation),
)


def canonicalise_value(value: object, config: CanonicalisationConfig | None = None) -> str:
    """Apply every enabled component in the declared order.

    Order is part of the contract: sentinels are resolved before parsing, so a `999`
    acting as a null never becomes the number 999. Changing the order changes results and
    must be reported as a protocol change.
    """
    config = config or CanonicalisationConfig()
    text = value
    for name, step in _STEPS:
        if getattr(config, name):
            text = step(text)
    return str(text)

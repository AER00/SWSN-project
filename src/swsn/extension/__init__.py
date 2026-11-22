"""Normalisation-aware matching with independently ablatable preprocessing steps.

    config.py        which canonicalisation components are enabled
    canonicalise.py  value-level canonicalisation (dates, numbers, units, sentinels)
    values.py        canonical value sets per column
    matcher.py       NormalisedComa(BaseMatcher) — the method itself
"""

from .config import CanonicalisationConfig

__all__ = ["CanonicalisationConfig"]

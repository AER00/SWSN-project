"""The M3/M4 deliverable: normalisation-aware matching.

Interface frozen in M2 so that M3 can implement against it and M4 can ablate it. The
body of every module here is M3 work; what is fixed now is the contract.

    config.py        which canonicalisation components are enabled
    canonicalise.py  value-level canonicalisation (dates, numbers, units, sentinels)
    values.py        canonical value sets per column
    matcher.py       NormalisedComa(BaseMatcher) — the method itself
"""

from .config import CanonicalisationConfig

__all__ = ["CanonicalisationConfig"]

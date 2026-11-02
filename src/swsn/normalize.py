"""Minimal canonicaliser — M2 preview only.

This is the ~30-line demonstrator used to estimate how much value-overlap headroom
canonicalisation buys (milestone2-plan.md §3.4). It is deliberately *not* the deliverable:
the production version lives in ``swsn.extension.canonicalise`` and is M3 work.

Rule: canonicalise only what a rule can justify. Anything that needs semantics
(translating 'São Paulo' to 'SP') is out of scope here and belongs to L4.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

CURRENCY = r"[$€£¥₹]|R\$|USD|EUR|BRL"
DECIMAL_COMMA = re.compile(r"(?<=\d),(?=\d{1,2}\b)")
SPACES = re.compile(r"\s+")
DATE_ISH = re.compile(r"[-/:]|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", re.IGNORECASE)
# 1.234,50 (European) and 1,234.50 (US) before the generic separator cleaning
EURO_NUMBER = re.compile(r"^(\d{1,3}(?:\.\d{3})+)(?:,(\d+))?$")
US_NUMBER = re.compile(r"^(\d{1,3}(?:,\d{3})+)(?:\.(\d+))?$")


def _strip_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    for dash in "‐‑‒–—−":
        text = text.replace(dash, "-")
    for quote in "‘’‚‛“”„":
        text = text.replace(quote, "'")
    return text.replace(" ", " ")


def canonicalise_value(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""

    text = _strip_unicode(str(value)).strip()
    if not text:
        return ""

    # dates first, but only for strings that look like dates — otherwise pandas will
    # happily parse identifiers such as "20240101" and destroy the value
    if DATE_ISH.search(text):
        parsed = pd.to_datetime(text, errors="coerce", format="mixed")
        if pd.notna(parsed):
            return parsed.strftime("%Y-%m-%dT%H:%M:%S")

    lowered = text.casefold()

    # numbers: drop currency and unit noise, normalise separators
    numeric = re.sub(CURRENCY, "", lowered, flags=re.IGNORECASE)
    numeric = re.sub(r"\b(kg|km|cm|mm|g|m|days?|pcs|units?)\b", "", numeric).strip()
    numeric = numeric.replace("%", "").strip()

    euro = EURO_NUMBER.fullmatch(numeric)
    us = US_NUMBER.fullmatch(numeric)
    if euro:
        integer, fraction = euro.group(1).replace(".", ""), euro.group(2)
    elif us:
        integer, fraction = us.group(1).replace(",", ""), us.group(2)
    else:
        integer, fraction = DECIMAL_COMMA.sub(".", numeric).replace(",", ""), None
    normalized = integer if fraction is None else f"{integer}.{fraction}"

    if re.fullmatch(r"-?\d+(\.\d+)?", normalized):
        return str(float(normalized)).rstrip("0").rstrip(".")

    # identifiers and text: collapse whitespace and punctuation runs
    return SPACES.sub(" ", re.sub(r"[^\w\s-]", " ", lowered)).strip()


def canonicalise_series(series: pd.Series) -> pd.Series:
    return series.map(canonicalise_value)


def overlap_after_canonicalisation(a: pd.Series, b: pd.Series) -> float:
    """Jaccard overlap of the canonicalised distinct value sets."""
    sa = {v for v in canonicalise_series(a).dropna() if v}
    sb = {v for v in canonicalise_series(b).dropna() if v}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

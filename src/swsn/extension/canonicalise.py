"""Pure scalar-to-string canonicalisers for the corruption ladder.

Each step is idempotent in isolation. The order and switches in the combined pipeline
are part of the ablation protocol.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from datetime import UTC, datetime, time

from pandas import isna
from pandas.api.types import is_scalar

from .config import CanonicalisationConfig

_TEXT_PUNCTUATION = str.maketrans({
    **dict.fromkeys("\u2010\u2011\u2012\u2013\u2014\u2212", "-"),
    **dict.fromkeys("\u2018\u2019\u201a\u201b", "'"),
    **dict.fromkeys("\u201c\u201d\u201e\u201f", '"'),
})
_REPEATED_PUNCTUATION = re.compile(r"""([.,!?;:'"-])\1+""")
_SENTINELS = frozenset({"n/a", "-", "unknown", "?", "null", "999", "-1", "see notes"})
_FLOAT_SENTINEL = re.compile(r"(?:999|-1)\.0+")
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[Tt ][0-9].*)?")
_EPOCH_SECONDS = re.compile(r"epoch:([+-]?[0-9]{1,12})", re.IGNORECASE)
_DATE_FORMATS = (
    (re.compile(r"[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}"), ("%m/%d/%Y", "%d/%m/%Y")),
    (re.compile(r"[0-9]{4}/[0-9]{1,2}/[0-9]{1,2}"), ("%Y/%m/%d",)),
    (re.compile(r"[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{4}"), ("%d.%m.%Y",)),
    (re.compile(r"[0-9]{1,2}\s+[^\W\d_]+\s+[0-9]{4}"), ("%d %b %Y", "%d %B %Y")),
)
_CURRENCY = r"R\$|[$\u20ac\u00a3\u00a5]|USD|EUR|BRL"
_NUMBER_VALUE = re.compile(
    rf"(?:(?:{_CURRENCY})\s*|ORD-|ID_|k)?"
    r"(?P<sign>[+-]?)(?P<number>[0-9][0-9.,'\u2019\s]*)"
    rf"(?:\s*(?:{_CURRENCY}|kg|km|cm|days?|%))?",
    re.IGNORECASE,
)
_DIGITS = re.compile(r"[0-9]+")
_GROUPED_INTEGER = re.compile(r"[1-9][0-9]{0,2}([., '])[0-9]{3}(?:\1[0-9]{3})*")
_FLOATIFIED_FLOAT = re.compile(r"([0-9]+)\.0+\.0")


def canonicalise_case_and_punctuation(value: object) -> str:
    """Casefold text and tidy formatting without removing accents or single delimiters."""
    text = unicodedata.normalize("NFC", str(value)).casefold()
    text = unicodedata.normalize("NFC", text).translate(_TEXT_PUNCTUATION)
    text = _REPEATED_PUNCTUATION.sub(r"\1", text)
    return " ".join(text.split())


def canonicalise_dates(value: object) -> str:
    """Return ISO dates/times; slash dates prefer US order and epoch seconds require a tag."""
    text = str(value)
    candidate = text.strip()
    epoch = _EPOCH_SECONDS.fullmatch(candidate)
    if not epoch and not _ISO_DATE.fullmatch(candidate):
        for pattern, formats in _DATE_FORMATS:
            if pattern.fullmatch(candidate):
                for date_format in formats:
                    try:
                        return datetime.strptime(candidate, date_format).date().isoformat()
                    except ValueError:
                        continue
        return text

    try:
        if epoch:
            parsed = datetime.fromtimestamp(int(epoch[1]), tz=UTC)
        else:
            if candidate.endswith("z"):
                candidate = candidate[:-1] + "Z"
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(UTC)
    except (ValueError, OverflowError, OSError):
        return text
    return parsed.date().isoformat() if parsed.time() == time.min else parsed.isoformat()


def canonicalise_numbers_and_units(value: object) -> str:
    """Normalise numeric formatting and strip known ladder affixes without scaling."""
    text = str(value)
    match = _NUMBER_VALUE.fullmatch(text.strip())
    if not match:
        return text

    number = " ".join(match["number"].replace("\u2019", "'").split())
    floatified = _FLOATIFIED_FLOAT.fullmatch(number)
    if floatified:
        number = floatified[1]

    decimal_separator = None
    if "." in number and "," in number:
        decimal_separator = "." if number.rfind(".") > number.rfind(",") else ","
    elif number.count(".") == 1:
        decimal_separator = "."
    elif number.count(",") == 1 and not _GROUPED_INTEGER.fullmatch(number):
        decimal_separator = ","

    fraction = ""
    integer = number
    if decimal_separator:
        integer, fraction = number.rsplit(decimal_separator, 1)
        if not _DIGITS.fullmatch(fraction):
            return text

    grouped = _GROUPED_INTEGER.fullmatch(integer)
    if grouped and grouped[1] != decimal_separator:
        integer = integer.replace(grouped[1], "")
    elif not _DIGITS.fullmatch(integer):
        return text

    integer = integer.lstrip("0") or "0"
    fraction = fraction.rstrip("0")
    sign = "-" if match["sign"] == "-" and (integer != "0" or fraction) else ""
    return f"{sign}{integer}.{fraction}" if fraction else f"{sign}{integer}"


def canonicalise_sentinels_and_nulls(value: object) -> str:
    """Map scalar nulls and exact ladder sentinel tokens to the empty string."""
    if not isinstance(value, str) and is_scalar(value) and isna(value):
        return ""
    text = str(value)
    token = text.strip().casefold()
    if not token or token in _SENTINELS or _FLOAT_SENTINEL.fullmatch(token):
        return ""
    return text


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

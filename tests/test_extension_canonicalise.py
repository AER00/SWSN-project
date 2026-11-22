import pandas as pd
import pytest

from swsn.extension.canonicalise import (
    canonicalise_case_and_punctuation,
    canonicalise_dates,
    canonicalise_numbers_and_units,
    canonicalise_sentinels_and_nulls,
    canonicalise_value,
)
from swsn.extension.config import CanonicalisationConfig
from swsn.extension.values import canonical_value_set


@pytest.mark.parametrize(
    "raw, expected",
    [
        (" \tStra\u00dfe\u00a0  WEST\n", "strasse west"),
        ("Sa\u0303O PAULO", "s\u00e3o paulo"),
        ("\u201cNORTH\u2014WEST\u201d", '"north-west"'),
        ("D\u2019ANGELO!!!", "d'angelo!"),
        ("2026-11-24", "2026-11-24"),
        ("-12.50", "-12.50"),
        ("ID_001/A", "id_001/a"),
        ("N/A", "n/a"),
        (999, "999"),
        ("\u00a0\t", ""),
    ],
)
def test_canonicalise_case_and_punctuation(raw, expected):
    normalised = canonicalise_case_and_punctuation(raw)
    assert normalised == expected
    assert canonicalise_case_and_punctuation(normalised) == normalised


@pytest.mark.parametrize("enabled, expected", [(True, "north-west"), (False, " NORTH\u2013WEST ")])
def test_text_canonicalisation_respects_config(enabled, expected):
    config = CanonicalisationConfig(
        case_and_punctuation=enabled,
        dates=False,
        numbers_and_units=False,
        sentinels_and_nulls=False,
    )

    assert canonicalise_value(" NORTH\u2013WEST ", config) == expected


@pytest.mark.parametrize(
    "raw",
    [None, pd.NA, pd.NaT, float("nan"), " N/A ", "-", "UNKNOWN", "?", "null", 999, -1.0, "see notes"],
)
def test_canonicalise_sentinels_and_nulls(raw):
    assert canonicalise_sentinels_and_nulls(raw) == ""


def test_sentinels_drop_out_of_the_value_set_only_when_enabled():
    series = pd.Series([pd.NA, " N/A ", 999.0, "Unknown Road", 1999], dtype=object)
    config = CanonicalisationConfig(case_and_punctuation=False, dates=False, numbers_and_units=False)

    assert canonical_value_set(series, config) == {"Unknown Road", "1999"}
    assert canonical_value_set(series, config.without("sentinels_and_nulls")) == {
        " N/A ", "999.0", "Unknown Road", "1999",
    }


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2024-03-04T00:00:00", "2024-03-04"),
        ("03/04/2024", "2024-03-04"),
        ("25/03/2024", "2024-03-25"),
        ("04.03.2024", "2024-03-04"),
        ("4 March 2024", "2024-03-04"),
        ("04 Mar 2024", "2024-03-04"),
        ("epoch:1709510400", "2024-03-04"),
        ("2024-03-04T05:00:00+01:00", "2024-03-04T04:00:00+00:00"),
        ("2024-02-30", "2024-02-30"),
        (20240304, "20240304"),
        (1709510400, "1709510400"),
    ],
)
def test_canonicalise_dates(raw, expected):
    assert canonicalise_dates(raw) == expected
    assert canonicalise_dates(expected) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1,234.50", "1234.5"),
        ("1.234,50", "1234.5"),
        ("1\u00a0234,50", "1234.5"),
        ("1\u2019234.50", "1234.5"),
        ("1,234", "1234"),
        ("0,125", "0.125"),
        ("R$1.234,50", "1234.5"),
        ("1234.50 USD", "1234.5"),
        ("12,5%", "12.5"),
        ("42 kg", "42"),
        ("12345.0.0", "12345"),
        ("00000042", "42"),
        ("ORD-00042", "42"),
        ("ID_00042", "42"),
        ("k00042", "42"),
        ("-0.000", "0"),
        ("9007199254740993.00", "9007199254740993"),
        ("1,2,3", "1,2,3"),
        ("2024-03-04", "2024-03-04"),
        ("BOOK-42", "BOOK-42"),
        ("5 Golden Days", "5 Golden Days"),
    ],
)
def test_canonicalise_numbers_and_units(raw, expected):
    assert canonicalise_numbers_and_units(raw) == expected
    assert canonicalise_numbers_and_units(expected) == expected


def test_default_value_set_applies_all_steps():
    raw = pd.Series([" N/A ", "04.03.2024", "R$1.234,50", " NORTH\u2014WEST "])

    assert canonical_value_set(raw) == {"2024-03-04", "1234.5", "north-west"}
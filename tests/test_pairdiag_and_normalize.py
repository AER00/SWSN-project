import pandas as pd
import pytest

from swsn.normalize import canonicalise_value, overlap_after_canonicalisation
from swsn.pairdiag import name_similarity, quadrant, value_similarity


def test_name_similarity_ignores_case_and_separators():
    assert name_similarity("Customer_ID", "customer id") == pytest.approx(1.0)
    assert name_similarity("order_id", "product_name") == pytest.approx(0.0)


def test_value_similarity_is_identity_for_same_domain():
    a = pd.Series(["A", " B ", "c"])
    b = pd.Series(["a", "b", "C"])
    assert value_similarity(a, b) == pytest.approx(1.0)


def test_quadrants():
    assert quadrant(0.9, 0.9) == "Q1_easy"
    assert quadrant(0.0, 0.9) == "Q2_synonym"
    assert quadrant(0.9, 0.0) == "Q3_trap"
    assert quadrant(0.0, 0.0) == "Q4_nonmatch"


@pytest.mark.parametrize(
    "raw, expected",
    [
        (" 1,234.50 ", "1234.5"),
        ("1.234,50", "1234.5"),
        ("$1234.50", "1234.5"),
        ("12,5%", "12.5"),
        ("2018-01-02", "2018-01-02T00:00:00"),
        ("01/02/2018", "2018-01-02T00:00:00"),
        ("São Paulo", "sao paulo"),
    ],
)
def test_canonicalise_value(raw, expected):
    assert canonicalise_value(raw) == expected


def test_canonicalisation_recovers_number_overlap():
    a = pd.Series(["1,234.5", "2,000.0"])
    b = pd.Series(["1234.5", "2000"])
    assert overlap_after_canonicalisation(a, b) == pytest.approx(1.0)

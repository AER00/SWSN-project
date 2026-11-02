import math

import pytest

from swsn.agreement import cohen_kappa


def test_perfect_agreement():
    a = ["1", "0", "1", "0"]
    assert cohen_kappa(a, a) == pytest.approx(1.0)


def test_agreement_at_chance_is_zero():
    # both annotators label everything positive: agreement is total but uninformative
    a, b = ["1"] * 4, ["1"] * 4
    assert cohen_kappa(a, b) == pytest.approx(1.0)


def test_systematic_disagreement_is_negative():
    a = ["1", "1", "0", "0"]
    b = ["0", "0", "1", "1"]
    assert cohen_kappa(a, b) == pytest.approx(-1.0)


def test_partial_agreement():
    a = ["1", "1", "0", "0", "1"]
    b = ["1", "0", "0", "1", "1"]
    kappa = cohen_kappa(a, b)
    assert -1.0 <= kappa <= 1.0
    assert kappa < 1.0


def test_empty_returns_nan():
    assert math.isnan(cohen_kappa([], []))


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        cohen_kappa(["1"], ["1", "0"])

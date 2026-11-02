from pathlib import Path

import pandas as pd
import pytest

from swsn.corrupt import apply_level, check_preservation, load_ladder

LADDER = Path(__file__).resolve().parents[1] / "corruption" / "ladder.yaml"
ALL_LEVELS = ["L1", "L2", "L3", "L4"]


@pytest.fixture
def tables():
    df_a = pd.DataFrame(
        {
            "order_id": [1001, 1002, 1003, 1004],
            "price": [10.5, 20.0, 30.25, 40.0],
            "city": ["sao paulo", "rio de janeiro", "curitiba", "recife"],
            "order_date": ["2018-01-01", "2018-01-02", "2018-02-01", "2018-03-15"],
        }
    )
    df_b = df_a.copy()
    return df_a, df_b


def test_l0_is_identity(tables):
    df_a, _ = tables
    result = apply_level(df_a, "L0", load_ladder(LADDER), seed=1)
    pd.testing.assert_frame_equal(result.df, df_a)
    assert result.rename_map == {}


def test_header_level_records_rename_map(tables):
    df_a, _ = tables
    result = apply_level(df_a, "L1", load_ladder(LADDER), seed=7)
    assert result.applied, "L1 should apply at least one operator"
    assert set(result.rename_map).issubset({str(c) for c in df_a.columns})
    for original, renamed in result.rename_map.items():
        assert result.remap_column(original) == renamed


@pytest.mark.parametrize("level", ALL_LEVELS)
def test_every_declared_operator_is_implemented(tables, level):
    """The ladder must not declare an operator the generator cannot run."""
    df_a, _ = tables
    result = apply_level(df_a, level, load_ladder(LADDER), seed=3)
    assert result.applied, f"{level} produced no operators"


def test_generation_is_deterministic(tables):
    df_a, _ = tables
    first = apply_level(df_a, "L2", load_ladder(LADDER), seed=11)
    second = apply_level(df_a, "L2", load_ladder(LADDER), seed=11)
    pd.testing.assert_frame_equal(first.df, second.df)
    assert first.rename_map == second.rename_map


def test_integrity_check_accepts_format_only_corruption(tables):
    df_a, df_b = tables
    corrupted = apply_level(df_a, "L2", load_ladder(LADDER), seed=5).df
    violations = check_preservation(
        corrupted, df_b, [("order_id", "order_id"), ("price", "price")], threshold=0.5
    )
    assert violations == []


def test_integrity_check_flags_destroyed_values(tables):
    _, df_b = tables
    destroyed = df_b.assign(order_id=["x", "y", "z", "w"])
    violations = check_preservation(destroyed, df_b, [("order_id", "order_id")], threshold=0.5)
    assert violations and "order_id" in violations[0]

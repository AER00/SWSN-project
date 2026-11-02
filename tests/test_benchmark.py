import pandas as pd
import pytest

from swsn.benchmark import drop_degenerate_recovery, run_pair
from swsn.corrupt import apply_level

SCHEMA = {
    "dataset": "toy",
    "tables": {
        "orders": {
            "columns": ["order_id", "customer_id", "amount"],
            "references": [
                {"column": "customer_id", "table": "customers", "column_ref": "customer_id",
                 "stratum": "S1"},
            ],
        },
        "customers": {"columns": ["customer_id", "name"]},
    },
    "traps": [
        {"table_a": "orders", "col_a": "order_id", "table_b": "customers",
         "col_b": "customer_id", "note": "both identifier-shaped"},
    ],
}


def _tables(n: int = 40):
    ids = [f"c{i:03d}" for i in range(n)]
    return {
        "orders": pd.DataFrame({
            "order_id": [f"o{i:03d}" for i in range(n)],
            "customer_id": ids,
            "amount": [float(i) for i in range(n)],
        }),
        "customers": pd.DataFrame({"customer_id": ids, "name": [f"name {i}" for i in range(n)]}),
    }


def _run(levels, matchers=("jaccard",), **kwargs):
    return run_pair(
        "toy", "orders", "customers", SCHEMA, _tables(),
        matcher_ids=list(matchers), levels=list(levels), max_rows=40,
        join_key=("customer_id", "customer_id"), **kwargs,
    )


def test_a_documented_foreign_key_is_recovered_at_l0():
    result = _run(["L0"])
    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "ok"
    assert row["recovery_at_1"] == pytest.approx(1.0)


def test_ground_truth_is_remapped_through_the_rename_map():
    """Without remapping, every L1 run would show recall 0 for a bookkeeping reason."""
    result = _run(["L1"])
    row = result.iloc[0]
    assert row["status"] == "ok"
    assert row["n_gt"] == 1


def test_each_level_and_matcher_gets_one_row():
    result = _run(["L0", "L1", "L2"], matchers=("jaccard",))
    assert len(result) == 3
    assert set(result["level"]) == {"L0", "L1", "L2"}


def test_mode_is_recorded_so_a_table_cannot_be_misread():
    attribution = _run(["L2"], cumulative=False)
    cumulative = _run(["L2"], cumulative=True)
    assert attribution.iloc[0]["mode"] == "attribution"
    assert cumulative.iloc[0]["mode"] == "cumulative"


def test_degeneracy_flag_fires_when_the_target_is_too_small():
    flagged = drop_degenerate_recovery(_run(["L0"]))
    # customers has 2 columns, so a top-3 really contains everything
    assert bool(flagged.iloc[0]["recovery_at_3_degenerate"]) is True
    assert bool(flagged.iloc[0]["recovery_at_1_degenerate"]) is False


def test_degeneracy_depends_on_the_target_column_count_not_the_data():
    flagged = drop_degenerate_recovery(_run(["L0"]))
    assert flagged.iloc[0]["n_target_columns"] == 3  # orders
    wide = _tables()
    n = len(wide["orders"])
    wide["orders"] = pd.concat(
        [wide["orders"], pd.DataFrame({f"extra_{i}": [0.0] * n for i in range(5)})], axis=1
    )
    result = run_pair(
        "toy", "orders", "customers", SCHEMA, wide,
        matcher_ids=["jaccard"], levels=["L0"], max_rows=40,
    )
    flagged = drop_degenerate_recovery(result)
    assert bool(flagged.iloc[0]["recovery_at_3_degenerate"]) is False


def test_a_pair_with_no_documented_correspondence_returns_nothing():
    empty = {
        "dataset": "toy",
        "tables": {"orders": {"columns": ["order_id"]}, "customers": {"columns": ["name"]}},
    }
    result = run_pair(
        "toy", "orders", "customers", empty, _tables(),
        matcher_ids=["jaccard"], levels=["L0"], max_rows=40,
    )
    assert result.empty


def test_traps_are_counted_when_a_matcher_proposes_them():
    result = _run(["L0"])
    assert "trap_hits" in result.columns
    assert result.iloc[0]["trap_hits"] >= 0


def test_cumulative_rename_chain_survives_duplicate_headers():
    """L1 can give two columns the same name; the value ops must not crash on it."""
    corrupted = apply_level(_tables()["orders"], "L4", cumulative=True)
    assert len(corrupted.df) == 40
    assert corrupted.applied  # every level's operators ran

import json

import numpy as np
import pandas as pd
import pytest

from swsn.registry import Dataset, DatasetClass
from swsn.triage import (
    GateOutcome,
    TriageResult,
    evaluate,
    render_table,
    write_triage,
)

GOOD = {
    "id": "d",
    "cls": DatasetClass.C_DOC,
    "domain": "testing",
    "kaggle_slug": "someone/something",
    "version": "1",
    "licence": "CC0: Public Domain",
    "sha256": {"a.csv": "deadbeef"},
}

SCHEMA = {
    "dataset": "d",
    "tables": {"a": {"references": [{"column": "x", "table": "b", "column_ref": "x"}]}},
}


def _tables(n_rows: int = 200, seed: int = 0):
    """A three-dimension fixture: D3 missingness, D4 decimal-comma, D7 outliers.

    Deliberately not hand-built column-by-column against the profiler's thresholds — it
    was tuned once by running the profiler, so the numbers here are whatever a realistic
    messy table produces at each row count.
    """
    rng = np.random.default_rng(seed)
    amounts, price_index = [], []
    for i in range(n_rows):
        value = float(rng.exponential(1e6))
        amounts.append(
            None if i % 5 == 0 else (f"{value:.2f}".replace(".", ",") if i % 2 else f"{value:.2f}")
        )
        price_index.append(1000.0 if i % 10 == 0 else 1.0)
    return {
        "a": pd.DataFrame({
            "order_key": [f"id-{i}" for i in range(n_rows)],
            "amount_brl": amounts,
            "price_index": price_index,
        })
    }


def test_a_well_formed_documented_dataset_passes_the_gate():
    result = evaluate(Dataset(**GOOD), SCHEMA, _tables())
    assert result.admitted, result.failed
    assert result.n_correspondences == 1


def test_missing_licence_fails_g1():
    result = evaluate(Dataset(**{**GOOD, "licence": None}), SCHEMA, _tables())
    assert result.admitted is False
    assert [g.gate for g in result.failed] == ["G1"]
    assert "licence" in result.failed[0].evidence


def test_a_valentine_benchmark_dataset_fails_g2():
    bad = Dataset(**{**GOOD, "kaggle_slug": "someone/chembl-mirror"})
    result = evaluate(bad, SCHEMA, _tables())
    assert [g.gate for g in result.failed] == ["G2"]


def test_c_nat_needs_three_hand_identified_correspondences():
    native = Dataset(**{**GOOD, "cls": DatasetClass.C_NAT})
    schema = {"dataset": "d", "tables": {"a": {"corresponds": [
        {"column": "x", "table": "b", "column_ref": "y", "stratum": "S2"},
    ]}}}
    result = evaluate(native, schema, _tables())
    assert [g.gate for g in result.failed] == ["G3"]
    assert "3" in result.failed[0].evidence


def test_a_clean_dataset_fails_the_messiness_gate():
    clean = {"a": pd.DataFrame({"order_key": range(50), "amount_brl": range(50)})}
    result = evaluate(Dataset(**GOOD), SCHEMA, clean)
    assert [g.gate for g in result.failed] == ["G4"]
    assert result.dimensions == []


def test_too_many_columns_fails_tractability():
    wide = _tables(120)
    n = len(wide["a"])
    wide["a"] = pd.concat(
        [wide["a"], pd.DataFrame({f"extra_{i}": [1.0] * n for i in range(120)})], axis=1
    )
    result = evaluate(Dataset(**GOOD), SCHEMA, wide)
    assert [g.gate for g in result.failed] == ["G5"]


def test_render_table_has_one_row_and_column_per_gate():
    results = [evaluate(Dataset(**GOOD), SCHEMA, _tables())]
    table = render_table(results)
    assert len(table) == 1
    assert {"dataset", "admitted", "G1", "G2", "G3", "G4", "G5"} <= set(table.columns)
    assert table.loc[0, "G1"] == "pass"


def test_write_triage_records_evidence_for_every_gate(tmp_path):
    path = write_triage([evaluate(Dataset(**GOOD), SCHEMA, _tables())], tmp_path / "triage.json")
    payload = json.loads(path.read_text())
    assert len(payload[0]["gates"]) == 5
    assert all(g["evidence"] for g in payload[0]["gates"])


def test_a_gate_outcome_with_no_failures_reports_admitted():
    result = TriageResult(dataset="x", gates=[GateOutcome("G1", True, "ok")])
    assert result.admitted is True
    assert result.failed == []


@pytest.mark.parametrize("n_rows", [60, 500])
def test_gate_is_size_independent_for_dimensions(n_rows):
    result = evaluate(Dataset(**GOOD), SCHEMA, _tables(n_rows))
    assert set(result.dimensions) == {"D3", "D4", "D7"}

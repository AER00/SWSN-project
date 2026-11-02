import csv

import pytest
import yaml

from swsn.schema_doc import (
    documented_correspondences,
    export_ground_truth,
    ground_truth_set,
    load_all_schemas,
    negative_correspondences,
    pairs_for_tables,
    stratum_counts,
)


def test_shipped_schemas_parse_and_are_stratified():
    schemas = load_all_schemas()
    assert {"olist", "instacart"} <= set(schemas)
    for dataset, schema in schemas.items():
        positives = documented_correspondences(schema)
        assert positives, f"{dataset} produced no ground truth"
        assert all(c.stratum.value in {"S1", "S2", "S3"} for c in positives)


def test_olist_has_a_populated_non_s1_stratum():
    """The whole point of C-doc is that some correspondences are not freebies."""
    schema = load_all_schemas()["olist"]
    counts = stratum_counts(documented_correspondences(schema))
    assert counts.get("S2", 0) >= 3
    assert counts.get("S3", 0) >= 1


def test_traps_are_kept_out_of_the_positive_set():
    schema = load_all_schemas()["olist"]
    positives = documented_correspondences(schema)
    traps = negative_correspondences(schema)
    assert traps, "olist declares no traps"
    positive_pairs = {frozenset({(c.table_a, c.col_a), (c.table_b, c.col_b)}) for c in positives}
    for trap in traps:
        assert frozenset({(trap.table_a, trap.col_a), (trap.table_b, trap.col_b)}) not in positive_pairs


def test_s4_under_references_is_rejected():
    schema = {
        "dataset": "bad",
        "tables": {
            "a": {"references": [
                {"column": "x", "table": "b", "column_ref": "y", "stratum": "S4"}
            ]}
        },
    }
    with pytest.raises(ValueError, match="belong in the top-level"):
        documented_correspondences(schema)


def test_a_pair_declared_in_both_directions_is_rejected():
    schema = {
        "dataset": "bad",
        "tables": {
            "a": {"references": [{"column": "x", "table": "b", "column_ref": "x"}]},
            "b": {"references": [{"column": "x", "table": "a", "column_ref": "x"}]},
        },
    }
    with pytest.raises(ValueError, match="declared twice"):
        documented_correspondences(schema)


def test_ground_truth_set_follows_the_requested_orientation():
    schema = {
        "dataset": "t",
        "tables": {
            "products": {"corresponds": [
                {"column": "cat", "table": "translation", "column_ref": "cat_en", "stratum": "S3"}
            ]}
        },
    }
    pairs = documented_correspondences(schema)
    assert ground_truth_set(pairs, "products", "translation") == {("cat", "cat_en")}
    assert ground_truth_set(pairs, "translation", "products") == {("cat_en", "cat")}
    assert ground_truth_set(pairs, "products", "customers") == set()


def test_pairs_for_tables_ignores_declaration_order():
    schema = load_all_schemas()["instacart"]
    pairs = documented_correspondences(schema)
    assert pairs_for_tables(pairs, "orders", "order_products__prior")
    assert pairs_for_tables(pairs, "order_products__prior", "orders")


def test_export_writes_one_row_per_correspondence(tmp_path):
    schema = load_all_schemas()["olist"]
    path = export_ground_truth(schema, out_dir=tmp_path)
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    positives = [r for r in rows if r["label"] == "1"]
    negatives = [r for r in rows if r["label"] == "0"]
    assert len(positives) == len(documented_correspondences(schema))
    assert len(negatives) == len(negative_correspondences(schema))
    assert {r["stratum"] for r in positives} <= {"S1", "S2", "S3"}
    assert {r["stratum"] for r in negatives} == {"S4"}


def test_export_matches_the_annotation_guide_format(tmp_path):
    """One file format in ground_truth/gt/, or the two drift apart."""
    schema = load_all_schemas()["olist"]
    path = export_ground_truth(schema, out_dir=tmp_path)
    header = next(csv.reader(path.open(encoding="utf-8")))
    assert header == ["table_a", "col_a", "table_b", "col_b", "label", "stratum",
                      "annotator", "note"]


def test_schema_files_are_valid_yaml_with_a_source():
    from pathlib import Path

    for path in Path("ground_truth/schema").glob("*.yaml"):
        schema = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert schema.get("source", "").startswith("https://"), f"{path} has no citable source"
        assert schema.get("retrieved"), f"{path} has no retrieval date"

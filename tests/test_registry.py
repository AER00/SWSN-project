import textwrap

import pytest

from swsn.registry import DatasetClass, PairType, Status, load_registry


def write(tmp_path, body):
    path = tmp_path / "datasets.yaml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_loads_datasets_and_pairs(tmp_path):
    path = write(
        tmp_path,
        """
        datasets:
          - id: olist
            class: c_doc
            domain: e-commerce
            kaggle_slug: olistbr/brazilian-ecommerce
            status: admitted
            licence: CC BY-NC-SA 4.0
            version: "1"
          - id: cardekho
            class: c_nat
            domain: used-cars
            kaggle_slug: nehalbirla/vehicle-dataset-from-cardekho
        pairs:
          - id: olist_orders__payments
            a: { dataset: olist, table: orders }
            b: { dataset: olist, table: payments }
            pair_type: p_grain
            rationale: one order can be settled by several payment rows
        """,
    )
    registry = load_registry(path)

    assert registry["olist"].cls is DatasetClass.C_DOC
    assert registry["olist"].status is Status.ADMITTED
    assert registry["olist"].triaged is True
    assert registry["cardekho"].triaged is False  # candidate and unversioned
    assert registry.pairs[0].pair_type is PairType.P_GRAIN
    assert len(registry.admitted()) == 1


def test_duplicate_ids_rejected(tmp_path):
    path = write(
        tmp_path,
        """
        datasets:
          - { id: a, class: c_doc, kaggle_slug: x/y }
          - { id: a, class: c_nat, kaggle_slug: x/z }
        """,
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_registry(path)


def test_unknown_class_rejected(tmp_path):
    path = write(tmp_path, "datasets:\n  - { id: a, class: nonsense, kaggle_slug: x/y }\n")
    with pytest.raises(ValueError, match="unknown class"):
        load_registry(path)


def test_pair_without_rationale_rejected(tmp_path):
    path = write(
        tmp_path,
        """
        datasets: []
        pairs:
          - id: p
            a: { dataset: a, table: t1 }
            b: { dataset: b, table: t2 }
        """,
    )
    with pytest.raises(ValueError, match="rationale"):
        load_registry(path)

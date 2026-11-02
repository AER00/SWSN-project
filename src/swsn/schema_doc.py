"""Transcribed documented schemas and the ground truth they generate.

A schema file lives in ``ground_truth/schema/<dataset>.yaml`` and looks like:

    dataset: olist
    source: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
    tables:
      olist_orders_dataset:
        columns: [order_id, customer_id, order_status, ...]
        row_count: 99441
        keys: [order_id]
        references:
          - column: customer_id
            table: olist_customers_dataset
            column_ref: customer_id
            stratum: S1
      olist_products_dataset:
        columns: [product_id, product_category_name, ...]
        corresponds:
          - column: product_category_name
            table: product_category_name_translation
            column_ref: product_category_name
            stratum: S2
            note: Portuguese to English category name

``references`` are join keys; ``corresponds`` are documented non-key correspondences
(renamed, translated, different grain). Both become ground truth; the stratum is what
distinguishes a freebie from a real test.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .registry import Stratum


@dataclass(frozen=True)
class Correspondence:
    table_a: str
    col_a: str
    table_b: str
    col_b: str
    stratum: Stratum
    kind: str  # "reference" | "corresponds"
    note: str = ""


def load_schema(path: str | Path) -> dict:
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        schema = yaml.safe_load(fh) or {}
    if "tables" not in schema:
        raise ValueError(f"{path}: schema must define `tables`")
    return schema


def documented_correspondences(schema: dict) -> list[Correspondence]:
    """Flatten a schema into a list of documented column correspondences."""
    out: list[Correspondence] = []
    for table, spec in (schema.get("tables") or {}).items():
        for ref in spec.get("references") or []:
            out.append(
                Correspondence(
                    table_a=table,
                    col_a=ref["column"],
                    table_b=ref["table"],
                    col_b=ref["column_ref"],
                    stratum=Stratum(ref.get("stratum", "S1")),
                    kind="reference",
                    note=ref.get("note", ""),
                )
            )
        for ref in spec.get("corresponds") or []:
            out.append(
                Correspondence(
                    table_a=table,
                    col_a=ref["column"],
                    table_b=ref["table"],
                    col_b=ref["column_ref"],
                    stratum=Stratum(ref.get("stratum", "S2")),
                    kind="corresponds",
                    note=ref.get("note", ""),
                )
            )
    return out


def by_table_pair(correspondences: list[Correspondence]) -> dict[tuple[str, str], list[Correspondence]]:
    grouped: dict[tuple[str, str], list[Correspondence]] = {}
    for c in correspondences:
        key = tuple(sorted((c.table_a, c.table_b)))
        grouped.setdefault(key, []).append(c)
    return grouped


def stratum_counts(correspondences: list[Correspondence]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in correspondences:
        counts[c.stratum.value] = counts.get(c.stratum.value, 0) + 1
    return dict(sorted(counts.items()))

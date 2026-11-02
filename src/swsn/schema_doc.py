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
            column_ref: product_category_name_english
            stratum: S3
            note: Portuguese to English category name
    traps:
      - {table_a: ..., col_a: ..., table_b: ..., col_b: ..., note: ...}

``references`` are join keys; ``corresponds`` are documented non-key correspondences
(renamed, translated, different grain). Both become ground truth; the stratum is what
distinguishes a freebie from a real test.

``traps`` are the opposite: pairs that are *not* correspondences, declared up front so the
probe can be scored against them instead of being argued about afterwards. They are kept
out of the ground truth deliberately — putting an S4 entry in ``references`` would make the
probe reward a wrong match, so ``documented_correspondences`` raises if it finds one.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import yaml

from .registry import Stratum

SCHEMA_DIR = Path("ground_truth/schema")
GT_DIR = Path("ground_truth/gt")


@dataclass(frozen=True)
class Correspondence:
    table_a: str
    col_a: str
    table_b: str
    col_b: str
    stratum: Stratum
    kind: str  # "reference" | "corresponds" | "trap"
    note: str = ""

    @property
    def as_pair(self) -> tuple[str, str]:
        return (self.col_a, self.col_b)


def load_schema(path: str | Path) -> dict:
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        schema = yaml.safe_load(fh) or {}
    if "tables" not in schema:
        raise ValueError(f"{path}: schema must define `tables`")
    return schema


def documented_correspondences(schema: dict) -> list[Correspondence]:
    """Flatten a schema into a list of documented column correspondences.

    Raises if an S4 stratum appears under ``references`` or ``corresponds``: a trap in the
    positive set silently corrupts every metric downstream.
    """
    out: list[Correspondence] = []
    dataset = schema.get("dataset", "<unknown>")

    def add(table: str, ref: dict, kind: str, default_stratum: str) -> None:
        stratum = Stratum(ref.get("stratum", default_stratum))
        if stratum is Stratum.S4:
            raise ValueError(
                f"{dataset}: S4 (trap) declared under `{kind}` in table {table!r}. "
                "Traps belong in the top-level `traps:` list; in the positive set they "
                "would teach the probe to reward a wrong match."
            )
        out.append(
            Correspondence(
                table_a=table,
                col_a=ref["column"],
                table_b=ref["table"],
                col_b=ref["column_ref"],
                stratum=stratum,
                kind=kind,
                note=(ref.get("note") or "").strip(),
            )
        )

    for table, spec in (schema.get("tables") or {}).items():
        for ref in spec.get("references") or []:
            add(table, ref, "reference", "S1")
        for ref in spec.get("corresponds") or []:
            add(table, ref, "corresponds", "S2")

    _reject_duplicates(out, dataset)
    return out


def _reject_duplicates(correspondences: list[Correspondence], dataset: str) -> None:
    """A column pair may be declared once only, in one direction.

    A foreign key declared on both the child and the parent table is the easy mistake, and
    it silently doubles that pair's weight in every per-stratum count.
    """
    seen: dict[frozenset, Correspondence] = {}
    for c in correspondences:
        key = frozenset({(c.table_a, c.col_a), (c.table_b, c.col_b)})
        if key in seen:
            other = seen[key]
            raise ValueError(
                f"{dataset}: the pair {c.table_a}.{c.col_a} -> {c.table_b}.{c.col_b} is "
                f"declared twice (also as {other.table_a}.{other.col_a} -> "
                f"{other.table_b}.{other.col_b}). Declare it once, on the child side."
            )
        seen[key] = c


def negative_correspondences(schema: dict) -> list[Correspondence]:
    """The declared traps (S4). Never part of the ground truth."""
    return [
        Correspondence(
            table_a=t["table_a"],
            col_a=t["col_a"],
            table_b=t["table_b"],
            col_b=t["col_b"],
            stratum=Stratum.S4,
            kind="trap",
            note=(t.get("note") or "").strip(),
        )
        for t in schema.get("traps") or []
    ]


def by_table_pair(
    correspondences: list[Correspondence],
) -> dict[tuple[str, str], list[Correspondence]]:
    grouped: dict[tuple[str, str], list[Correspondence]] = {}
    for c in correspondences:
        key = tuple(sorted((c.table_a, c.table_b)))
        grouped.setdefault(key, []).append(c)
    return grouped


def pairs_for_tables(
    correspondences: list[Correspondence], table_a: str, table_b: str
) -> list[Correspondence]:
    """Correspondences between two named tables, in either direction."""
    wanted = {table_a, table_b}
    return [c for c in correspondences if {c.table_a, c.table_b} == wanted]


def ground_truth_set(
    correspondences: list[Correspondence], table_a: str, table_b: str
) -> set[tuple[str, str]]:
    """Column pairs for one table pair, oriented as (source_col, target_col).

    Valentine's matcher results are directed: ``(a.source_column, a.target_column)``. The
    orientation follows the direction declared in the schema file (``column`` is the
    source side). Callers matching in the opposite direction swap the pairs.
    """
    out: set[tuple[str, str]] = set()
    for c in pairs_for_tables(correspondences, table_a, table_b):
        if c.table_a == table_a:
            out.add((c.col_a, c.col_b))
        else:
            out.add((c.col_b, c.col_a))
    return out


def stratum_counts(correspondences: list[Correspondence]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in correspondences:
        counts[c.stratum.value] = counts.get(c.stratum.value, 0) + 1
    return dict(sorted(counts.items()))


def export_ground_truth(
    schema: dict,
    out_dir: str | Path = GT_DIR,
    dataset_id: str | None = None,
) -> Path:
    """Write the ground truth as a reviewable CSV, one row per column pair.

    Uses the file format declared in ``ground_truth/annotation_guide.md`` — the same one the
    C-nat annotators use — so there is a single format in ``ground_truth/gt/`` rather than
    two that have to be reconciled later. Documented correspondences are ``label=1`` and
    the declared traps are ``label=0`` with stratum S4, which is what a two-person
    annotation round would produce for them anyway.

    ``annotator`` is ``schema``: these labels come from the publisher's documentation, not
    from a person, and the column has to say so.
    """
    did = dataset_id or schema["dataset"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{did}.csv"

    with target.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["table_a", "col_a", "table_b", "col_b", "label", "stratum", "annotator", "note"]
        )
        for c in documented_correspondences(schema):
            writer.writerow(
                [c.table_a, c.col_a, c.table_b, c.col_b, 1, c.stratum.value, "schema", c.note]
            )
        for c in negative_correspondences(schema):
            writer.writerow(
                [c.table_a, c.col_a, c.table_b, c.col_b, 0, c.stratum.value, "schema", c.note]
            )
    return target


def load_all_schemas(schema_dir: str | Path = SCHEMA_DIR) -> dict[str, dict]:
    """Every transcribed schema, keyed by dataset id."""
    out: dict[str, dict] = {}
    for path in sorted(Path(schema_dir).glob("*.yaml")):
        schema = load_schema(path)
        out[schema["dataset"]] = schema
    return out

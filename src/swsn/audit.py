"""D9 — documentation-versus-data audit (milestone2-plan.md §3.1, §3.3).

The published schema is our ground truth, so it has to be checked against the files
before it is trusted. A documented column that is absent, a documented key that is not
unique, or a documented foreign key that does not resolve are all findings — either the
documentation is stale or the data is dirty, and both are reportable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class TableAudit:
    table: str
    documented_columns: int
    missing_columns: list[str] = field(default_factory=list)
    undocumented_columns: list[str] = field(default_factory=list)
    row_count_documented: int | None = None
    row_count_observed: int | None = None

    @property
    def column_coverage(self) -> float:
        if not self.documented_columns:
            return 0.0
        present = self.documented_columns - len(self.missing_columns)
        return present / self.documented_columns

    @property
    def row_count_matches(self) -> bool | None:
        if self.row_count_documented is None or self.row_count_observed is None:
            return None
        return self.row_count_documented == self.row_count_observed


@dataclass
class ForeignKeyAudit:
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str
    resolving_share: float
    child_nulls: int

    @property
    def satisfied(self) -> bool:
        return self.resolving_share >= 0.99


@dataclass
class AuditReport:
    dataset: str
    tables: list[TableAudit]
    foreign_keys: list[ForeignKeyAudit]

    def summary(self) -> dict:
        fk = self.foreign_keys
        return {
            "dataset": self.dataset,
            "tables": len(self.tables),
            "mean_column_coverage": (
                sum(t.column_coverage for t in self.tables) / len(self.tables)
                if self.tables
                else 0.0
            ),
            "missing_columns": sum(len(t.missing_columns) for t in self.tables),
            "undocumented_columns": sum(len(t.undocumented_columns) for t in self.tables),
            "fk_checked": len(fk),
            "fk_satisfied": sum(1 for f in fk if f.satisfied),
            "fk_mean_resolving_share": (
                sum(f.resolving_share for f in fk) / len(fk) if fk else 0.0
            ),
        }


def audit_table(
    table: str,
    documented_columns: list[str],
    df: pd.DataFrame,
    row_count_documented: int | None = None,
) -> TableAudit:
    documented = set(documented_columns)
    observed = {str(c) for c in df.columns}
    return TableAudit(
        table=table,
        documented_columns=len(documented),
        missing_columns=sorted(documented - observed),
        undocumented_columns=sorted(observed - documented),
        row_count_documented=row_count_documented,
        row_count_observed=len(df),
    )


def check_foreign_key(
    child: pd.DataFrame,
    child_table: str,
    child_col: str,
    parent: pd.DataFrame,
    parent_table: str,
    parent_col: str,
) -> ForeignKeyAudit:
    """Share of non-null child values that resolve in the parent column."""
    child_values = child[child_col].dropna()
    parent_values = set(parent[parent_col].dropna())
    if len(child_values) == 0:
        share = 0.0
    else:
        share = child_values.isin(parent_values).mean()
    return ForeignKeyAudit(
        child_table=child_table,
        child_column=child_col,
        parent_table=parent_table,
        parent_column=parent_col,
        resolving_share=float(share),
        child_nulls=int(child[child_col].isna().sum()),
    )


def audit_dataset(
    dataset_id: str,
    schema: dict,
    tables: dict[str, pd.DataFrame],
) -> AuditReport:
    """Run the full D9 audit for one dataset.

    ``schema`` is the structure documented in ``ground_truth/schema/<id>.yaml``:
    ``{tables: {name: {columns: [...], row_count: int|None, references: [...]}}}``.
    """
    table_audits = []
    for name, spec in (schema.get("tables") or {}).items():
        if name not in tables:
            table_audits.append(
                TableAudit(
                    table=name,
                    documented_columns=len(spec.get("columns") or []),
                    missing_columns=list(spec.get("columns") or []),
                )
            )
            continue
        table_audits.append(
            audit_table(
                name,
                spec.get("columns") or [],
                tables[name],
                spec.get("row_count"),
            )
        )

    foreign_keys = []
    for name, spec in (schema.get("tables") or {}).items():
        if name not in tables:
            continue
        for ref in spec.get("references") or []:
            parent = ref.get("table")
            if parent not in tables:
                continue
            foreign_keys.append(
                check_foreign_key(
                    tables[name],
                    name,
                    ref["column"],
                    tables[parent],
                    parent,
                    ref["column_ref"],
                )
            )

    return AuditReport(dataset=dataset_id, tables=table_audits, foreign_keys=foreign_keys)

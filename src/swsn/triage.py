"""The admission gate G1-G5.

A dataset is admitted only if all five criteria pass. Three of them are measurable from
what we already have — the registry, the transcribed schema, the profiler — and are
computed here. The other two need a human judgement (is the download fast enough, is the
licence usable) and are recorded as evidence strings.

The reason this is a module and not a paragraph: the gate has to be applied to *every*
candidate before any of them is used, and a table in the report that is produced by the
same code that produces the decision is harder to fudge than one written afterwards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .profile import dimension_flags, profile_table, table_summary
from .registry import Dataset
from .schema_doc import documented_correspondences

# Anything Valentine itself benchmarks on. Using one of these would forfeit the rubric's
# "datasets differ from the main papers" point outright.
BENCHMARK_SOURCES = {
    "tpc-di", "tpc di", "open data", "chembl", "wikidata", "wiki data",
    "magellan", "abt-buy", "abt buy", "walmart-amazon", "dblp-acm", "itunes-amazon", "beer",
}

MAX_COLUMNS = 120          # G5
MIN_DIMENSIONS = 3         # G4
MIN_CORRESPONDENCES_C_NAT = 3  # G3


@dataclass(frozen=True)
class GateOutcome:
    gate: str
    passed: bool
    evidence: str

    def as_dict(self) -> dict:
        return {"gate": self.gate, "passed": self.passed, "evidence": self.evidence}


@dataclass
class TriageResult:
    dataset: str
    gates: list[GateOutcome] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    n_correspondences: int = 0

    @property
    def admitted(self) -> bool:
        return all(g.passed for g in self.gates)

    @property
    def failed(self) -> list[GateOutcome]:
        return [g for g in self.gates if not g.passed]

    def summary(self) -> dict:
        return {
            "dataset": self.dataset,
            "admitted": self.admitted,
            "failed_gates": [g.gate for g in self.failed],
            "dimensions": self.dimensions,
            "n_correspondences": self.n_correspondences,
        }


def _g1_provenance(dataset: Dataset) -> GateOutcome:
    problems = []
    if not dataset.version:
        problems.append("version not pinned")
    if not dataset.licence:
        problems.append("licence not recorded")
    if not dataset.sha256:
        problems.append("no checksums")
    if problems:
        return GateOutcome("G1", False, "; ".join(problems))
    return GateOutcome(
        "G1", True,
        f"public Dataset, version {dataset.version}, {len(dataset.sha256)} files checksummed, "
        f"licence: {dataset.licence}",
    )


def _g2_not_benchmark(dataset: Dataset) -> GateOutcome:
    haystack = f"{dataset.id} {dataset.kaggle_slug} {dataset.domain}".lower()
    hits = sorted(s for s in BENCHMARK_SOURCES if s in haystack)
    if hits:
        return GateOutcome("G2", False, f"matches Valentine benchmark source(s): {hits}")
    return GateOutcome("G2", True, "not one of Valentine's benchmark sources or their tables")


def _g3_pairing(dataset: Dataset, correspondences: int) -> GateOutcome:
    if dataset.cls.value == "c_doc":
        ok = correspondences > 0
        need = "documented relationship"
    else:
        ok = correspondences >= MIN_CORRESPONDENCES_C_NAT
        need = f">= {MIN_CORRESPONDENCES_C_NAT} hand-identified correspondences"
    return GateOutcome(
        "G3", ok,
        f"{correspondences} correspondences transcribed ({need} required for {dataset.cls.value})",
    )


def _g4_messiness(dimensions: list[str]) -> GateOutcome:
    ok = len(dimensions) >= MIN_DIMENSIONS
    return GateOutcome(
        "G4", ok,
        f"{len(dimensions)} of D1-D7 present without synthetic corruption: "
        f"{', '.join(dimensions) if dimensions else 'none'} (need {MIN_DIMENSIONS})",
    )


def _g5_tractability(n_columns: int, max_rows: int, download_seconds: float | None) -> GateOutcome:
    problems = []
    if n_columns > MAX_COLUMNS:
        problems.append(f"{n_columns} columns > {MAX_COLUMNS}")
    if download_seconds is not None and download_seconds >= 60:
        problems.append(f"download took {download_seconds:.0f}s")
    evidence = f"{n_columns} columns, largest table {max_rows:,} rows"
    if download_seconds is not None:
        evidence += f", downloaded in {download_seconds:.0f}s"
    if problems:
        return GateOutcome("G5", False, "; ".join(problems) + f" ({evidence})")
    return GateOutcome("G5", True, evidence + "; sampleable to 5k rows on a shared key")


def evaluate(
    dataset: Dataset,
    schema: dict | None = None,
    tables: dict[str, pd.DataFrame] | None = None,
    download_seconds: float | None = None,
) -> TriageResult:
    """Apply all five gates to one dataset.

    ``tables`` should be a sample (a few tens of thousands of rows is plenty); the
    dimensions are proportions and do not need the full files.
    """
    correspondences = len(documented_correspondences(schema)) if schema else 0

    dimensions: list[str] = []
    n_columns = 0
    max_rows = 0
    for df in (tables or {}).values():
        n_columns = max(n_columns, len(df.columns))
        max_rows = max(max_rows, len(df))
        flags = dimension_flags(table_summary(profile_table(df)))
        dimensions.extend(k for k, v in flags.items() if v)
    dimensions = sorted(set(dimensions))

    return TriageResult(
        dataset=dataset.id,
        gates=[
            _g1_provenance(dataset),
            _g2_not_benchmark(dataset),
            _g3_pairing(dataset, correspondences),
            _g4_messiness(dimensions),
            _g5_tractability(n_columns, max_rows, download_seconds),
        ],
        dimensions=dimensions,
        n_correspondences=correspondences,
    )


def render_table(results: list[TriageResult]) -> pd.DataFrame:
    """One row per dataset, one column per gate, for the report and notebook 00."""
    rows = []
    for r in results:
        row = {"dataset": r.dataset, "admitted": r.admitted}
        for g in r.gates:
            row[g.gate] = "pass" if g.passed else "FAIL"
        row["dimensions"] = " ".join(r.dimensions)
        row["correspondences"] = r.n_correspondences
        rows.append(row)
    return pd.DataFrame(rows)


def write_triage(results: list[TriageResult], path: str | Path) -> Path:
    """Persist the full gate evidence as JSON, so the report can quote it verbatim."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {"summary": r.summary(), "gates": [g.as_dict() for g in r.gates]} for r in results
    ]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    """Apply the gate to every registered dataset that has data and a transcribed schema."""
    import argparse

    from .registry import load_registry
    from .schema_doc import SCHEMA_DIR, load_schema
    from .tables import load_tables

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("data/datasets.yaml"))
    parser.add_argument("--schema-dir", type=Path, default=SCHEMA_DIR)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("evaluation/triage.json"))
    parser.add_argument("--nrows", type=int, default=50_000)
    args = parser.parse_args(argv)

    registry = load_registry(args.registry)
    results: list[TriageResult] = []
    missing: list[str] = []

    for dataset in registry.datasets.values():
        schema_path = args.schema_dir / f"{dataset.id}.yaml"
        if not schema_path.exists():
            missing.append(f"{dataset.id} (no schema)")
            continue
        if not dataset.root(args.data_dir).exists():
            missing.append(f"{dataset.id} (not downloaded)")
            continue
        schema = load_schema(schema_path)
        tables = load_tables(
            dataset.id, list((schema.get("tables") or {}).keys()),
            data_dir=args.data_dir, nrows=args.nrows,
        )
        result = evaluate(dataset, schema, tables)
        results.append(result)
        print(f"[gate] {dataset.id:20s} {'ADMIT' if result.admitted else 'REJECT':6s} "
              f"{[g.gate for g in result.failed]}")

    if results:
        print()
        print(render_table(results).to_string(index=False))
        print("\n[out ]", write_triage(results, args.out))
    if missing:
        print("\n[skip] no gate applied:", ", ".join(missing))
    return 0 if all(r.admitted for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

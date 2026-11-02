"""Dataset registry.

`data/datasets.yaml` is the single source of truth for what the project uses. Everything
else (download, profiling, probe, report tables) reads from here rather than hard-coding
slugs or filenames.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class DatasetClass(str, Enum):
    """How the dataset supplies ground truth."""

    C_DOC = "c_doc"  # documented multi-table dataset, GT from the published schema
    C_NAT = "c_nat"  # independent single tables, GT from annotation


class Status(str, Enum):
    CANDIDATE = "candidate"
    ADMITTED = "admitted"
    DROPPED = "dropped"


class PairType(str, Enum):
    P_DOC = "p_doc"  # both tables from one documented dataset
    P_NATURAL = "p_natural"  # two independent uploads, same domain
    P_GRAIN = "p_grain"  # related tables at different grain
    P_SPLIT = "p_split"  # one table split in two; control condition


class Stratum(str, Enum):
    """Ground-truth stratum. S4 entries are negatives (traps)."""

    S1 = "S1"  # documented key, near-identical name
    S2 = "S2"  # same concept, materially different name
    S3 = "S3"  # same concept, different format / unit / grain
    S4 = "S4"  # trap — similar name or type, different meaning


@dataclass(frozen=True)
class Dataset:
    id: str
    cls: DatasetClass
    domain: str
    kaggle_slug: str
    status: Status = Status.CANDIDATE
    licence: str | None = None
    version: str | None = None
    sha256: dict[str, str] = field(default_factory=dict)
    notes: str = ""

    def root(self, base: Path) -> Path:
        return base / "raw" / self.id

    @property
    def admitted(self) -> bool:
        return self.status is Status.ADMITTED

    @property
    def triaged(self) -> bool:
        """A dataset is usable only once its licence and version are recorded."""
        return self.admitted and bool(self.licence) and self.version is not None


@dataclass(frozen=True)
class TableRef:
    dataset: str
    table: str


@dataclass(frozen=True)
class TablePair:
    id: str
    a: TableRef
    b: TableRef
    pair_type: PairType
    rationale: str
    join_key: tuple[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.rationale.strip():
            raise ValueError(
                f"pair {self.id!r} needs a rationale: why would these two tables be "
                "related in practice? (milestone2-plan.md §1.3)"
            )


@dataclass
class Registry:
    datasets: dict[str, Dataset]
    pairs: list[TablePair]

    def __getitem__(self, dataset_id: str) -> Dataset:
        return self.datasets[dataset_id]

    def admitted(self) -> dict[str, Dataset]:
        return {k: v for k, v in self.datasets.items() if v.admitted}

    def pairs_for(self, dataset_id: str) -> list[TablePair]:
        return [p for p in self.pairs if dataset_id in (p.a.dataset, p.b.dataset)]

    def by_domain(self) -> dict[str, list[Dataset]]:
        out: dict[str, list[Dataset]] = {}
        for ds in self.datasets.values():
            out.setdefault(ds.domain, []).append(ds)
        return out


def _parse_dataset(raw: dict[str, Any]) -> Dataset:
    try:
        cls = DatasetClass(raw["class"])
    except KeyError as exc:
        raise ValueError(f"dataset {raw.get('id')!r} has no `class`") from exc
    except ValueError as exc:
        raise ValueError(
            f"dataset {raw.get('id')!r}: unknown class {raw['class']!r}; "
            f"expected one of {[c.value for c in DatasetClass]}"
        ) from exc

    try:
        status = Status(raw.get("status", "candidate"))
    except ValueError as exc:
        raise ValueError(
            f"dataset {raw.get('id')!r}: unknown status {raw.get('status')!r}; "
            f"expected one of {[s.value for s in Status]}"
        ) from exc

    return Dataset(
        id=raw["id"],
        cls=cls,
        domain=raw.get("domain", "unknown"),
        kaggle_slug=raw["kaggle_slug"],
        status=status,
        licence=raw.get("licence"),
        version=raw.get("version"),
        sha256=dict(raw.get("sha256") or {}),
        notes=(raw.get("notes") or "").strip(),
    )


def _parse_pair(raw: dict[str, Any]) -> TablePair:
    return TablePair(
        id=raw["id"],
        a=TableRef(**raw["a"]),
        b=TableRef(**raw["b"]),
        pair_type=PairType(raw.get("pair_type", "p_natural")),
        rationale=raw.get("rationale", ""),
        join_key=tuple(raw["join_key"]) if raw.get("join_key") else None,
    )


def load_registry(path: str | Path = "data/datasets.yaml") -> Registry:
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    datasets = [_parse_dataset(d) for d in raw.get("datasets") or []]
    ids = [d.id for d in datasets]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"duplicate dataset ids in {path}: {sorted(duplicates)}")

    pairs = [_parse_pair(p) for p in raw.get("pairs") or []]

    return Registry(datasets={d.id: d for d in datasets}, pairs=pairs)


def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksums(dataset: Dataset, base: Path) -> list[str]:
    """Return the files that fail verification. An empty list means everything matches."""
    failures: list[str] = []
    for name, expected in dataset.sha256.items():
        target = dataset.root(base) / name
        if not target.exists():
            failures.append(f"{name}: missing")
        elif sha256_file(target) != expected:
            failures.append(f"{name}: checksum mismatch")
    return failures

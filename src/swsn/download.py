"""Dataset download.

Public Kaggle *Datasets* download anonymously through kagglehub (open access since April
2024), so no credentials are required. Competition datasets would need a token and are
deliberately not used as the primary sources.

Usage
-----
    python -m swsn.download --config data/datasets.yaml
    python -m swsn.download --config data/datasets.yaml --only olist
    python -m swsn.download --offline          # verify manually placed files only
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .registry import Dataset, Status, load_registry, verify_checksums

DEFAULT_DATA_DIR = Path("data")


def fetch(dataset: Dataset, data_dir: Path = DEFAULT_DATA_DIR, force: bool = False) -> Path:
    """Download one dataset into ``data/raw/<id>/`` and return the directory."""
    dest = dataset.root(data_dir)
    dest.mkdir(parents=True, exist_ok=True)

    if dest.exists() and any(dest.iterdir()) and not force:
        print(f"[skip] {dataset.id}: already present at {dest}")
        return dest

    try:
        import kagglehub  # imported lazily: the module is useless in --offline mode
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "kagglehub is not installed. Run `uv sync`, or download the CSVs manually "
            "and use --offline (see data/README.md)."
        ) from exc

    ref = dataset.kaggle_slug
    if dataset.version:
        ref = f"{ref}/versions/{dataset.version}"

    print(f"[get ] {dataset.id}: {ref}")
    cached = Path(kagglehub.dataset_download(ref))

    for item in cached.iterdir():
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)

    return dest


def run(
    config: Path,
    data_dir: Path = DEFAULT_DATA_DIR,
    only: list[str] | None = None,
    offline: bool = False,
    force: bool = False,
) -> int:
    registry = load_registry(config)
    selected = [
        ds
        for ds in registry.datasets.values()
        if (only is None or ds.id in only) and ds.status is not Status.DROPPED
    ]
    if not selected:
        print("nothing to do: no matching datasets in the registry", file=sys.stderr)
        return 1

    problems = 0
    for dataset in selected:
        if offline:
            print(f"[ver ] {dataset.id}")
        else:
            try:
                fetch(dataset, data_dir, force=force)
            except RuntimeError as exc:
                print(f"[fail] {dataset.id}: {exc}", file=sys.stderr)
                problems += 1
                continue

        if not dataset.sha256:
            print(f"[warn] {dataset.id}: no checksums recorded yet — record them after triage")
            continue

        failures = verify_checksums(dataset, data_dir)
        for failure in failures:
            print(f"[fail] {dataset.id}: {failure}", file=sys.stderr)
        problems += len(failures)

    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("data/datasets.yaml"))
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--only", nargs="*", help="restrict to these dataset ids")
    parser.add_argument("--offline", action="store_true", help="verify only, no network")
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    args = parser.parse_args(argv)

    return run(args.config, args.data_dir, args.only, args.offline, args.force)


if __name__ == "__main__":
    raise SystemExit(main())

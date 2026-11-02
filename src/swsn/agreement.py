"""Inter-annotator agreement.

Cohen's kappa over binary labels (match / no-match) between two annotators, reported per
pair and pooled. Skipped pairs never enter the calculation — they are excluded, not
treated as agreement.

Usage
-----
    python -m swsn.agreement --gt-dir ground_truth/gt
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

NEGATIVE = "0"
POSITIVE = "1"


def cohen_kappa(a: list[str], b: list[str]) -> float:
    if len(a) != len(b):
        raise ValueError("label lists must be the same length")
    n = len(a)
    if n == 0:
        return float("nan")

    agree = sum(1 for x, y in zip(a, b) if x == y) / n
    pa = sum(1 for x in a if x == POSITIVE) / n
    pb = sum(1 for y in b if y == POSITIVE) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    if expected == 1.0:
        return 1.0
    return (agree - expected) / (1 - expected)


def load_annotations(path: Path) -> dict[tuple[str, str], str]:
    """Read one annotator's file: (col_a, col_b) -> label."""
    out: dict[tuple[str, str], str] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("label", "").strip().lower() in {"skip", ""}:
                continue
            out[(row["col_a"], row["col_b"])] = row["label"].strip()
    return out


def compare(pair_files: dict[str, Path]) -> dict:
    """Return per-pair and pooled kappa for the annotated files of one table pair."""
    if len(pair_files) < 2:
        raise ValueError("need at least two annotators to compute agreement")
    names = sorted(pair_files)
    base = load_annotations(pair_files[names[0]])
    result: dict = {"per_annotator": {}, "pairs": {}}

    for other in names[1:]:
        theirs = load_annotations(pair_files[other])
        common = sorted(set(base) & set(theirs))
        a = [base[k] for k in common]
        b = [theirs[k] for k in common]
        result["per_annotator"][f"{names[0]}__{other}"] = {
            "n": len(common),
            "kappa": cohen_kappa(a, b),
            "disagreements": sum(1 for x, y in zip(a, b) if x != y),
        }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gt-dir", type=Path, default=Path("ground_truth/gt"))
    args = parser.parse_args(argv)

    raw = args.gt_dir / "raw"
    if not raw.exists():
        print(f"no per-annotator files under {raw}; nothing to compare")
        return 1

    for pair_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        files = {f.stem: f for f in pair_dir.glob("*.csv")}
        if len(files) < 2:
            continue
        report = compare(files)
        for key, value in report["per_annotator"].items():
            print(f"{pair_dir.name:30s} {key:20s} n={value['n']:4d} "
                  f"kappa={value['kappa']:.3f} disagreements={value['disagreements']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

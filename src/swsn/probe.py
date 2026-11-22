"""Valentine probe — does the matcher recover relationships that are documented to exist?

The probe uses the matchers and metrics defined in ``evaluation/protocol.yaml``.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
import yaml

MATCHER_FACTORIES = {
    "coma": ("valentine.algorithms", "Coma"),
    "cupid": ("valentine.algorithms", "Cupid"),
    "distribution_based": ("valentine.algorithms", "DistributionBased"),
    "jaccard": ("valentine.algorithms", "JaccardDistanceMatcher"),
    "similarity_flooding": ("valentine.algorithms", "SimilarityFlooding"),
}


def load_protocol(path: str | Path = "evaluation/protocol.yaml") -> dict:
    with Path(path).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def build_matcher(matcher_id: str, params: dict | None = None):
    """Instantiate a Valentine-compatible matcher by ID, importing it lazily."""
    if matcher_id == "normalised_coma" or matcher_id.startswith("normalised_coma_without_"):
        from swsn.extension.config import CanonicalisationConfig
        from swsn.extension.matcher import NormalisedComa

        extension_params = dict(params or {})
        config = CanonicalisationConfig.from_dict(extension_params.pop("config", None))
        if matcher_id != "normalised_coma":
            component = matcher_id.removeprefix("normalised_coma_without_")
            config = config.without(component)
        return NormalisedComa(config=config, **extension_params)

    if matcher_id not in MATCHER_FACTORIES:
        raise KeyError(f"unknown matcher {matcher_id!r}")
    module_name, class_name = MATCHER_FACTORIES[matcher_id]
    module = __import__(module_name, fromlist=[class_name])
    cls = getattr(module, class_name)
    return cls(**(params or {}))


def run_matcher(dfs: list[pd.DataFrame], matcher, names: list[str]):
    from valentine import valentine_match

    return valentine_match(dfs, matcher, df_names=names)


def as_pairs(matches) -> list[tuple[str, str, float]]:
    """Flatten MatcherResults into (source_column, target_column, score)."""
    out = []
    for pair, score in matches.items():
        out.append((pair.source_column, pair.target_column, float(score)))
    return out


def precision_recall_f1(
    predicted: Iterable[tuple[str, str, float]],
    ground_truth: set[tuple[str, str]],
    threshold: float = 0.0,
) -> dict:
    kept = {(a, b) for a, b, s in predicted if s >= threshold}
    tp = len(kept & ground_truth)
    precision = tp / len(kept) if kept else 0.0
    recall = tp / len(ground_truth) if ground_truth else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1,
            "n_predicted": len(kept), "n_gt": len(ground_truth), "tp": tp}


def recovery_at_k(
    predicted: Iterable[tuple[str, str, float]],
    ground_truth: set[tuple[str, str]],
    k: int = 1,
) -> float:
    """Share of documented correspondences appearing in the top-k of each source column."""
    if not ground_truth:
        return 0.0

    ranked: dict[str, list[tuple[str, float]]] = {}
    for a, b, score in predicted:
        ranked.setdefault(a, []).append((b, score))
    for items in ranked.values():
        items.sort(key=lambda item: item[1], reverse=True)

    hits = 0
    for a, b in ground_truth:
        top = [target for target, _ in ranked.get(a, [])[:k]]
        hits += b in top
    return hits / len(ground_truth)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=Path("evaluation/protocol.yaml"))
    parser.add_argument("--dataset", required=False, help="dataset id to probe")
    parser.add_argument("--matcher", default="coma")
    args = parser.parse_args(argv)

    protocol = load_protocol(args.protocol)
    print(f"protocol v{protocol.get('version')} status={protocol.get('status')}")
    print("probe runner is wired up; dataset loading is implemented with the first"
          " admitted dataset (see notebooks/05_probe_recovery.ipynb)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""NormalisedComa — the method, not the preprocessing.

Interface frozen in M2; body is M3/M4 work. The point of freezing it now is that M4's
"method execution" has a target and the type-3 claim ("a new method") is backed by code
rather than by a description.

What it will do differently from Valentine's `Coma`:

1. the schema signal is unchanged — column names, tokenised as Coma does it;
2. the instance signal is computed over *canonical* value sets (``values.py``), so
   formatting, units, sentinels and dates no longer destroy value overlap;
3. the two signals are combined with per-signal weights exposed through
   ``match_details``, which makes the contribution inspectable and the ablation exact;
4. a confidence threshold is derived from the observed score distribution rather than
   fixed, so the decision point adapts to the dataset instead of to the benchmark.

TODO(M3): verify the ``BaseMatcher`` import path and the exact ``get_matches`` signature
against the installed Valentine version before implementing — the published docs describe
the method but not the signature.
"""

from __future__ import annotations

from .config import CanonicalisationConfig

try:  # pragma: no cover - import shape depends on the installed version
    from valentine.algorithms.base_matcher import BaseMatcher  # type: ignore
except ImportError:  # pragma: no cover

    class BaseMatcher:  # type: ignore[no-redef]
        """Fallback so this module imports without Valentine installed."""


class NormalisedComa(BaseMatcher):
    """Normalisation-aware variant of the hybrid COMA matcher."""

    def __init__(
        self,
        config: CanonicalisationConfig | None = None,
        max_distinct_values: int = 1000,
        schema_weight: float = 0.5,
        instance_weight: float = 0.5,
        seed: int = 42,
    ) -> None:
        if not 0.0 <= schema_weight <= 1.0:
            raise ValueError("schema_weight must be in [0, 1]")
        if not 0.0 <= instance_weight <= 1.0:
            raise ValueError("instance_weight must be in [0, 1]")
        if abs(schema_weight + instance_weight - 1.0) > 1e-9:
            raise ValueError("schema_weight + instance_weight must equal 1")

        self.config = config or CanonicalisationConfig()
        self.max_distinct_values = max_distinct_values
        self.schema_weight = schema_weight
        self.instance_weight = instance_weight
        self.seed = seed

    def get_matches(self, source_input, target_input):
        """Return column correspondences between two tables.

        M3 implementation outline:
          1. canonical value sets for both sides (``values.canonical_value_set``);
          2. name similarity for the schema signal;
          3. weighted combination into a score per candidate pair;
          4. ``match_details`` carrying ``name_sim``, ``value_sim`` and the weights.
        """
        raise NotImplementedError(
            "M3: implement NormalisedComa.get_matches — see the module docstring for the "
            "four steps and evaluation/protocol.yaml for the ablation switches"
        )

    def get_matches_batch(self, profiles):
        """Optional batch view; Coma uses it for statistics across all input tables.

        TODO(M3): only override if the batch view genuinely improves the instance signal.
        """
        raise NotImplementedError("M3: decide whether the batch view is needed")

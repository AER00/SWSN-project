"""Combine COMA's flat-schema name signal with canonical value overlap."""

from __future__ import annotations

from itertools import combinations
from statistics import median

import pandas as pd
from valentine.algorithms import BaseMatcher, ColumnPair
from valentine.algorithms.coma.similarity.tokens import tokens_similarity
from valentine.algorithms.coma.similarity.trigram import trigram_similarity
from valentine.data_sources import BaseTable

from .config import CanonicalisationConfig
from .values import DEFAULT_MAX_DISTINCT, canonical_value_set, jaccard


class NormalisedComa(BaseMatcher):
    """Normalisation-aware variant of the hybrid COMA matcher."""

    def __init__(
        self,
        config: CanonicalisationConfig | None = None,
        max_distinct_values: int = DEFAULT_MAX_DISTINCT,
        schema_weight: float = 0.5,
        instance_weight: float = 0.5,
        seed: int = 42,
    ) -> None:
        if max_distinct_values < 0:
            raise ValueError("max_distinct_values must be non-negative")
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
        self._match_details: dict[ColumnPair, dict[str, float]] = {}

    def get_matches(self, source_input: BaseTable, target_input: BaseTable) -> dict[ColumnPair, float]:
        """Return column correspondences between two tables."""
        return self.get_matches_batch([source_input, target_input])

    def get_matches_batch(self, tables: list[BaseTable]) -> dict[ColumnPair, float]:
        """Keep scores at or above the median positive score for each table pair."""
        self._match_details = {}
        matches: dict[ColumnPair, float] = {}
        if len(tables) < 2:
            return matches

        profiles = [
            (table.name, {
                column.name: canonical_value_set(
                    pd.Series(column.data, dtype=object), self.config,
                    max_distinct=self.max_distinct_values, seed=self.seed,
                )
                for column in table.get_instances_columns()
            })
            for table in tables
        ]
        for (source_name, source_values), (target_name, target_values) in combinations(profiles, 2):
            candidates = {}
            for source_column, source_set in source_values.items():
                for target_column, target_set in target_values.items():
                    source_label, target_label = str(source_column), str(target_column)
                    name_sim = max(
                        trigram_similarity(source_label, target_label),
                        tokens_similarity(source_label, target_label),
                    )
                    value_sim = jaccard(source_set, target_set)
                    score = self.schema_weight * name_sim + self.instance_weight * value_sim
                    if score > 0.0:
                        pair = ColumnPair(source_name, source_column, target_name, target_column)
                        candidates[pair] = (score, name_sim, value_sim)

            if not candidates:
                continue
            threshold = median(score for score, _, _ in candidates.values())
            for pair, (score, name_sim, value_sim) in candidates.items():
                if score >= threshold:
                    matches[pair] = score
                    self._match_details[pair] = {
                        "name_sim": name_sim,
                        "value_sim": value_sim,
                        "schema_weight": self.schema_weight,
                        "instance_weight": self.instance_weight,
                    }
        return matches

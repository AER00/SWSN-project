"""Canonicalisation configuration.

Each switch corresponds to exactly one ladder dimension and exactly one row of the M4
ablation table. Turning a switch off must remove a measurable amount of repair — if it
does not, the component is not worth shipping.

    case_and_punctuation   D5 / L3   casefold, punctuation and whitespace variants
    dates                  D4 / L2   multiple date encodings -> one
    numbers_and_units      D4 / L2   separators, currency, units, zero padding, prefixes
    sentinels_and_nulls    D3 / L3   sentinel tokens -> null, mixed types -> parseable
"""

from __future__ import annotations

from dataclasses import dataclass, fields

COMPONENTS = (
    "case_and_punctuation",
    "dates",
    "numbers_and_units",
    "sentinels_and_nulls",
)


@dataclass(frozen=True)
class CanonicalisationConfig:
    case_and_punctuation: bool = True
    dates: bool = True
    numbers_and_units: bool = True
    sentinels_and_nulls: bool = True

    def enabled(self) -> tuple[str, ...]:
        return tuple(name for name in COMPONENTS if getattr(self, name))

    def without(self, component: str) -> CanonicalisationConfig:
        """Copy with one component disabled — the ablation switch."""
        if component not in COMPONENTS:
            raise ValueError(f"unknown component {component!r}; expected {COMPONENTS}")
        values = {f.name: getattr(self, f.name) for f in fields(self)}
        values[component] = False
        return CanonicalisationConfig(**values)

    @classmethod
    def from_dict(cls, raw: dict | None) -> CanonicalisationConfig:
        raw = raw or {}
        unknown = set(raw) - set(COMPONENTS)
        if unknown:
            raise ValueError(f"unknown canonicalisation switches: {sorted(unknown)}")
        return cls(**raw)

    def describe(self) -> str:
        on = [name for name in COMPONENTS if getattr(self, name)]
        return f"CanonicalisationConfig(active={on or ['none']})"

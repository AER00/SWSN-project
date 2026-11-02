"""The protocol is a design document, so it has to be machine-checkable.

This file exists because `evaluation/protocol.yaml` was invalid YAML for the whole first
day and nothing noticed: `headline:` was a list with a mapping key appended. Nothing read
the file until the benchmark runner did.
"""

from pathlib import Path

import pytest

from swsn.probe import build_matcher, load_protocol

PROTOCOL = Path("evaluation/protocol.yaml")


@pytest.fixture(scope="module")
def protocol():
    return load_protocol(PROTOCOL)


def test_protocol_parses_and_is_versioned(protocol):
    assert protocol["version"] >= 1
    assert protocol["status"] in {"provisional", "frozen"}
    if protocol["status"] == "frozen":
        assert protocol["frozen_on"], "a frozen protocol must record the date it was frozen"


def test_every_declared_matcher_can_be_instantiated(protocol):
    for entry in protocol["matchers"]:
        matcher = build_matcher(entry["id"], entry.get("params"))
        assert matcher is not None, entry["id"]


def test_matcher_classes_are_importable_paths(protocol):
    import importlib

    for entry in protocol["matchers"]:
        module_name, _, class_name = entry["class"].rpartition(".")
        module = importlib.import_module(module_name)
        assert hasattr(module, class_name), f"{entry['class']} does not exist"


def test_ladder_levels_are_declared_and_ordered(protocol):
    levels = protocol["sets"]["c_syn"]["levels"]
    assert levels[0] == "L0", "L0 must be the uncorrupted baseline"
    assert len(levels) == len(set(levels))


def test_declared_levels_exist_in_the_ladder_config(protocol):
    from swsn.corrupt import level_order, load_ladder

    declared = set(level_order(load_ladder("corruption/ladder.yaml")))
    for level in protocol["sets"]["c_syn"]["levels"]:
        assert level in declared, f"protocol uses {level}, ladder does not define it"


def test_strata_are_the_four_declared(protocol):
    assert set(protocol["strata"]) == {"S1", "S2", "S3", "S4"}


def test_aggregate_f1_is_restricted(protocol):
    """Reporting a bare F1 is exactly the mistake the strata exist to prevent."""
    assert protocol["reporting"]["aggregate_f1"] == "allowed_only_with_strata"


def test_non_goals_still_forbid_tuning():
    text = PROTOCOL.read_text(encoding="utf-8")
    assert "threshold tuning" in text
    assert "aggregate_f1: allowed_only_with_strata" in text

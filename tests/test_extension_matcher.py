import pandas as pd
import pytest
from valentine import valentine_match
from valentine.algorithms import ColumnPair, Coma

from swsn.extension.config import CanonicalisationConfig
from swsn.extension.matcher import NormalisedComa


def test_normalised_coma_recovers_a_renamed_column_and_exposes_scores():
    source = pd.DataFrame({"amount": ["R$1.234,50", "N/A"]})
    target = pd.DataFrame({"charge": ["1234.5", "unknown"], "amount": ["999", "?"]})
    names = ["orders", "payments"]
    matcher = NormalisedComa(schema_weight=0.2, instance_weight=0.8)
    expected = ColumnPair("orders", "amount", "payments", "charge")

    matches = valentine_match([source, target], matcher, df_names=names)

    assert dict(matches) == {expected: pytest.approx(0.8)}
    assert matches.get_details(expected) == {
        "name_sim": 0.0, "value_sim": 1.0, "schema_weight": 0.2, "instance_weight": 0.8,
    }

    config = CanonicalisationConfig().without("numbers_and_units")
    ablated = NormalisedComa(config=config, schema_weight=0.2, instance_weight=0.8)
    assert expected not in valentine_match([source, target], ablated, df_names=names)


def test_normalised_coma_keeps_comas_name_signal():
    frames = [pd.DataFrame({"quantity": ["red"]}), pd.DataFrame({"quantities": ["blue"]})]
    pair = ColumnPair("aaa", "quantity", "bbb", "quantities")

    baseline = valentine_match(frames, Coma(use_schema=True, use_instances=False))
    matches = valentine_match(frames, NormalisedComa(schema_weight=1.0, instance_weight=0.0))

    assert matches[pair] == pytest.approx(baseline[pair])


def test_normalised_coma_retains_details_for_all_table_pairs():
    frames = [
        pd.DataFrame({"abc": ["2024-03-04"]}),
        pd.DataFrame({"def": ["03/04/2024"]}),
        pd.DataFrame({"ghi": ["04.03.2024"]}),
    ]
    matcher = NormalisedComa(schema_weight=0.0, instance_weight=1.0)
    matches = valentine_match(frames, matcher, df_names=["one", "two", "three"])
    expected = {
        ColumnPair("one", "abc", "two", "def"),
        ColumnPair("one", "abc", "three", "ghi"),
        ColumnPair("two", "def", "three", "ghi"),
    }

    assert dict(matches) == dict.fromkeys(expected, 1.0)
    assert matches.details.keys() == expected
    assert not valentine_match(frames[:2], matcher, instance_sample_size=0)
    assert not matcher.match_details
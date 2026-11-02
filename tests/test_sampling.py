import pandas as pd

from swsn.pairdiag import value_similarity
from swsn.sampling import sample_by_key, sample_pair


def make_tables(n=1000):
    ids = [f"order_{i:05d}" for i in range(n)]
    a = pd.DataFrame({"order_id": ids, "value": range(n)})
    b = pd.DataFrame({"order_id": list(reversed(ids)), "amount": range(n)})
    return a, b


def test_naive_head_sampling_destroys_overlap():
    """Regression guard for the 2026-11-02 bug: this is what NOT to do."""
    a, b = make_tables()
    head_a, head_b = a.head(50), b.head(50)
    assert value_similarity(head_a["order_id"], head_b["order_id"]) == 0.0


def test_sample_pair_preserves_overlap():
    a, b = make_tables()
    sample_a, sample_b = sample_pair(a, b, "order_id", "order_id", max_rows=50, seed=1)
    assert value_similarity(sample_a["order_id"], sample_b["order_id"]) > 0.99


def test_sample_by_key_keeps_all_rows_for_sampled_keys():
    a, b = make_tables()
    sample = sample_by_key(b, "order_id", max_rows=10, seed=2)
    assert sample["order_id"].nunique() == 10
    assert set(sample["order_id"]).issubset(set(a["order_id"]))


def test_value_similarity_is_scale_invariant():
    """Regression guard for the 2026-11-02 bug: subsampling distinct values made two
    identical 100k-element id sets score ~0.005 instead of ~1.0."""
    ids = [f"id_{i:06d}" for i in range(20_000)]
    a = pd.Series(ids)
    b = pd.Series(list(reversed(ids)))
    assert value_similarity(a, b) > 0.99


def test_missing_key_raises():
    a, _ = make_tables()
    try:
        sample_by_key(a, "nope")
    except KeyError:
        return
    raise AssertionError("expected KeyError")

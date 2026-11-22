# NormalisedComa

## M3 Preprocessing

The extension normalises column values before comparing columns, without editing
the source CSVs or their headers. It removes known null tokens first, then
normalises dates, numeric formatting and known unit affixes, and finally text
case, punctuation and whitespace. It does not convert units, translate values,
or repair semantic changes. Sentinel rules are specific to this corruption
ladder: `999` and `-1`, for example, can be legitimate values in other data.

Pandas loads CSVs consistently with the baseline, and Python's standard library
implements the explicit parsing rules with no new runtime dependency. Valentine
provides the `BaseMatcher` interface so both baseline and extension run through
the same harness. See the [tool inventory](tools.md) for the broader experiment.

From the repository root, after `make setup` and
`uv run python -m swsn.download --only olist`, run this before/after demo. It
uses actual Olist values with deliberately altered formats; `N/A` is an
injected missing-value token, not an observed row.

```bash
uv run python - <<'PY'
from datetime import date

from swsn.extension.canonicalise import canonicalise_value
from swsn.tables import load_table

order = load_table("olist", "olist_orders_dataset", nrows=1).iloc[0]
payment = load_table("olist", "olist_order_payments_dataset", nrows=1).iloc[0]
day = date.fromisoformat(order["order_purchase_timestamp"].split()[0])
amount = f'{payment["payment_value"]:.2f}'
payment_type = payment["payment_type"]
examples = {
    "dates": (day.strftime("%d.%m.%Y"), day.isoformat()),
    "numbers_and_units": ("R$ " + amount.replace(".", ","), amount),
    "case_and_punctuation": ("  " + payment_type.upper() + "  ", payment_type),
    "sentinels_and_nulls": ("N/A", ""),
}
for step, (dirty, reference) in examples.items():
    clean = canonicalise_value(dirty)
    assert clean == canonicalise_value(reference), step
    print(f"{step}: {dirty!r} -> {clean!r}")
PY
```

## M4 Matcher Evaluation

```bash
uv run python -m swsn.download --only olist instacart
uv run python -m swsn.run_benchmark --extension --datasets olist instacart
```

`--extension` reads the baselines and four leave-one-out ablations from the
[protocol](../evaluation/protocol.yaml). It writes `results_attribution.csv`
and `results_cumulative.csv` under `evaluation/m4/`, without overwriting M2.
Each CSV has 420 successful runs: 12 documented pairs x 5 levels x 7 matchers.
Attribution applies each level in isolation; cumulative mode stacks the levels.

Cumulative Recovery@1 (mean over pairs, 22 November 2026):

| Matcher | L0 | L1 | L2 | L3 | L4 |
|---|---:|---:|---:|---:|---:|
| Valentine COMA (instances on) | .958 | .542 | .486 | .486 | .403 |
| Valentine Jaccard | .875 | .708 | .403 | .403 | .403 |
| NormalisedComa | .931 | .569 | .514 | .514 | .542 |
| Without case/punctuation | .931 | .569 | .514 | .514 | .514 |
| Without dates | .931 | .569 | .514 | .514 | .542 |
| Without numbers/units | .931 | .569 | .431 | .431 | .458 |
| Without sentinels/nulls | .931 | .569 | .514 | .514 | .542 |

The full extension beats these two baselines on cumulative L2/L3, but not both
at every level. The numeric ablation changes Recovery@1 for Instacart
`products`/`aisles` at L2-L4; the text ablation changes it for Olist
customers/sellers at L4 only. No ablation changes attribution Recovery@1.
Dates and null normalisation show no measured benefit on this grid. The sole
annotated S3 correspondence has Recovery@1 of zero across all variants and
levels in both modes. Recovery@3 is degenerate on three of the twelve pairs.

The extension uses COMA's flat-schema name scores, Jaccard on canonical value
sets, a 50/50 blend and a per-pair median threshold on positive scores. Its
comparison with COMA therefore does not isolate preprocessing; leave-one-out
comparisons isolate individual steps within the extension. L4 is a semantic
negative control, not evidence that the method repairs changed meaning. These
are first results under the provisional protocol, not a claim of general
superiority or formal novelty.
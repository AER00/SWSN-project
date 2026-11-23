# NormalisedComa

## M3 Preprocessing

The extension normalises column values before comparing columns, without editing
the source CSVs or their headers. It removes known null tokens first, then
normalises dates, numeric formatting and known unit affixes, and finally text
case, punctuation and whitespace. It does not convert units, translate values,
or repair semantic changes. Sentinel rules are specific to this corruption
ladder: `999` and `-1`, for example, can be legitimate values in other data.
Run the pipeline once on raw values. For example, `00000999` becomes `999` on
the first pass, and a second pass treats `999` as a missing-value marker.
An ambiguous number such as `1,234` is read as a grouped integer.

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
uv run python -m swsn.m4_report
```

`--extension` reads the baselines and four leave-one-out ablations from the
[protocol](../evaluation/protocol.yaml). It writes `results_attribution.csv`
and `results_cumulative.csv` under `evaluation/m4/`, without overwriting M2.
Each CSV has 420 successful runs: 12 documented pairs x 5 levels x 7 matchers.
Attribution applies each level in isolation; cumulative mode stacks the levels.
The report command reads both CSVs and rebuilds the vector figures.

- [M4 presentation](../reports/Valentine_M4_deck.pptx)
- [Matcher comparison](../reports/figures/m4_recovery.svg)
- [Numeric and unit normalisation ablation](../reports/figures/m4_numeric_ablation.svg)

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

With cumulative format noise (L2 and L3), NormalisedComa leads COMA by 2.8
percentage points and Jaccard by 11.1 on mean Recovery@1 across table pairs.
Turning off numeric and unit cleanup reduces the L2 mean by 8.3 points. This
change comes from the Instacart `products`/`aisles` pair. Turning off text cleanup
changes the Olist customers/sellers pair at L4 only. The date and null ablations
give the same Recovery@1 across this grid. In attribution mode, all four
ablations give the same Recovery@1 as the full extension.

### Recovery by match type at cumulative L2

The cells count documented matches ranked first across all pairs. The ladder
figure gives each table pair equal weight, so a one-match pair can have a larger
effect per match than a pair with several matches.

| Matcher | S1 similar names | S2 different names | S3 format or grain | Total |
|---|---:|---:|---:|---:|
| Valentine COMA | 5/11 | 4/6 | 0/1 | 9/18 |
| Valentine Jaccard | 4/11 | 4/6 | 0/1 | 8/18 |
| NormalisedComa | 6/11 | 2/6 | 0/1 | 8/18 |

### Comparison with the COMA paper

Do and Rahm’s COMA combines multiple schema matchers and explores reuse of
earlier matches. We apply that idea of combining signals to flat Kaggle tables.
NormalisedComa keeps the flat column-name score and blends it 50/50 with
Jaccard overlap on canonical value sets. It keeps candidates at or above the
median positive score for each pair. Explicit cleanup rules let us inspect what
changes and switch off individual rules. The measured baseline is the installed
Valentine COMA with instance matching enabled. [Do and Rahm, VLDB 2002](https://www.vldb.org/conf/2002/S17P03.pdf) ·
[Koutras et al., ICDE 2021](https://arxiv.org/abs/2010.07386)

The COMA comparison changes value scoring and candidate selection as well as
preprocessing. The ablations measure what happens when one cleanup step is
removed from the extension. L4 is a semantic negative control. The evaluation
uses two datasets and one seed under the checked-in provisional protocol.
The only S3 match was missed at every level in both modes, and Recovery@3 is
degenerate on three pairs. These results support a narrow claim about format
cleanup on this benchmark.

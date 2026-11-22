"""Build the seven EDA notebooks and the M3 tool notebooks.

Kept as a script rather than seven hand-edited JSON files: the notebooks are executable
documents over a library, so their content is a dozen calls each and editing JSON by hand
is how a notebook and the library drift apart.

    python notebooks/_build.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent

SETUP = """\
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd().parent / "src"))
import pandas as pd
pd.set_option("display.max_columns", 60)
pd.set_option("display.width", 160)
"""


def _cell_id(text: str) -> str:
    """Stable id per cell source, so rebuilding does not churn the files."""
    return "c" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:15]


def md(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": _cell_id(text),
        "metadata": {},
        "source": text.strip("\n").splitlines(True),
    }


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "id": _cell_id(text),
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.strip("\n").splitlines(True),
    }


def notebook(title: str, cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.13"},
            "title": title,
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


NOTEBOOKS: dict[str, dict] = {}

# --------------------------------------------------------------------- 00 triage
NOTEBOOKS["00_dataset_triage"] = notebook("00 Dataset Triage", [
    md("""
# 00 Dataset triage

Candidates are scored against the G1–G5 admission gate from the plan. A dataset is used
only if all five pass; a drop is recorded with the reason it failed, not just removed.

**Scope:** the full gate has been run on the two C-doc datasets (Olist, Instacart), which
need schema files and hand-identified correspondences for G3. The six C-nat datasets are
registered with G1 only (slug, licence, checksum) and stay `candidate` until G3/G4 are
checked after annotation. MovieLens was dropped (HTTP 403).
"""),
    code(SETUP),
    md("## The registry"),
    code("""
from swsn.registry import load_registry

registry = load_registry("../data/datasets.yaml")
pd.DataFrame([
    {
        "dataset": d.id,
        "class": d.cls.value,
        "domain": d.domain,
        "version": d.version,
        "licence": d.licence,
        "status": d.status.value,
        "files checksummed": len(d.sha256),
    }
    for d in registry.datasets.values()
]).sort_values(["class", "status", "dataset"])
"""),
    md("""
## Why MovieLens was dropped

The slug `grouplens/movielens-25m-dataset` returns **HTTP 403** from the public Kaggle
metadata endpoint, so it is either not public or no longer exists under that name. It was
optional in the plan; Olist and Instacart already give the contrast the report needs, and
the days saved go to the C-nat annotation round.

## Licences are in the API, not on the page

The dataset page renders its metadata sidebar client-side, so fetching the HTML returns
only the title. `https://www.kaggle.com/api/v1/datasets/view/<owner>/<slug>` returns JSON
with `licenseName`, anonymously. Every licence above was read from there.
"""),
    md("## Gate results (C-doc datasets only)"),
    code("""
import json, pathlib
path = pathlib.Path("../evaluation/triage.json")
if path.exists():
    payload = json.loads(path.read_text())
    display(pd.DataFrame([r["summary"] for r in payload]))
    for r in payload:
        print(f"--- {r['summary']['dataset']}")
        for g in r["gates"]:
            print(f"  {g['gate']} {'pass' if g['passed'] else 'FAIL'}  {g['evidence']}")
else:
    print("run `python -m swsn.triage` first, or `make bench`")
"""),
    md("""
## What the gate actually excluded

Nothing was excluded for being too messy — the two C-doc datasets pass the messiness gate
at exactly **3 of 7 dimensions**, which is the minimum. D1 (header noise), D2 (type
instability) and D4 (format heterogeneity) are absent from both at L0. That is the finding
that motivates the corruption ladder: the dimensions a matcher is most sensitive to are
precisely the ones real Kaggle data does not have.
"""),
])

# ------------------------------------------------------------------ 01 inventory
NOTEBOOKS["01_inventory"] = notebook("01 Inventory", [
    md("""
# 01 Inventory

What is actually in the collection: tables, columns, inferred dtypes, null shares. Read
before any analysis, because every later claim is a claim about *these* files.
"""),
    code(SETUP),
    code("""
from swsn.registry import load_registry
from swsn.tables import load_tables
from swsn.schema_doc import load_all_schemas

registry = load_registry("../data/datasets.yaml")
schemas = load_all_schemas("../ground_truth/schema")

rows = []
for did, schema in schemas.items():
    tables = load_tables(did, list(schema["tables"]), data_dir="../data", nrows=50_000)
    for name, df in tables.items():
        rows.append({
            "dataset": did,
            "table": name,
            "columns": len(df.columns),
            "rows (sampled)": len(df),
            "documented columns": len(schema["tables"][name].get("columns") or []),
            "null share": round(float(df.isna().mean().mean()), 4),
        })
pd.DataFrame(rows).sort_values(["dataset", "table"])
"""),
    md("## Column types, as pandas infers them"),
    code("""
for did, schema in schemas.items():
    print(f"=== {did}")
    tables = load_tables(did, list(schema["tables"]), data_dir="../data", nrows=5_000)
    for name, df in tables.items():
        print(f"  {name}")
        print("   ", dict(df.dtypes.astype(str)))
"""),
    md("""
Note the misspelling carried in the Olist source itself: `product_name_lenght` and
`product_description_lenght`. It is in the published schema too, so it is transcribed as
is — a canonicaliser that normalises Portuguese and English does not fix a typo.
"""),
])

# ------------------------------------------------------------------- 02 dirtiness
NOTEBOOKS["02_dirtiness"] = notebook("02 Dirtiness", [
    md("""
# 02 Dirtiness profile (D1–D7)

Per-column heuristics, aggregated per table. Every number here has to be defensible in the
report, so nothing is a learned score.
"""),
    code(SETUP),
    code("""
from swsn.profile import profile_table, table_summary, dimension_flags, DIMENSION_FLAGS

print("dimension definitions")
for dim, rule in DIMENSION_FLAGS.items():
    print(f"  {dim}: {rule}")
"""),
    code("""
from swsn.schema_doc import load_all_schemas
from swsn.tables import load_tables

schemas = load_all_schemas("../ground_truth/schema")
summaries = []
for did, schema in schemas.items():
    tables = load_tables(did, list(schema["tables"]), data_dir="../data", nrows=50_000)
    for name, df in tables.items():
        summary = table_summary(profile_table(df))
        flags = dimension_flags(summary)
        summaries.append({"dataset": did, "table": name,
                          **{k: int(v) for k, v in flags.items()},
                          "n": sum(flags.values())})
pd.DataFrame(summaries).sort_values("n", ascending=False)
"""),
    md("## The dimension-by-table matrix"),
    code("""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd().parent / "src"))
from IPython.display import SVG, display
display(SVG(filename="../reports/figures/f1_dirtiness.svg"))
"""),
    md("""
## Reading the matrix

- **D1, D2 and D4 are empty everywhere.** Both datasets have clean snake_case headers,
  stable inferred types and one format per column. Whatever "messy Kaggle data" means, it
  is not this, at L0.
- **D3 is structural where it appears.** Instacart's `days_since_prior_order` is null for
  every user's first order — 206k of 3.4M rows. That is the definition of the column, not
  missing data.
- **D7 fires on money and counts.** Prices, payment values and weights are all strongly
  right-skewed; that is what `DistributionBased` sees and what makes it behave differently
  from the string matchers.

The mess this project is about is therefore mostly *cross-table* — the same concept written
differently on each side — which is exactly what the strata and the D8 quadrants measure,
and exactly what the L1–L4 operators introduce.
"""),
])

# ------------------------------------------------------------- 03 documentation
NOTEBOOKS["03_documentation_audit"] = notebook("03 Documentation Audit", [
    md("""
# 03 Documentation audit (D9)

The published schema is our ground truth, so it has to be checked against the files before
it is trusted. A documented column that is absent, or a documented foreign key that does not
resolve, is a finding either way: stale documentation is itself a form of dirtiness.
"""),
    code(SETUP),
    code("""
from swsn.audit import audit_dataset
from swsn.schema_doc import load_all_schemas
from swsn.tables import load_tables

schemas = load_all_schemas("../ground_truth/schema")
for did, schema in schemas.items():
    tables = load_tables(did, list(schema["tables"]), data_dir="../data")
    report = audit_dataset(did, schema, tables)
    print(f"=== {did}")
    print("   ", report.summary())
    for t in report.tables:
        if t.missing_columns or t.undocumented_columns:
            print(f"    {t.table}: missing={t.missing_columns} undocumented={t.undocumented_columns}")
    for fk in report.foreign_keys:
        print(f"    FK {fk.child_table}.{fk.child_column} -> {fk.parent_table}.{fk.parent_column}"
              f"  {fk.resolving_share:.2%}  nulls={fk.child_nulls}")
    print()
"""),
    md("""
## Result

Column coverage **1.00** for both datasets, zero missing and zero undocumented columns, and
**all 12 documented foreign keys across the two datasets resolve at 100.00 %**, on tables up
to 32 million child rows.

That is the precondition for the whole C-doc design: if the documentation did not hold, the
ground truth derived from it would be worthless. Row counts are not published, so
`row_count` is null in the schema files and that column of the audit says nothing rather
than guessing a number.

## The BOM

`product_category_name_translation.csv` starts with a UTF-8 byte-order mark
(`ef bb bf`). pandas strips it with the C parser; a plain `csv.DictReader` does not, and the
first column becomes `"\\ufeffproduct_category_name"`. `swsn.tables` reads with
`encoding="utf-8-sig"` so the documented name always holds — but anything reading these
files another way will see a phantom column.
"""),
])

# ---------------------------------------------------------------- 04 cross table
NOTEBOOKS["04_cross_table"] = notebook("04 Cross-Table Signal", [
    md("""
# 04 Cross-table signal (D8)

For every candidate column pair across two tables: how similar are the *names*, and how much
do the *values* overlap? This locates, before any matcher runs, which documented
correspondences are easy (Q1), which are synonyms (Q2), which are traps (Q3) and which are
unrelated (Q4) — so a matcher's failure can be attributed to the signal it needed.
"""),
    code(SETUP),
    code("""
from swsn.benchmark import d8_quadrants
from swsn.schema_doc import load_schema
from swsn.tables import load_tables

schema = load_schema("../ground_truth/schema/olist.yaml")
products = load_tables("olist", ["olist_products_dataset"], data_dir="../data", nrows=50_000)
translation = load_tables("olist", ["product_category_name_translation"], data_dir="../data")

frame = d8_quadrants(
    products["olist_products_dataset"], translation["product_category_name_translation"],
    "olist_products_dataset", "product_category_name_translation", schema,
)
frame.sort_values(["stratum", "name_sim"], ascending=[True, False])
"""),
    md("""
## The pair that matters

`product_category_name` ↔ `product_category_name_english` sits at **name similarity 0.72,
value overlap 0.03**: the column names agree almost perfectly and the values share almost
nothing, because one side is Portuguese and the other English.

Every string-similarity matcher ranks the *identical-name* column first — correctly, that
one is also a real correspondence — and never promotes the translated one above it. This is
the single correspondence the project's extension exists to recover, and no built-in
matcher recovers it at any corruption level (see notebook 06).
"""),
    code("""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd().parent / "src"))
from IPython.display import SVG, display
display(SVG(filename="../reports/figures/f2_quadrants.svg"))
"""),
    md("""
## A caveat that cost a day

`value_similarity` compares exact value sets. An earlier version subsampled 1,000 distinct
values per side before taking the Jaccard overlap; with ~99,400 distinct order ids per side,
two *identical* value domains scored **0.0055 instead of 0.99999**, and the most trivial
match in the dataset was classified as a trap. Jaccard over sampled distinct sets is not
scale-invariant. The default is now exact sets, and `tests/test_pairdiag_and_normalize.py`
pins it.
"""),
])

# -------------------------------------------------------------- 05 probe
NOTEBOOKS["05_probe_recovery"] = notebook("05 Probe and Recovery", [
    md("""
# 05 How well does Valentine recover documented relationships?

The core measurement: for each documented table pair, does each of Valentine's built-in
matchers put the documented column in the top-k for its source column?
"""),
    code(SETUP),
    code("""
results = pd.read_csv("../evaluation/results_attribution.csv")
print(f"{len(results)} runs, {int((results.status != 'ok').sum())} errors")
results.groupby(["matcher", "status"]).size().unstack(fill_value=0)
"""),
    md("""
## Recovery@1 by level, by matcher (attribution mode)

Each level applies only its own operators to the original data, so levels do not stack and
a later level can recover (COMA: 0.542 at L1, back to 0.958 at L2). L0 is the uncorrupted
baseline. Cumulative results are in notebook 06.

The `recovery_at_*_degenerate` flags mark runs where the target table has so few columns
that top-k contains everything. Those runs are excluded from the means — a column of 1.0s
the matcher did not earn would flatter every matcher equally and hide the differences the
table exists to show.
"""),
    code("""
from swsn.run_benchmark import summary

summary(results).to_string()
"""),
    md("## Per-document table pair, at L0"),
    code("""
l0 = results[(results.level == "L0") & (results.status == "ok")]
l0.pivot_table(index=["dataset", "pair_id"], columns="matcher",
               values="recovery_at_1", aggfunc="first").round(2)
"""),
    md("""
## DistributionBased does not run reliably here

12 of 300 runs raise, all from this one matcher, in two distinct ways:

- `PulpSolverError` from `COIN_CMD` — reproducible on the same input. The bundled CBC
  binary runs fine standalone, so it is the invocation.
- `ValueError: malformed node` from `literal_eval(v.name)` — the solver's variable names are
  built as `"(order_id,payment_type)"` and parsed back as a Python tuple, which only works
  when the vertex names are numeric.

valentine 1.1.0 declares `PuLP[cbc]>=4.0,<5.0`, so this is a defect against its own declared
dependency, not a pinning mistake on our side. It stays in the grid with its failure count
reported and is excluded from cross-matcher comparison.
"""),
])

# -------------------------------------------------------- 06 corruption ladder
NOTEBOOKS["06_corruption_ladder"] = notebook("06 Corruption Ladder", [
    md("""
# 06 Corruption ladder

Real Kaggle data turned out to be clean in the dimensions a matcher is most sensitive to
(D1, D2, D4 are empty at L0 for both C-doc datasets). So those dimensions are introduced
deliberately, one per level, with ground truth preserved through recorded rename maps.

**Two modes, and the report must say which one a table shows:**

- *attribution* — each level applies only its own operators to the original frame. Later
  levels are not necessarily worse, because the corruptions do not stack. Answers "which
  dimension breaks which matcher signal".
- *cumulative* — levels 0..n applied in order. Answers "how does recovery decay as dirt
  accumulates".
"""),
    code(SETUP),
    code("""
from swsn.corrupt import load_ladder, level_order, parse_level

ladder = load_ladder("../corruption/ladder.yaml")
for level in level_order(ladder):
    specs = parse_level(ladder, level)
    print(f"{level}: {specs[0].dimension if specs else '—'}  {[s.id for s in specs]}")
"""),
    md("## The degradation curve"),
    code("""
cumulative = pd.read_csv("../evaluation/results_cumulative.csv")
from swsn.run_benchmark import summary
summary(cumulative).to_string()
"""),
    code("""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd().parent / "src"))
from IPython.display import SVG, display
display(SVG(filename="../reports/figures/f3_degradation.svg"))
display(SVG(filename="../reports/figures/f4_strata_coma.svg"))
"""),
    md("""
## Attribution mode, for comparison

Each level on its own (not stacked). Per-operator ablation (one operator at a time) is not
run yet; it is planned for M3/M4.
"""),
    code("""
attribution = pd.read_csv("../evaluation/results_attribution.csv")
summary(attribution).to_string()
"""),
    md("""
## What it shows

For the name-based matchers (COMA, Cupid) header noise (L1) accounts for most of the loss; for Jaccard and DistributionBased the value levels cost more. COMA (with instance values) drops from 0.958 to
0.542 the moment columns are renamed, abbreviated and translated, and loses a further 0.14
over the value levels.

And by stratum: **the S3 correspondence — the one genuine cross-lingual pair — is recovered
by no matcher at any level, at 0.0 throughout**, while S1 sits at 1.0 until L1 (S1 identical-name keys then halve for COMA).

Caveat: S3 is a single pair, and at k=1 only one of the two correspondences sharing the
source column can be hit.

That 0.0 is the case for the project's extension. Everything else recovers; this does not.
"""),
    md("""
## Reproducing

```bash
make bench      # evaluation/results_attribution.csv + results_cumulative.csv
make figures    # reports/figures/*.pdf + *.svg
```
"""),
])


# ------------------------------------------------------- tool notebooks (M3)
NOTEBOOKS["tool_rapidfuzz"] = notebook("tool_rapidfuzz", [
    md("""
# rapidfuzz — introductory notebook

M3 requires a minimal notebook per selected tool. This one covers **rapidfuzz**, the
fuzzy-string library the project depends on (`pyproject.toml`). It is short on purpose:
setup, the two scoring choices that matter here (plain `ratio` vs `token_set_ratio`), and
one worked example on column names and one on category values.

`rapidfuzz` is a C++ implementation of the string metrics popularised by `fuzzywuzzy`.
It is fast enough to score every column-name pair between two tables, which is what makes
it usable inside a diagnostic rather than only offline.

**Why it is relevant to this project.** The D8 cross-table diagnostic
(`src/swsn/pairdiag.py`) scores names with a hand-rolled exact-token Jaccard: it returns
0.33 for `customer_city` vs `customer_cty` and 0.50 for `price` vs `price (brl)`, even
though a human reads both pairs as the same column. Fuzzy scoring is the obvious
replacement signal, and *which* scorer to use — and what has to happen before it — is the
content of this notebook.
"""),
    code(SETUP),
    md("""
## Setup

rapidfuzz is a project dependency, so there is no install step. Every scorer returns a
score in `[0, 100]`.
"""),
    code("""
from rapidfuzz import __version__ as rapidfuzz_version, fuzz
from rapidfuzz.utils import default_process

print("rapidfuzz", rapidfuzz_version)
print("default_process('Credit_Card (BRL)') ->", repr(default_process("Credit_Card (BRL)")))

for name in ("ratio", "partial_ratio", "token_sort_ratio", "token_set_ratio", "WRatio"):
    scorer = getattr(fuzz, name)
    print(f"{name:18} {scorer('order id', 'order_id'):6.2f}  {scorer('payment', 'payment_value'):6.2f}")
"""),
    md("""
## Two defaults that will bite you

rapidfuzz scores **raw characters** unless you pass a `processor`. That has two
consequences the project cannot ignore:

1. **Every scorer is case-sensitive.** `boleto` vs `BOLETO` scores 0 — the strings share
   no case-matching characters beyond the empty one.
2. **`token_*` scorers split on whitespace only.** `order_status` is one token; it does
   not line up with the tokens of `status of order`. Snake_case names therefore behave
   like single opaque strings instead of word sequences.

Both are fixed in one step by `default_process`, which lowercases and maps every
non-alphanumeric character to a space — the same normalisation the project's
canonicalisation does before any comparison. The cell below shows the difference in
isolation, because it is the single most common way a rapidfuzz score looks "wrong".
"""),
    code("""
cases = [
    ("boleto", "BOLETO"),
    ("order_status", "status of order"),
    ("credit_card", "credit card"),
    ("customer_city", "customer_cty"),
]

for a, b in cases:
    raw = fuzz.token_set_ratio(a, b)
    proc = fuzz.token_set_ratio(a, b, processor=default_process)
    print(f"{a:14} | {b:20} raw {raw:6.1f}   with default_process {proc:6.1f}")
"""),
    md("""
- Case: `boleto`/`BOLETO` goes 0 → 100.
- Separator: `order_status`/`status of order` goes ~81 → 100, because the underscore now
  becomes a token boundary.
- A typo is already handled without preprocessing: `customer_city`/`customer_cty` scores
  96 in both modes, which is exactly the case an exact-token measure misses.

So the rest of the notebook reports scores **with `default_process` applied**, and says so.
"""),
    md("""
## Scorer choice on column names

`ratio` compares the character sequences; `token_sort_ratio` sorts whitespace-separated
tokens before comparing; `token_set_ratio` compares token *sets*, so a superset (an
appended unit or language marker) scores as high as an exact match.

The rows are the kinds of names the corruption ladder produces: a unit or language marker
appended, a rename, a typo, a reorder. The last column is the project's current
exact-token Jaccard for reference.
"""),
    code("""
from swsn.pairdiag import name_similarity

name_pairs = [
    ("order_id", "order id"),
    ("customer_zip_code_prefix", "geolocation_zip_code_prefix"),
    ("price", "PRICE (BRL)"),
    ("product_category_name", "product_category_name (en)"),
    ("customer_city", "customer_cty"),
    ("order_status", "status_of_order"),
    ("shipping_limit_date", "Unnamed: 3"),
    ("review_score", "review_comment_title"),
]

pd.DataFrame(
    [
        {
            "a": a,
            "b": b,
            "ratio": round(fuzz.ratio(a, b, processor=default_process), 1),
            "token_sort": round(fuzz.token_sort_ratio(a, b, processor=default_process), 1),
            "token_set": round(fuzz.token_set_ratio(a, b, processor=default_process), 1),
            "token_jaccard (project)": round(name_similarity(a, b), 2),
        }
        for a, b in name_pairs
    ]
)
"""),
    md("""
What to take from the table:

- **An appended unit is the `token_set_ratio` column** — `price` vs `PRICE (BRL)` scores
  66.7 with `ratio` (the suffix costs a third of the score) and 100 with `token_set`.
- **A reorder plus a stopword needs `token_set_ratio`** — `order_status` vs
  `status_of_order` goes 44.4 → 88.9 → 100 across `ratio`, `token_sort_ratio` and
  `token_set_ratio`: sorting removes the order penalty, and set comparison ignores the
  extra `of`.
- **A typo is where character-level scoring earns its place** — `customer_city` vs
  `customer_cty` is 96, against 0.33 for exact-token Jaccard.
- **No scorer fixes a rename** — `shipping_limit_date` vs `Unnamed: 3` is low for every
  scorer above. That is L1 and semantic territory; string similarity cannot cross it,
  and the extension is supposed to be honest about that boundary.
"""),
    md("""
## Category values

The same question for values rather than names, using categories the project actually
uses (Olist statuses and payment types, Brazilian state names, product categories). The
last three rows are the boundary case: a Portuguese→English translation.
"""),
    code("""
value_pairs = [
    ("delivered", "Delivered"),
    ("shipped", "shiped"),
    ("credit_card", "credit card"),
    ("boleto", "BOLETO"),
    ("voucher", "voucher "),
    ("SP", "São Paulo"),
    ("beleza_saude", "health_beauty"),
    ("casa_conforto", "home comfort"),
    ("telefonia_fixa", "landline_phone"),
]

pd.DataFrame(
    [
        {
            "a": a,
            "b": b,
            "ratio": round(fuzz.ratio(a, b, processor=default_process), 1),
            "token_sort": round(fuzz.token_sort_ratio(a, b, processor=default_process), 1),
            "token_set": round(fuzz.token_set_ratio(a, b, processor=default_process), 1),
        }
        for a, b in value_pairs
    ]
)
"""),
    md("""
Two conclusions the project relies on:

1. **Fuzzy scoring is a clustering aid, not a matcher.** After preprocessing, same-language
   variants (`delivered`/`Delivered`, `credit_card`/`credit card`, `boleto`/`BOLETO`) all
   sit near 100, which is what D5 (categorical variants) measures. It does not decide that
   two *columns* correspond — that needs the value overlap on canonicalised value sets.
2. **It cannot cross a language or a code.** `beleza_saude`/`health_beauty` scores ~40,
   `casa_conforto`/`home comfort` ~56, `SP`/`São Paulo` 18–36, `telefonia_fixa`/`landline_phone`
   ~29–36 — far below the ~100 of a same-language variant. The project puts those in L4 and
   treats them as out of reach for normalisation; a low score here is the correct,
   negative-control behaviour, not a bug to tune away.
"""),
    md("""
## Using it on a table

One worked call on the project's own ground-truth column names: take the columns of one
table and ask which are closest to a query name. `process.extract` runs the loop. The
score tells you *closeness*; the threshold is a decision, not a default.
"""),
    code("""
from rapidfuzz import process

columns = [
    "order_id", "customer_id", "order_status", "order_purchase_timestamp",
    "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

for query in ("order date", "purchase time", "customer"):
    best = process.extract(query, columns, scorer=fuzz.token_set_ratio,
                           processor=default_process, limit=3)
    print(f"{query!r:16} ->", [(choice, round(score, 1)) for choice, score, _ in best])
"""),
    md("""
What this exposes:

- `order date` returns **three different date columns all at 100**, because each contains
  the token set {order, date}. The score cannot tell `order_delivered_carrier_date` from
  `order_estimated_delivery_date`, which is exactly the many-to-one decision the matcher
  has to make with value overlap, not string similarity.
- `customer` matches both `customer_id` and `order_delivered_customer_date` at 100, for
  the same set-containment reason.

So: use rapidfuzz as a **signal**, never as a decision rule. The project's D8 diagnostic
keeps exact-token Jaccard deliberately (see `docs/findings.md` on D8); this notebook shows
what would change if that were swapped for `token_set_ratio`, and why the swap is a
trade-off rather than a strict improvement.
"""),
    md("""
## Reproducing

```bash
make notebooks   # regenerate notebooks/*.ipynb from scripts/notebook builder
make eda         # execute every notebook in place
```

The project's own name-similarity function is `swsn.pairdiag.name_similarity`. It is
exact-token by design: changing the diagnostic's signal changes the D8 quadrant counts,
so the swap belongs in a commit that re-runs the diagnostic and updates the figures.
"""),
])


NOTEBOOKS["tool_valentine"] = notebook("tool_valentine", [
    md("""
# valentine — introductory notebook

M3 requires a minimal notebook per selected tool. This one covers **valentine**, the
library under study: load two tables, run a matcher, read the result object, score it
against documented ground truth, and register a trivial matcher of your own.

The project uses Valentine as the baseline suite; the extension in
`src/swsn/extension/` is a `BaseMatcher` subclass that plugs into the same harness.
"""),
    code(SETUP),
    md("""
## Two tables

Loaded through the project's table loader so the path, encoding and sampling match every
other notebook and the benchmark. Both tables come from Olist and are documented as
joinable on `order_id`.
"""),
    code("""
from swsn.tables import load_table

orders = load_table("olist", "olist_orders_dataset", data_dir="../data", nrows=5000)
payments = load_table("olist", "olist_order_payments_dataset", data_dir="../data", nrows=5000)
print("orders  ", orders.shape)
print("payments", payments.shape)
print("orders columns  :", list(orders.columns))
print("payments columns:", list(payments.columns))
"""),
    md("""
## Run a matcher

`valentine_match` takes a list of tables, a matcher instance and names for the tables.
It returns a `MatcherResults`, which is a read-only mapping from `ColumnPair` to a score.
Coma is hybrid here: schema (name) similarity and instance (value) similarity.
"""),
    code("""
from valentine import valentine_match
from valentine.algorithms import Coma

matches = valentine_match(
    [orders, payments],
    Coma(use_schema=True, use_instances=True),
    df_names=["orders", "payments"],
)
print(f"{len(matches)} candidate pairs")
for pair, score in list(matches.items())[:5]:
    print(f"{pair.source_column:35} -> {pair.target_column:25} {score:.3f}")
"""),
    md("""
## Reading `MatcherResults`

The mapping is sorted from highest to lowest score, so the first item is the matcher's
best proposal. `get_details(pair)` returns the per-sub-matcher breakdown when the matcher
provides one — for Coma, the name and instance components.
"""),
    code("""
best = next(iter(matches))
print("best pair :", best)
print("score     :", round(matches[best], 3))
print("details   :", matches.get_details(best))
"""),
    md("""
## Score against documented ground truth

The publisher documents which columns correspond, so the ground truth does not have to be
hand-annotated. `ground_truth_set` returns `(source_column, target_column)` pairs for one
table pair; Valentine's metrics accept full `ColumnPair` instances, which keeps the table
names in the comparison.
"""),
    code("""
from swsn.schema_doc import load_schema, documented_correspondences, ground_truth_set

schema = load_schema("../ground_truth/schema/olist.yaml")
correspondences = documented_correspondences(schema)
gt_pairs = ground_truth_set(
    correspondences, "olist_orders_dataset", "olist_order_payments_dataset"
)
print("documented pairs for orders x payments:", sorted(gt_pairs))
"""),
    code("""
from valentine.algorithms import ColumnPair
from valentine.metrics import Precision, Recall, F1Score

ground_truth = [ColumnPair("orders", a, "payments", b) for a, b in gt_pairs]
for metric in (Precision(), Recall(), F1Score()):
    print(metric.apply(matches, ground_truth))
"""),
    md("""
The numbers look harsh because this table pair has **one** documented correspondence, so
precision and recall are coarse: one wrong proposal among the candidates halves
precision. The benchmark uses twelve pairs and reports by stratum for exactly this reason
(`evaluation/protocol.yaml`). The default `one_to_one=True` applies Hungarian selection;
pass `one_to_one=False` to score the raw proposal set instead.
"""),
    md("""
## Register your own matcher

Every matcher implements one method, `get_matches(source_input, target_input)`, and returns
a dict of `ColumnPair` to score. The batch method has a default that calls `get_matches`
over every pair of tables, so a two-table matcher needs nothing else. This one proposes a
pair only when the two column names are identical — the simplest possible baseline.
"""),
    code("""
from valentine.algorithms import BaseMatcher, ColumnPair

class ExactNameMatcher(BaseMatcher):
    \"\"\"Propose a pair only when the two column names are identical.\"\"\"

    def get_matches(self, source_input, target_input):
        pairs = {}
        for source_column in source_input.get_columns():
            for target_column in target_input.get_columns():
                if source_column.name == target_column.name:
                    pairs[
                        ColumnPair(
                            source_input.name, source_column.name,
                            target_input.name, target_column.name,
                        )
                    ] = 1.0
        return pairs

exact = valentine_match(
    [orders, payments], ExactNameMatcher(), df_names=["orders", "payments"]
)
print(f"{len(exact)} exact-name matches")
for pair, score in exact.items():
    print(pair.source_column, "->", pair.target_column, score)
"""),
    md("""
## What this shows

- Valentine's contract is small: implement `get_matches`, return `ColumnPair` scores.
  Everything else — metrics, one-to-one selection, details — is provided by the library.
- The extension differs from `ExactNameMatcher` only in how it computes the score:
  COMA's name functions plus Jaccard over canonicalised value sets, with the two
  components exposed in `match_details`.
- A single table pair is not enough to judge a matcher; that is why the project evaluates
  on twelve pairs, five corruption levels and per stratum.

## Reproducing

```bash
make data     # the Olist CSVs
make eda      # execute this notebook
```
"""),
])


NOTEBOOKS["tool_kagglehub"] = notebook("tool_kagglehub", [
    md("""
# kagglehub — introductory notebook

M3 requires a minimal notebook per selected tool. This one covers **kagglehub**, the
library the project uses to fetch public Kaggle Datasets without an account or API token.

It shows three things: what a download returns, that repeated downloads hit the cache, and
why the project checks a SHA-256 against the registry instead of trusting the download.
"""),
    code(SETUP),
    md("""
## Download a public dataset

`dataset_download("<owner>/<slug>")` fetches the dataset and returns the local directory.
The handle includes the version, so the same call is reproducible until the publisher
uploads a new version. The dataset here is a 36 KB CSV from the project registry.
"""),
    code("""
import kagglehub

path = kagglehub.dataset_download("fedesoriano/heart-failure-prediction")
print("path:", path)
"""),
    md("""
## Files and cache behaviour

The returned path lives inside kagglehub's cache. Calling the same handle again does not
re-download: it resolves to the same directory, which is what makes repeated notebook runs
cheap and offline runs possible once the cache is warm.
"""),
    code("""
from pathlib import Path

second = kagglehub.dataset_download("fedesoriano/heart-failure-prediction")
print("same directory:", Path(path) == Path(second))
print("cache root   :", kagglehub.cache.get_cache_folder())
print("files        :", sorted(p.name for p in Path(path).iterdir()))
"""),
    md("""
## Verify a checksum

A cache hit proves the bytes did not change locally; it does not prove they are the bytes
the project pinned. `data/datasets.yaml` records a SHA-256 per file, and the project
verifies it before using the data — a silent dataset update changes the evaluation set,
which would make every result incomparable to the last one.
"""),
    code("""
from swsn.registry import load_registry, sha256_file

registry = load_registry("../data/datasets.yaml")
dataset = registry.datasets["heart_failure"]
actual = sha256_file(Path(path) / "heart.csv")
print("registry :", dataset.sha256["heart.csv"])
print("actual   :", actual)
print("match    :", actual == dataset.sha256["heart.csv"])
"""),
    md("""
## Relation to the project's download step

`make data` calls `swsn.download`, which uses kagglehub and then copies and verifies the
files into `data/raw/<dataset>/` so that every loader reads one layout. `make data
OFFLINE=1` skips the network and only verifies what is already on disk. kagglehub's cache
is an implementation detail; the registry and the checksum are the contract.

## Reproducing

```bash
make setup
# execute this notebook (needs network on a cold cache)
make eda
```
"""),
])


NOTEBOOKS["tool_pyyaml"] = notebook("tool_pyyaml", [
    md("""
# PyYAML — introductory notebook

M3 requires a minimal notebook per selected tool. This one covers **PyYAML**, used because
the project treats configuration as data: the dataset registry, the evaluation protocol
and the corruption ladder are YAML files that can be reviewed in a diff instead of being
buried in code.

The notebook loads the registry, validates the ladder, and shows that a bad file fails
loudly instead of silently producing an empty configuration.
"""),
    code(SETUP),
    md("""
## Load the dataset registry

`load_registry` reads `data/datasets.yaml`, parses every dataset and pair, and rejects
duplicate ids. Keeping the checks in the loader means a typo in the YAML is an error at
load time, not a missing row three notebooks later.
"""),
    code("""
from swsn.registry import load_registry

registry = load_registry("../data/datasets.yaml")
print("datasets:", len(registry.datasets), "| pairs:", len(registry.pairs))
print([d.id for d in registry.datasets.values()])
"""),
    code("""
dataset = registry.datasets["heart_failure"]
print("class   :", dataset.cls.value)
print("slug    :", dataset.kaggle_slug)
print("licence :", dataset.licence)
print("files   :", list(dataset.sha256))
"""),
    md("""
## Load and validate the ladder

The ladder is a mapping from level id to a dimension and a list of operators. `load_ladder`
is a thin `yaml.safe_load`; the validation happens when a level is parsed, so an unknown
level or a malformed operator raises instead of returning `None`.
"""),
    code("""
from swsn.corrupt import level_order, load_ladder, parse_level

ladder = load_ladder("../corruption/ladder.yaml")
for level in level_order(ladder):
    operators = [spec.id for spec in parse_level(ladder, level)]
    print(f"{level}: {len(operators):2d} operators  {operators}")
"""),
    md("""
L0 is deliberately empty: the uncorrupted baseline has no operator, and that is visible in
the data rather than implied by a comment.
"""),
    md("""
## Fail loudly on a bad entry

The important behaviour is the failure, not the success. A schema file without `tables`
is rejected by `load_schema` with the path in the message, so a broken config names the
file that broke.
"""),
    code("""
import pathlib
import tempfile

from swsn.schema_doc import load_schema

with tempfile.TemporaryDirectory() as tmp:
    bad = pathlib.Path(tmp) / "bad.yaml"
    bad.write_text("dataset: toy\\n", encoding="utf-8")
    try:
        load_schema(bad)
    except ValueError as exc:
        print(f"{type(exc).__name__}: {exc}")
"""),
    md("""
## Safe loading

`yaml.safe_load` constructs only plain Python types (dict, list, str, int, float, bool,
None). `yaml.load` without a loader can instantiate arbitrary objects, which is why the
project never uses it on files that come from outside the repository.
"""),
    code("""
import yaml

sample = \"\"\"\\
version: "1"
threshold: 0.15
levels: [L0, L1]
\"\"\"
values = yaml.safe_load(sample)
print(values)
print({key: type(value).__name__ for key, value in values.items()})
"""),
    md("""
Note `version: "1"` stays a string: the registry quotes versions on purpose, because
`version: 1.0` would load as a float and compare unequal to the string "1".

## Reproducing

```bash
make eda
```
"""),
])


def write_all() -> None:
    for name, nb in NOTEBOOKS.items():
        path = HERE / f"{name}.ipynb"
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("[nb  ]", path)


if __name__ == "__main__":
    write_all()

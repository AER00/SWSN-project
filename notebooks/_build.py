"""Build the seven EDA notebooks.

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


def write_all() -> None:
    for name, nb in NOTEBOOKS.items():
        path = HERE / f"{name}.ipynb"
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("[nb  ]", path)


if __name__ == "__main__":
    write_all()

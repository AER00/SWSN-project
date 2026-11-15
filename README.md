# Valentine on messy Kaggle tables

Analysis of Valentine's schema-matching suite on messy, real-world Kaggle tables, and a
normalisation-aware extension of the hybrid COMA matcher.

Course project, SWSN 2026/27. Milestone 1 fixed the topic, method and literature; this
repository is the code base for Milestone 2 onward.

## Status

| Milestone | Due | State |
|---|---|---|
| M2 — datasets, EDA, repo, report | 09.11.2026 | datasets triaged, ground truth transcribed, 600-run ladder benchmark, report drafted |
| M3 — tools, preprocessing, Kanban | 16.11.2026 | not started (`extension/` scaffolded only) |
| M4 — first results, novelty | 30.11.2026 | not started |
| M5 — second results, draft report | 14.12.2026 | not started |
| M6 — final report, defence | 11–18.01.2027 | not started |

### Headline result

Recovery@1 on twelve documented table pairs, cumulative corruption ladder:

| | L0 | L1 header | L2 +values | L3 +noise | L4 +semantic |
|---|---|---|---|---|---|
| COMA | 0.958 | 0.542 | 0.486 | 0.486 | 0.403 |
| SimilarityFlooding | 0.958 | 0.833 | 0.750 | 0.722 | 0.722 |
| Jaccard | 0.875 | 0.708 | 0.403 | 0.403 | 0.403 |
| Cupid | 0.847 | 0.292 | 0.208 | 0.292 | 0.292 |
| DistributionBased | 0.648 | 0.537 | 0.292 | 0.283 | 0.250 |

For name-based matchers (COMA, Cupid) header noise is most of the loss (COMA 0.958→0.542, Cupid 0.847→0.292), while value-based
matchers (Jaccard, DistributionBased) lose most at the value levels. The one genuinely cross-lingual correspondence (Olist's
Portuguese→English category name) is not recovered at k=1 by any matcher (single pair; see docs/findings.md). The full write-up is `reports/milestone2-eda.pdf`.

## Quickstart

```bash
make setup               # uv sync + the NLTK corpora Valentine downloads on first use
make data                # download the Kaggle datasets (public, anonymous access)
make triage              # apply the G1-G5 admission gate -> evaluation/triage.json
make bench               # 5 matchers x 5 levels x 12 pairs with ground truth (18 declared) -> evaluation/results_*.csv
make figures             # reports/figures/*.pdf + *.svg
make test                # test suite
make eda                 # execute the notebooks
make all                 # setup + data + test + eda
```

Each target is a thin wrapper over a module (`python -m swsn.<name>`), so anything can be
run and inspected on its own. `make bench` takes about four minutes.

`make setup` also fetches ~52 MB of NLTK data (`punkt_tab`, `omw-1.4`, `stopwords`,
`wordnet`) into `~/nltk_data`. Without it the first `Coma` call downloads them itself —
taking ~26 s instead of ~0.15 s — and an offline machine cannot run the hybrid matchers at
all. See `docs/findings.md`.

Requires [`uv`](https://docs.astral.sh/uv/). Python 3.13 is installed automatically by
`uv` — do **not** use the system Python 3.14, Valentine needs `>=3.12,<3.16` and Python
3.15 lacks PuLP wheels on macOS.

No Kaggle account or API token is needed: every source is a public Kaggle *Dataset*,
which downloads anonymously through `kagglehub`. If downloads are blocked, the README in
`data/` explains how to place the CSVs manually (`make data OFFLINE=1`).

## Repository layout

```
data/            dataset registry (datasets.yaml), download script, raw data (gitignored)
src/swsn/        profiling, audit, corruption, probe and diagnostic modules
src/swsn/extension/  the M3/M4 deliverable: canonicalisation + NormalisedComa matcher
corruption/      declared corruption operators per ladder level
evaluation/      provisional evaluation protocol and baseline definitions
ground_truth/    transcribed schemas, labelled pairs, annotation guide, agreement tooling
notebooks/       the seven EDA notebooks (00–06)
reports/         the 2-page EDA report and exported figures
docs/            tool inventory and extended bibliography
tests/           smoke tests
```

## Data and licences

Raw CSVs are **not** committed. `data/datasets.yaml` records each dataset's slug,
version, SHA-256 and licence; `data/README.md` carries the attribution text. Datasets are
attributed to their Kaggle publishers and are used under their respective licences
(several are non-commercial).

## Notebooks

| Notebook | Purpose |
|---|---|
| `00_dataset_triage` | candidate → admitted/dropped, with the reason per table |
| `01_inventory` | tables, schemas, types, sizes |
| `02_dirtiness` | D1–D7 dirtiness profile across the collection |
| `03_documentation_audit` | D9: does the published schema hold in the files? |
| `04_cross_table` | D8 name-similarity × value-overlap quadrants |
| `05_probe_recovery` | how well Valentine recovers documented relationships |
| `06_corruption_ladder` | how the matching signal degrades from L0 to L4 |

## Method in one paragraph

Documented multi-table datasets supply ground truth that annotation cannot: the publisher
states which columns correspond. Those correspondences are stratified (S1 same-name keys,
S2 renamed, S3 format/unit, S4 traps) because the trivial stratum would otherwise dominate
any aggregate score. The same datasets are then degraded along a declared corruption ladder
(L0–L4) — one dimension per level — with ground truth preserved through recorded rename
maps. This gives an evaluation where every result has a known cause, and a specification for
the normalisation-aware matcher the project proposes.

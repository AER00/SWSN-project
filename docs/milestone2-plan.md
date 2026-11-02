# Milestone 2 — plan (v4)
**Window:** 02.11.2026 (Mon) → 09.11.2026 (Mon) · **Submit Sun 08.11** (one day of buffer)
**Deliverables:** chosen datasets · EDA notebooks/code · public repository · EDA report (≤2 pages, PDF)
**Target: 8/8** — on time (2) + repo (1) + datasets fit but not from the main papers (2) + variety (1) + specific EDA (2)

> **v2 change:** added a class of multi-file Kaggle datasets whose published schema documentation is used as an authoritative ground truth, plus a Valentine feasibility probe against it.
> **v3 change:** added a corruption ladder — controlled degradation of those datasets with ground truth preserved by construction. Fixes the trivial-S1 problem and gives every result a causal attribution. Built in M2, evaluated in M4.
> **v4 change:** restructured for forward compatibility — M2 now hands M3–M6 concrete artefacts (frozen protocol, extension scaffold, tool inventory, baseline choice, vector figures) so later milestones are assembly rather than rework. See §9.4–9.6.

---

## 0. What M2 has to prove

1. **The population is real and different** — Kaggle tables, not Valentine's benchmark (TPC-DI / Open Data / ChEMBL / WikiData / Magellan). → +2
2. **It is varied** — several unrelated domains and two different matching regimes. → +1
3. **It is messy in the ways M1 claims, and that messiness is measurable** — quantified per column, with a quantified effect on matcher behaviour. → +2

Plus a repository a stranger can run (1) and an on-time submission (2).

---

## 1. Datasets

### 1.1 Admission gate (all must pass)

| # | Criterion | Threshold |
|---|---|---|
| G1 | Provenance | public Kaggle *Dataset* upload (anonymous download works); slug, version, licence recorded |
| G2 | Not in Valentine's benchmark | not TPC-DI / Open Data / ChEMBL / WikiData / Magellan; avoid Magellan-derived tables (Abt-Buy, Walmart-Amazon, DBLP-ACM, iTunes-Amazon, Beer) |
| G3 | Pairing | either a documented relationship (C-doc) or ≥3 hand-identified correspondences (C-nat) |
| G4 | Messiness | ≥3 of D1–D7 without synthetic corruption |
| G5 | Tractability | ≤120 columns; rows sampled to ≤5k for matcher runs; downloads in <60 s |

**Kaggle Datasets vs Competitions:** public *Datasets* download anonymously via kagglehub. *Competition* data requires accepting the rules and an API token — pick Dataset mirrors where they exist, and treat competition-only sources as opt-in with a documented credential step.

### 1.2 Three dataset classes (this is the structural change)

| Class | What it is | Ground truth | What it measures |
|---|---|---|---|
| **C-doc** — documented multi-file | one Kaggle dataset shipped as many related CSVs with a published schema / ERD / data dictionary | **derived from the documentation**, then verified | a *controlled* regime with exact GT: how well Valentine recovers relationships that are known to exist |
| **C-nat** — natural pairs | two independently uploaded single tables in the same domain | hand-annotated, double, adjudicated | the *messy real-world* regime the project is actually about |
| **C-syn** — corrupted copies (L0–L4) | a C-doc dataset with declared, seeded corruption applied to one table | inherited from C-doc, remapped through the rename map | *which* dimension of dirt breaks *which* matcher signal — the attribution axis |

C-doc does the heavy lifting for the rubric's "datasets fit the problem": it lets you state, with numbers, that these tables genuinely contain the relationships a matcher should find. C-nat keeps the headline messiness claim honest — no documentation exists there, which is the point. C-syn (§1.6) supplies the controlled axis both of them lack. Three classes, three different jobs; none of them is redundant.

### 1.3 C-doc candidates (3 recommended)

| Dataset | Files | Documented relationships | Why it is useful |
|---|---|---|---|
| **Olist Brazilian E-Commerce** (`olistbr/brazilian-ecommerce`) | 9 CSVs | published data-schema section: customers→orders→items→payments/reviews, items→products/sellers, zip-prefix joins to geolocation, PT↔EN category translation | full ERD, mixed PK/FK, renamed and cross-language columns, a genuinely messy geolocation table, one many-to-one translation table |
| **Instacart Market Basket** (Dataset mirror, e.g. `psparks/instacart-market-basket-analysis`) | 6 CSVs | documented hierarchy orders→order_products→products→aisles/departments | small, fast, clean hierarchy — good for a first probe and for isolating matcher behaviour from data noise |
| **MovieLens** (`grouplens/movielens-25m-dataset`) | 6 CSVs | documented; `links.csv` maps movieId→imdbId/tmdbId | small; `links.csv` is an **authoritative cross-dataset mapping**, enabling a controlled cross-dataset discovery scenario |
| *optional 4th* | **Home Credit Default Risk** (competition `home-credit-default-risk`) | 8 CSVs + **`HomeCredit_columns_description.csv`** — a machine-readable column dictionary inside the data | the richest case (122-column application table, 3-level join path), but competition rules + 27M-row tables; add only if time allows |

### 1.4 C-nat candidates (3–4 domains)

| Domain | Candidate tables (verify slugs + licences during triage) |
|---|---|
| Used cars | Craigslist cars (`austinreese/craigslist-carstrucks-data`), CarDekho (`nehalbirla/vehicle-dataset-from-cardekho`), USA cars (`doaaalsenani/usa-cars-dataset`) |
| Housing / rentals | NYC Airbnb (`dgomonov/new-york-city-airbnb-open-data`), Melbourne housing (`anthonypino/melbourne-housing-market`), King County (`harlfoxem/housesalesprediction`) |
| Jobs / salaries | LinkedIn job postings (`arshkon/linkedin-job-postings`), DS job salaries (`ruchi798/data-science-job-salaries`) |
| Health | Heart failure (`fedesoriano/heart-failure-prediction`), Diabetes (`iammustafatz/diabetes-prediction-dataset`), Insurance (`mirichoi0218/insurance`) |

Slugs rot. Triage on 03.11 decides; each candidate is downloaded, inspected, and either frozen into `data/datasets.yaml` or dropped with a reason recorded.

### 1.5 Ground truth from documentation — the design that makes it defensible

**The trap:** in a documented relational schema, almost every relationship is a foreign key with an **identical column name** (`order_id` ↔ `order_id`, `SK_ID_CURR` ↔ `SK_ID_CURR`). Valentine will find those at ~1.0, so an aggregate F1 says nothing and flatters the matcher. Documentation also never lists the *non*-relationships, which are where false positives live.

**Fix — stratify the ground truth and report per stratum, never only in aggregate:**

| Stratum | Definition | Olist example | Expectation |
|---|---|---|---|
| **S1 same-name keys** | documented FK, near-identical name | `orders.order_id` ↔ `order_payments.order_id` | trivially recovered; sanity check and upper bound |
| **S2 renamed / cross-lingual** | same concept, materially different name | `products.product_category_name` (PT) ↔ `product_category_name_translation.product_category_name_english` | the semantic-matcher frontier |
| **S3 format / unit / grain** | same concept, different encoding or aggregation | `customer_zip_code_prefix` (int) ↔ `geolocation_zip_code_prefix`; `order_items.price` vs `order_payments.payment_value` | the normalisation layer's target |
| **S4 traps** | similar name or type, *different* meaning | the several `*_timestamp` columns in `orders`; `NAME_CONTRACT_TYPE` vs `NAME_CONTRACT_STATUS`; `customer_id` vs `customer_unique_id` in the same table | false-positive source; must be modelled as negatives |

**Protocol:**
1. **Extract** the documented skeleton automatically where possible (Home Credit's `columns_description.csv` is machine-readable; otherwise a hand-transcribed `schema.yaml` per dataset with each table's columns, PK, FKs, and a source citation).
2. **Audit** the documentation against the files (see D9 in §3.1): missing columns, renamed columns, broken referential integrity, wrong cardinalities. Documentation that fails the audit is corrected and the correction logged — never silently trusted.
3. **Assign strata** by two people, independently; disagreements adjudicated. Recorded in `ground_truth/gt_<dataset>.csv`: `table_a, col_a, table_b, col_b, label, stratum, verified, note`.
4. **Negative space is explicit:** within each table pair, every candidate pair not labelled positive is negative unless marked `unknown`/`skip` (e.g. two ID columns with no documented relation — decide and justify one way). `unknown` is excluded from scoring and its count is reported.
5. **Cross-check** against a small sample of hand annotation on the same pairs — the point is to show the documented GT agrees with human judgement where both exist.

This cuts annotation effort by roughly half versus annotating every pair from scratch, and gives a defensible, citable source for every positive.

### 1.6 Corruption ladder — controlled degradation, ground truth preserved

Take a C-doc dataset, keep the documented correspondence set, and degrade **a copy of one table** along a ladder of declared operators. Ground truth survives by construction: header renames are recorded in a mapping and *composed* into the GT; value reformatting does not change which columns correspond.

**What this buys:**
- **It kills the S1 freebie.** Rename `order_id` → `pedido_id` / `Order Ref` / `customer_order_identifier` and a name-identical key match stops being trivial — now the hybrid matcher has to recover it from instance values. That is a genuine test of Coma's instance component instead of a formality.
- **Causal attribution.** One dimension per level means you can say *which* kind of dirt breaks *which* matcher signal, not merely that dirty data is harder.
- **A falsifiable prediction for the extension.** Normalisation-aware matching should recover L2 and most of L3, and should do nothing at L4. If it recovers L4 too, either the operators leak or the matcher is doing semantics — both are findings.
- **Exact GT, near-zero annotation cost.** Every correspondence is known before corruption.

**Levels — cumulative, one dimension added per level:**

| Level | Adds | Recoverable by normalisation? |
|---|---|---|
| **L0** | none — original | — |
| **L1 header** | rename (abbreviation, translation, units appended, case, noise prefix/suffix, `Unnamed: n`), reorder, duplicate names, spurious columns | no — normalisation cannot invent a name; this is semantic-matcher territory |
| **L2 value format** | dates (ISO → slash / text / epoch), numbers (thousand separators, decimal comma, currency prefix, `%`, zero-padding, `12345` → `12345.0`), IDs (`ORD-12345`, case changes) | **yes — the extension's target** |
| **L3 noise** | sentinel nulls (`N/A`, `-`, `unknown`, `?`, 999), mixed types within a column, whitespace padding, unicode dashes/quotes, units embedded in values | mostly yes — needs null and unit handling |
| **L4 semantic** | synonym dictionary, abbreviation, language translation of values (`São Paulo` → `SP`), category recoding | no — deliberately outside the extension's scope; the negative control |

**Operators are declared, seeded and audited.** Each is `(name, dimension, target, preserves_match, params, seed)`:
- value-*format* operators preserve the value domain → GT valid
- value-*substitution* operators (random remapping, independent masking) destroy it → permitted only when applied **identically to both sides through one mapping**, otherwise rejected
- header renames write `renames.yaml`, composed into GT automatically

**One-sided by default.** Corrupt table A, leave B clean. That is the realistic asymmetry (one published table is a scraped mess, the other is curated) and keeps GT trivially valid. A two-sided variant with shared mappings is optional.

**Build-time integrity check.** After generation, canonicalise and recompute `value_sim` for every GT positive. If a `preserves_match: true` pair collapses below threshold, the generator has a bug and the build fails. Report destroyed pairs per level — it must be zero.

**Variants:** the cumulative ladder L0–L4, plus a one-dimension-at-a-time ablation on two pairs so joint effects can be separated from single-dimension effects.

**The honest caveat:** real messiness is *correlated* — a table's dates are all messy because one export pipeline mangled them — while the ladder is iid by construction. That is the price of attribution, and it is exactly why C-nat stays in the plan as the external-validity check.

**Where it lands:** built in M2 (needed for the D8 sensitivity analysis), used as the target specification for the normalisation layer in M3, and as the evaluation axis in M4. It is *not* evaluated as a benchmark in M2.

**One taxonomy, four uses.** The operator dimensions, the canonicalisation modules in `extension/`, and the ablation rows in M4 are deliberately the *same* set — every ladder dimension has exactly one repair component. That is what makes the M4 ablation valid: each switch turns off one repair, and the corresponding level shows what it was worth. Build the taxonomy once in M2 and it carries the preprocessing notebook, the method description and the results table.

---

## 2. Repository

Public GitHub repo, e.g. `swsn-valentine-messy-tables`. Raw data is **not** committed (licences vary — Olist is non-commercial/attribution, MovieLens is research-licence, competition data has its own rules); download is scripted and checksummed.

```
README.md                  # 5-command quickstart, dataset table, licences
pyproject.toml + uv.lock   # Python 3.13 (valentine >=3.12,<3.16; 3.15 on macOS lacks PuLP wheels)
Makefile                   # setup · data · eda · probe · report · test · all
data/
  datasets.yaml            # slug, version, sha256, licence, n_files, n_rows, fetched_at
  README.md                # provenance, licence, attribution per dataset
  raw/ processed/          # gitignored
src/swsn/
  download.py              # kagglehub wrapper, checksum verify, --offline manual path
  registry.py              # dataset / table-pair / stratum metadata models
  schema_doc.py            # parse documented schemas -> candidate GT skeleton
  audit.py                 # D9 documentation-vs-data audit
  profile.py               # D1–D7 dirtiness metrics
  pairdiag.py              # D8 name-similarity × value-overlap diagnostics
  corrupt.py               # declared ladder operators, seeded, with preserve contract + integrity check
  probe.py                 # Valentine runs over C-doc sets -> per-stratum metrics
  normalize.py             # preview stub — superseded by extension/canonicalise.py in M3
extension/                 # M3/M4 deliverable — interface frozen in M2, implemented in M3
  config.py                # canonicalisation switches, one per ladder dimension D2/D3/D4
  canonicalise.py          # dates, numbers, units, sentinels -> canonical values      [M3]
  values.py                # canonical value sets per column                           [M3]
  matcher.py               # NormalisedComa(BaseMatcher): get_matches + match_details   [M3/M4]
evaluation/
  protocol.yaml            # frozen design: matchers, sets, levels, metrics, thresholds, seeds
  baselines.md             # COMA (VLDB 2002) method baseline; Starmie as alternative approach
docs/
  tools.md                 # tool inventory + justification (M3 seed)
  literature.md            # extended bibliography incl. new components (M5 seed)
corruption/
  ladder.yaml              # level -> operator list, targets, seeds
  renames/<dataset>/<level>.yaml   # header rename maps, composed into GT
notebooks/
  00_dataset_triage.ipynb
  01_inventory.ipynb
  02_dirtiness.ipynb
  03_documentation_audit.ipynb
  04_cross_table.ipynb
  05_probe_recovery.ipynb
  06_corruption_ladder.ipynb
ground_truth/
  annotation_guide.md      # strata definitions + adjudication rules
  schema/<dataset>.yaml    # transcribed documented schema, with citations
  gt/*.csv                 # labelled pairs by stratum, per corruption level
  agreement.py             # κ for C-nat, adjudication log for C-doc strata
reports/                   # milestone2-eda.pdf + figures/
tests/                     # smoke tests for profilers, audit, metric wrappers
```

**Reproducibility checklist (the 1 point):** clean clone → `make all` works; dataset versions + sha256 pinned; row sampling seeded; `--offline` documented; `make test` green; README states exact Python version and the PuLP/wheel gotcha.

---

## 3. Exploratory analysis

### 3.1 Dirtiness taxonomy (per column, aggregated per table)

| Dim | Measures | How |
|---|---|---|
| **D1 header noise** | autogenerated names (`Unnamed: 0`), duplicates, units in header, non-ASCII, abbreviations, mixed naming styles | regex + normalised-name collisions |
| **D2 type instability** | inferred dtype ≠ best parse dtype; coercion rate; mixed-type columns | per-column coercion attempt |
| **D3 missingness & sentinels** | NaN share; `N/A`, `-`, `unknown`, `?`; 0/−1/999 as null | sentinel frequency match |
| **D4 format heterogeneity** | several number formats (separators, decimal comma, currency, %, ranges) or date formats in one column | distinct regex shapes / strptime patterns |
| **D5 categorical noise** | case / whitespace / punctuation / spelling variants of one entity | fuzzy clustering → clusters per column |
| **D6 cardinality & texture** | unique ratio, constant columns, ID-like columns, free text | unique ratio + mean token length |
| **D7 distribution shape** | skew, zero-inflation, outliers — what `DistributionBased` sees | moments + IQR |
| **D9 documentation fidelity** | documented columns missing in data; undocumented columns present; documented type ≠ observed; referential integrity of every documented FK; documented row counts vs actual | doc-vs-data diff |

D9 is the dimension the documented datasets make possible, and it is a real finding either way: if the docs hold, the GT is trustworthy; where they don't, the gap is a measured messiness result (stale documentation is itself a form of dirtiness).

### 3.2 D8 — cross-table signal

Per column pair across all pairs: `name_sim` (token Jaccard on canonicalised names) and `value_sim` (Jaccard over normalised value sets, sample ≤1000 distinct values, trim+lowercase only). Plot with GT as colour, in quadrants:

| | high `value_sim` | low `value_sim` |
|---|---|---|
| **high `name_sim`** | easy matches | **traps** (S4) — false positives |
| **low `name_sim`** | **S2/S3** — normalisation's target | true non-matches |

Report counts and true-match share per quadrant, split by stratum. This predicts *which* matchers fail and *how*, and pre-registers the failure modes M4 tests.

### 3.3 Documentation audit (notebook 03)

Per dataset: column coverage (documented ∩ observed / documented), type agreement, FK referential-integrity pass rate, duplicate-key violations, row-count drift. Output: a table plus a figure — *documented relationships that the data does not actually satisfy*. For Olist expect geolocation duplicates and missing `customer_zip_code_prefix` values; for Home Credit expect undocumented columns.

### 3.4 Normalisation preview (notebook 04, with D8 — secondary)

Apply a ~30-line canonicaliser (casefold, strip punctuation, unify dates, strip currency/units, fix separators, map sentinels to NaN) and recompute `value_sim`; plot Δ by stratum. Reports headroom only — the real layer is M3.

### 3.5 Valentine feasibility probe (notebook 05) — the user-facing question

**Question:** given relationships documented to exist, how well does Valentine actually find them?

Design, deliberately capped so it stays EDA and does not become M4:

- **Scope:** Olist + Instacart in the first pass; MovieLens and Home Credit only if Friday is clear.
- **Matchers:** all five built-ins — `Coma`, `Cupid`, `DistributionBased`, `JaccardDistanceMatcher`, `SimilarityFlooding`. Cheap at sampled row counts.
- **Runs:** `valentine_match([df...], matcher, df_names=[...])` per C-doc dataset → all unordered table pairs; `Coma`, `SimilarityFlooding` and `DistributionBased` get the batch view.
- **Metrics:** per table pair — Precision / Recall / F1, plus `PrecisionTop10Percent` and `MRR` since several matchers emit scores; report the Hungarian one-to-one variant where it changes the answer.
- **Headline metric — documented-relationship recovery@k:** of the K documented correspondences, how many appear in Valentine's top-1 / top-3 per source column. Directly answers "does it find the relationships".
- **Breakdown by stratum S1–S4.** This is the figure that matters: expect ≈1.0 on S1 and degradation on S2/S3, with S4 driving false positives. Aggregate F1 is reported but never as the sole result — it is dominated by S1 and would be misleading.
- **Runtime table** (seconds per pair) — feeds M3/M4 planning.
- **Explicit non-goals:** no tuning, no preprocessing, no new matcher, no ablation. Those are M3/M4. The probe answers only "is this GT source usable, and does it separate matchers meaningfully".

### 3.6 Corruption-ladder sensitivity (notebook 06) — EDA, not results

Recompute `name_sim` and `value_sim` for every column pair at L0–L4 and plot each pair's **trajectory through the D8 plane**. Expected:

- GT positives slide from Q1 → Q2 as header corruption (L1) removes the name signal
- they slide Q1 → Q3 as value reformatting (L2) removes the lexical value signal
- S4 traps drift toward the false-positive corner as levels rise
- L4 pushes everything into the semantic quadrant, where neither signal works

Report the migration matrix (pair counts per quadrant per level), split by stratum. This is the EDA's strongest output and it needs **no matcher run**: it shows which fraction of true matches become invisible to name-only and value-only signals at each level — that is the headroom the extension has to recover. One confirmatory Coma run at L0 vs L2 supplies the direction of the effect; the full ladder evaluation is M4.

Also report the correlation caveat: measured C-nat dirtiness is clustered, ladder dirtiness is iid, so the ladder understates real difficulty.

### 3.7 Figures for the report (1 table + 4 figures)

| Fig | Content |
|---|---|
| T1 | Dataset table: class, domain, files, rows × cols, licence, GT source |
| F1 | Dirtiness heatmap: tables × D1–D7 (+D9 panel), z-scored, annotated |
| F2 | D8 quadrant scatter coloured by stratum |
| F3 | **Recovery by stratum, per matcher** — the money figure |
| F4 | D8 trajectories across L0–L4, or the migration matrix |

D9 goes into the report text or a small table if it fits; the normalisation preview stays in the notebook.

---

## 4. EDA report (≤2 pages, PDF)

```
1  Motivation and question          (different setting from Valentine's benchmark)
2  Datasets                         (T1; C-doc vs C-nat vs ladder, why all three)
3  What "messy" means here          (D1–D7 + D9 audit, F1; 1–2 findings)
4  Cross-table signal               (D8 + F2)
5  Can Valentine see documented relationships?  (F3 + stratified numbers)
6  What controlled degradation shows (F4 — the causal story)
7  Implications and threats         (3 bullets → M3/M4; validity limits)
```

Every claim carries a number and a figure reference. Seven sections, two pages — if it overflows, cut §4 prose, never §5 or §6.

---

## 5. Schedule (02.11 → 09.11, four people)

| Date | Work | Owner |
|---|---|---|
| **Mon 02.11** | env bootstrap (`uv` + Python 3.13; Valentine install smoke test; kagglehub anonymous download check on Olist + Instacart); repo skeleton; **Kanban board created from §5**; candidate longlist; strata definitions drafted | A + all |
| **Tue 03.11** | triage: download and score every candidate against G1–G5; freeze the dataset list; `datasets.yaml` with versions + sha256 | B |
| **Wed 04.11** | transcribe documented schemas → `schema/*.yaml`; build GT skeleton; D9 audit module; `corrupt.py` operator set + `ladder.yaml`; notebook 01 + 03 | B, C |
| **Thu 05.11** | strata assignment + adjudication for C-doc; D1–D7 profiler; generate L0–L4 + integrity check; notebook 02 + 05 start | B, C, D |
| **Fri 06.11** | D8 diagnostics (04); **probe run** Olist + Instacart × 5 matchers at L0 and L2 (05); ladder sensitivity (06) | D, C |
| **Sat 07.11** | C-nat annotation round + κ; figures exported as vector PDF/SVG; report draft; **freeze `evaluation/protocol.yaml`, scaffold `extension/`, write `docs/tools.md` + `docs/literature.md`**; clean-room `make all` | A, B, D |
| **Sun 08.11** | report PDF; Kanban updated; repo tagged; **submit** | A |
| Mon 09.11 | buffer only | — |

Tracks: **A** repo/infrastructure · **B** dataset curation + ground truth · **C** profiling, audit, corruption operators · **D** diagnostics, probe, figures.
**Priority order if the week slips:** Olist probe > ladder sensitivity > documentation audit > C-nat annotation > MovieLens/Home Credit > normalisation preview.

---

## 6. Scope guard

- The probe is **one fixed configuration**, reported per stratum. No tuning, no threshold search, no preprocessing variants — that is M4's job and doing it now destroys the M4 story.
- The ladder is **built and characterised** in M2 (D8 trajectories, one confirmatory L0/L2 run). Evaluating the extension across L0–L4 is M4. Do not run the full ladder benchmark now.
- No production normalisation layer (M3).
- No final-report prose — 2 pages.
- If the probe shows Valentine performs badly on S2/S3, that is a **result**, not a failure: report it, it is the premise of the extension.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Documented names identical → trivial S1 dominates and flatters results | mandatory per-stratum reporting; aggregate F1 never reported alone; L1 renaming removes the freebie |
| Ladder judged artificial ("real data isn't iid-corrupted") | C-nat stays as the external-validity check; every operator is declared; measured dirtiness distribution from C-nat is reported alongside so the reader can judge realism |
| Corruption silently breaks a GT pair | `preserves_match` contract + build-time integrity check that fails the build; destroyed-pair count reported per level |
| Documentation stale or wrong | D9 audit before GT is used; corrections logged with citations |
| Kaggle slug dead / licence restrictive / competition rules | G1 gate; prefer Dataset mirrors; fallback slug per class; manual-download path |
| Valentine won't install (Python 3.14, PuLP) | `uv python install 3.13` on day 1 |
| Probe runtime explodes (Olist geolocation is ~1M rows) | sample rows to ≤5k, seeded; runtime table reported |
| Probe drifts into M4 | frozen matcher list, frozen metric set, one figure, non-goals written down |
| C-nat annotation overruns | it is now the *second* priority; cap at 3 domains |
| Report becomes a matcher benchmark | F3 is one figure; sections 3–4 (dirtiness, documentation) carry the EDA weight |

---

## 8. Decisions to confirm

1. **C-doc scope:** Olist + Instacart (recommended minimum) vs + MovieLens (+ half a day) vs + Home Credit (+1 day, competition credentials).
2. **C-nat scope:** 3 domains (recommended, ~6 pairs) vs 4 — smaller now that the ladder carries the attribution argument.
3. **Ladder depth:** L0–L4 cumulative with L4 as the negative control (recommended) vs L0–L3 only (faster, but loses the "normalisation has a ceiling" claim).
4. **Corruption sidedness:** one-sided (recommended — realistic asymmetry, GT trivially valid) vs two-sided with shared mappings (harder, closer to "both tables are messy").
5. **Probe in M2** vs deferred to M4 — recommended in M2: it validates the GT source and de-risks M3/M4, at the cost of ~1 day.
6. **Extension architecture:** `NormalisedComa(BaseMatcher)` subclass with per-signal `match_details` (**recommended** — gives M4 a method to execute and defends the type-3 claim) vs a preprocessing wrapper around the stock `Coma`. Freeze the interface in M2, implement in M3.
7. **Baseline for M4:** COMA (VLDB 2002) as the method lineage + Valentine's published `Coma` as the system baseline; Starmie (PVLDB 2023) as the alternative-approach reference. Recorded in `evaluation/baselines.md`.
8. **Repo host:** public GitHub.

---

## 9. Fit check against all six milestones

### 9.1 Coverage

| Milestone | Rubric item | Covered by | Status |
|---|---|---|---|
| **M1** | topic · type 3 · literature | already submitted (9.75/10) | ✅ but see 9.2.1 |
| **M2** | on time / repo / datasets differ / variety / specific EDA | C-doc + C-nat + C-syn; D1–D9; D8 quadrants; ladder trajectories; probe | ✅ strong, time-tight |
| **M3** | tools fit datasets · tools fit methods · preprocessing 3 pt · project management 3 pt | ladder defines the L2/L3 repairs → preprocessing notebooks; `docs/tools.md`; Kanban seeded 02.11 | ✅ closed by §9.4 |
| **M4** | problem prep · method execution · evaluation · pros vs baseline paper | named baseline, frozen protocol, `extension/` scaffold, ladder evaluation | ✅ closed by §9.4–9.5 |
| **M5** | 7 report sections · references · pipeline figures | section map fixed in M2; `docs/literature.md`; vector figures | ✅ closed by §9.4 |
| **M6** | report 20 pt (datasets /2, method /2, eval strategy /2) · repo 20 pt | three dataset classes, matcher-level extension, stratified + ladder evaluation, seeded reproducibility | ✅ |

Nothing in the plan is wasted at any milestone: the ladder built in M2 is the M3 preprocessing specification and the M4 evaluation axis.

### 9.2 Five adjustments

**1. Reconcile "ground truth is absent" with constructed ground truth.**
The submitted M1 description says the target population has *no* ground truth. The plan now constructs it three ways. That is a refinement, not a contradiction — but it must be said out loud, in M2 report §2 and again in M6:
> Ground truth does not exist in the target population (independently published messy Kaggle tables). We therefore evaluate on documented multi-table datasets where the relationships are known, on controlled degradations of those datasets, and on independent uploads as an external-validity check.

Do **not** leave the M1 sentence and the M2 method looking like they disagree.

**2. Frame the extension as a method, not as preprocessing.** This is the biggest risk in the whole project.
M3 grades *preprocessing* (3 pt); M4 and M6 grade *method*. The same artefact gets presented twice, and if it is only a data-cleaning step, M4's "method execution" is thin and the M1 type-3 claim ("a new method") becomes hard to defend against a type-2 downgrade. Therefore:
- implement it as a matcher-level component — e.g. a `BaseMatcher` subclass that computes normalisation-aware instance similarity (canonicalised value sets, sentinel-aware nulls, unit/format unification) with sub-scores exposed via `match_details`;
- in M3 the same code appears as the *preprocessing pipeline* that produces canonicalised tables;
- in M4/M6 it appears as the *method* and is ablated per dimension.
If the extension is a standalone matcher, the comparison against `Coma` is direct and the novelty is visible. Decided in M2 — §8 decision 6, frozen in §9.5.

**3. Add literature for the new components.** M5 asks for a valid references list; M6 grades references /2. The corruption ladder and the dirtiness taxonomy are new to the project and are currently uncited. Add ~3:
- a data-quality / cleaning taxonomy paper (frames D1–D9);
- a robustness/corruption-benchmark precedent (frames the ladder as a method, not an invention);
- optionally a schema-matching robustness or evaluation study.
Slot: literature list extended during M2, written into related work in M5.

**4. Seed the Kanban in M2, not M3.** Project management is 3 of M3's 10 points and requires tasks, due dates and fair distribution. §5 of this plan already *is* that table — put it into GitHub Projects / Trello on 02.11 and keep it updated, rather than reconstructing it the week of 16.11.

**5. Defend the C-doc setting explicitly.** A grader may object that Olist/Instacart tables are one database, not independent datasets. Answer in M2 report §2 in one sentence: column matching between tables of one schema is exactly Valentine's task (joinable-column / dataset discovery), and it still contains renamed, translated and differently-formatted columns; C-nat supplies the independent-upload setting, C-syn the controlled one. Without that sentence the datasets point is arguable; with it, it is not.

### 9.3 Time budget

M2 is now the heaviest milestone in the plan: three dataset classes, a documentation audit, D8 diagnostics, a corruption generator and a probe — in six working days. That is feasible with four people **only** because the ladder removes roughly a day of hand annotation and because C-nat is now second priority. Keep the priority order in §5. If the week slips, the ladder and the Olist probe survive and C-nat shrinks to three domains; if it slips badly, C-nat drops to one domain and the report leans on doc + ladder, which still satisfies "datasets differ from the main papers" and "variety".

M3 (7 days after) is not compressed by this: the ladder *is* its preprocessing content, so M3 gets easier, not harder.

### 9.4 Handover — what M2 leaves for the next four milestones

| Artefact | Produced | Consumed by |
|---|---|---|
| `data/datasets.yaml` + dataset cards | triage, 03.11 | M3 "tools appropriate for the datasets" (1 pt); M5/M6 dataset description (/2) |
| `corruption/ladder.yaml` + operator set | 04–05.11 | M3 preprocessing notebooks (3 pt); M4 evaluation axis |
| `evaluation/protocol.yaml` — frozen matchers, sets, levels, metrics, thresholds, seeds | 07.11 | M4 (the whole design), M6 evaluation strategy (/2) |
| `ground_truth/` — transcribed schemas, strata, GT CSVs, κ log | 04–07.11 | M4 metrics; M6 |
| `docs/tools.md` — tool inventory with justification | 07.11 | M3 tool selection (2 pt) — becomes the submission field almost verbatim |
| `docs/literature.md` — extended bibliography | 07.11 | M5 references (1 pt); M6 references (/2) |
| Figures as vector PDF/SVG | 07.11 | M4 deck; M5 report figures (1 pt); M6 figures (/3) |
| Kanban board seeded from §5 | 02.11 | M3, M4, M5 project management (3 pt each) |
| `extension/` scaffold with frozen interface | 07.11 | M3 implementation; M4 method execution (1 pt) |
| The 2-page EDA report | 08.11 | M5 report dataset + evaluation sections; M6 |

Everything here is produced as a side effect of doing M2 properly — none of it is extra work, it is the same work written down in the place the next milestone reads from.

### 9.5 Commitments to freeze before 09.11

Four decisions that shape M3–M6 and are cheap now, expensive later:

1. **Extension is a matcher, not a wrapper.** `NormalisedComa(BaseMatcher)` in `extension/matcher.py`, using `extension/canonicalise.py`, exposing per-signal sub-scores via `match_details`. The interface is written down in M2 even though the body is M3. This is what makes M4 "method execution" a real point rather than a formality.
2. **Baseline paper fixed.** COMA (VLDB 2002) for method lineage, Valentine's published `Coma` as the system baseline, Starmie (PVLDB 2023) as the alternative approach. Written into `evaluation/baselines.md` so M4's "pros w.r.t. a baseline paper" has a named target.
3. **Metric set frozen.** Precision / Recall / F1, `PrecisionTop10Percent`, `MRR`, raw and Hungarian one-to-one, reported by stratum S1–S4 and by ladder level. Changing the metric set after M4 invalidates the results; freezing it in M2 is free.
4. **Report section map fixed.** The seven M5 sections each already have a source artefact (§4 and `project-overview.md`). At M5 the draft is assembly; nothing has to be invented under deadline.

### 9.6 What M2 deliberately does not do

- Does not implement `extension/` beyond stubs — that body is M3's 3 preprocessing points and its own deliverable.
- Does not run the ladder benchmark — that is M4's evaluation.
- Does not write report prose past the 2 pages.
- Does not build the introductory tool notebooks — it only records which tools need one.

This keeps milestone boundaries clean: every later rubric has something new to grade, and nothing is pre-spent. A milestone that is already "done" in the previous one is worth no points in either.

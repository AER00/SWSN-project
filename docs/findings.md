# Findings log

Reverse-chronological. One entry per thing we learned by running the code, as opposed to
things we assumed in the plan. These feed the M2 report and the M5 draft.

---

## 2026-11-02 — triage, ground truth, and the first ladder results (evening)

**Licences are not on the dataset page, but they are in the API.** `WebFetch` on a Kaggle
dataset page returns only the title — the metadata sidebar is rendered client-side.
`https://www.kaggle.com/api/v1/datasets/view/<owner>/<slug>` returns JSON with
`licenseName` for every public dataset, anonymously. Every candidate resolved except
MovieLens, whose slug returns 403: not public or renamed. Recorded as `dropped`.

Licences as read: Olist CC BY-NC-SA 4.0, Instacart CC0, Craigslist Cars CC0, Airbnb NYC
CC0, Melbourne Housing CC BY-NC-SA 4.0, Cardekho "Database: Open Database", Diabetes
"Data files © Original Authors", Heart Failure "Database: Open Database".

**The published documentation holds.** The D9 audit ran against both C-doc datasets:
column coverage 1.00, zero missing or undocumented columns, and **all 6 documented foreign
keys resolve in both datasets at 100.00 %** — Olist (6 FKs, up to 112,650 child rows) and
Instacart (6 FKs, 32M child rows). That is the precondition for using documentation as
ground truth, and it now has a number instead of an assumption. Row counts are not
published, so `row_count` is null in the schema files and that column of the audit says
nothing rather than guessing.

**The datasets are less dirty than the literature implies — at L0 anyway.** Scored against
D1–D7, Olist shows D3 D5 D7 and Instacart D3 D6 D7: both exactly 3 of 7, the minimum that
passes the gate. D1 (header noise), D2 (type instability) and D4 (format heterogeneity)
are **absent from both at L0**. The mess is concentrated in review free text
(`olist_order_reviews_dataset`) and in *cross-table* value differences, not spread across
the tables. This is the finding that justifies the corruption ladder: real Kaggle data is
clean in the dimensions a matcher is most sensitive to, so you have to introduce them to
study them.

**Four fixes to the profiler, all found by it disagreeing with the data.**

1. *D4 fired on every column of every table.* `format_shapes` mapped digits to `9` and
   letters to `a`, so a 32-hex id like `06b8999e…` got a shape unique to its own
   letter/digit pattern — the count grew with the row count and the threshold flagged
   everything. Fixed by collapsing runs (`999` → `9`) and restricting D4 to columns that
   are mostly numeric or mostly date, which is what "several number formats in one column"
   actually means.
2. *D5 fired on free text.* Every comment is "unique except for casing", so the raw
   variant count is non-zero in any text column. Restricted to columns with a small
   vocabulary (`unique_ratio < 0.5`), where case/whitespace variants mean one entity
   written several ways.
3. *D6 fired on every primary key.* "ID-like" was defined as high cardinality *and* long
   values; single-token ids missed it, multi-word product names hit it. Redefined as free
   text (≥3 words per value) or a constant column.
4. *D3 used a mean where every other dimension used max.* Instacart's
   `days_since_prior_order` is null for **6 %** of rows — structural, since a user's first
   order has no predecessor — but averaged across 7 columns that dilutes to 0.9 %, under
   the 1 % threshold, so the dataset failed its own messiness gate for a reason that was an
   artefact of the aggregation. Now `max`, consistent with the other six.

**Cardekho ships four versions of the same domain under four naming conventions.**
`car data.csv` (snake_case), `CAR DETAILS FROM CAR DEKHO.csv` (spaced Title Case),
`Car details v3.csv` (Title Case), `car details v4.csv` (spaced Title Case, different
column set). That is a naturally occurring S2/S3 test bed — same concepts, different names
and formats, no corruption applied. It was already in the candidate list; it turns out to
be the best C-nat source in the collection, better than the 1.4 GB craigslist file.

**`recovery@k` is meaningless when k ≥ the number of target columns.** Olist's
`products -> category_translation` pair has two target columns, so recovery@3 was 1.0 for
every matcher at every level — a perfect score earned by there being nothing to rank.
Flagged with `recovery_at_3_degenerate` and excluded from aggregate means; the row stays in
the CSV so the table can show it with the caveat attached.

**Valentine's `DistributionBased` does not work reliably here.** 12 of 300 runs raised,
all from this one matcher, in two distinct ways:

- `PulpSolverError: Error while trying to execute` from `COIN_CMD` — reproducible, same
  input, every time. The bundled CBC binary runs fine standalone
  (`cbc -quit` prints its banner), so it is the invocation, not the binary.
- `ValueError: malformed node` from `literal_eval(v.name)` in
  `distribution_based/discovery.py` — the solver's variable names are built as
  `"(order_id,payment_type)"` and parsed back as a Python tuple, which only works when the
  cluster vertex names are numeric.

Pin details: valentine 1.1.0, PuLP 4.2.0, `cbcbox` 0.1.0, arm64 macOS. PuLP 4.x is the
declared dependency (`PuLP[cbc]>=4.0,<5.0`), so this is a defect in how the matcher is
written against that API, not a pinning mistake on our side. **Decision for M2:**
`DistributionBased` stays in the grid, its failures are reported as a count, and it is
excluded from cross-matcher comparisons with that reason stated. M3 must either pin an
older PuLP or drop it to four matchers.

**`duplicate_header` (L1) broke the cumulative ladder.** After L1 gives two columns the
same name, `out[col]` in the value-operator loop returns a two-column frame instead of a
series, and the run died with `cannot assemble with duplicate keys` raised inside pandas,
three operators away from the cause. Fixed by indexing value operators **positionally**
(`isetup`/`iloc`) instead of by label. Worth keeping the failure in mind: the same thing
will happen to any downstream code that addresses columns by name after L1.

**Attribution and cumulative modes are not interchangeable.** Each level applies only its
own operators to the original frame, so L2's corruption is not added on top of L1's — which
means COMA scores *higher* at L2 (0.958) than at L1 (0.431). That looks like a bug and is
not: L1 renames headers, L2 reformats values. Both modes are now implemented
(`apply_level(..., cumulative=)`), both are written to separate CSVs, and the report has to
say which one a table is showing.

**First headline result (cumulative, 4 matchers, 12 documented pairs, 5k-row join-aware
samples).** Recovery@1 by level:

| level | COMA | Cupid | Jaccard | SimFlooding |
|---|---|---|---|---|
| L0 | 0.958 | 0.847 | 0.917 | 0.958 |
| L1 header | **0.431** | **0.292** | **0.708** | **0.833** |
| L2 +values | 0.431 | 0.208 | 0.403 | 0.750 |
| L3 +noise | 0.431 | 0.292 | 0.403 | 0.722 |
| L4 +semantic | 0.431 | 0.292 | 0.403 | 0.722 |

Header noise costs more than every other dimension combined. And by stratum, the S3
correspondence (`product_category_name` ↔ `product_category_name_english`, the one genuine
cross-lingual pair) is recovered **by no matcher at any level** — 0.0 across the board —
while S1 sits at 1.0 until L1 and S2 at 1.0 for COMA. The extension's whole case is in that
0.0.

**The protocol file had never been parsed.** `headline:` was a YAML list with a
`recovery_k:` mapping key appended, which is a parse error. It survived because nothing
read the file until the benchmark runner did. Protocol files are now loaded in a test.

---

## 2026-11-02 — environment and first end-to-end run (Olist)

**Anonymous Kaggle download works.** `kagglehub.dataset_download("olistbr/brazilian-ecommerce")`
fetched 42.6 MB with no Kaggle account, token or `~/.kaggle/kaggle.json`. Version 2, nine
CSVs. The plan's preference for public *Datasets* over *Competitions* is correct —
competition data would still need accepted rules and a token.

**Python 3.13 via uv installs the whole stack cleanly.** `uv python install 3.13` then
`uv sync` → valentine 1.1.0, pandas, scipy, matplotlib, Jupyter. No PuLP wheel problem on
3.13 / macOS arm64.

**Coma downloads ~52 MB of NLTK data on first use.** `valentine.utils.utils.ensure_nltk_data`
fetches `punkt_tab`, `omw-1.4`, `stopwords` and `wordnet` into `~/nltk_data`. The first
`Coma` call took **26 s**; every later call took **0.15 s** on the same input. This is a
reproducibility constraint, not a curiosity:

- an offline machine cannot run Coma at all;
- any runtime comparison that includes the first call is wrong by two orders of magnitude;
- `make setup` now pre-fetches the resources (`make nltk`), and the protocol excludes
  warm-up from reported timings.

**Two sampling traps, found one after the other — both made the pipeline report the
opposite of the truth.**

1. *Row sampling.* Taking the first 5,000 rows of `orders` and of `order_payments`
   independently yields two **disjoint** sets of order ids, so the matcher sees no value
   relationship at all. Fixed by `swsn.sampling.sample_pair`, which samples key values once
   and filters both tables to them. Protocol rule: sample on a shared key, never per table.
2. *Distinct-value sampling.* `value_similarity` subsampled 1,000 distinct values per
   column before computing Jaccard. With ~99,400 distinct order ids per side, two
   **identical** value domains scored `0.0055` instead of `0.99999`, and the D8 diagnostic
   classified the most trivial match in the dataset as a Q3 trap. Jaccard over sampled
   distinct sets is not scale-invariant. Fixed: exact sets by default (`max_distinct=None`);
   subsampling is opt-in and documented as approximate.

The lesson is worth carrying into the report: **a sampling step must be shown not to change
the statistic it feeds.** Trap 1 was visible immediately because the numbers were absurd;
trap 2 survived one round of "fixing" because it also produced absurd numbers for a
plausible-sounding reason.

**Valentine returns scored pairs, not decisions.** Coma produced 5 pairs for
`orders ↔ payments` with scores 0.192–0.748; one is ground truth. F1 computed at threshold 0
is therefore meaningless (0.33) while `recovery@1` is 1.0. This is why the metric set
includes `PrecisionTop10Percent` and `MRR` and why the protocol forbids reporting a bare F1.

**Steady-state runtime is not the constraint.** After warm-up, a 8-column × 5-column pair
at 5,000 rows takes 0.15 s with Coma and 0.42 s with `JaccardDistanceMatcher` in the earlier
cold run. The full ladder (3 datasets × 5 matchers × 5 levels) is feasible in a notebook.

**Licence not yet confirmed.** The Olist dataset page did not render its licence field to
our fetcher. Recorded as `null` in `data/datasets.yaml` with a note — confirm before the
repository embeds anything or is publicised.

**Checksums recorded** for all nine Olist files (version 2), so the download is verifiable
with `make data OFFLINE=1`.

---

## Template for new entries

```
## YYYY-MM-DD — short title

**What we expected.** ...
**What happened.** ... (numbers, not adjectives)
**What it changes.** ... (code, protocol, or plan)
```

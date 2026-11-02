# Findings log

Reverse-chronological. One entry per thing we learned by running the code, as opposed to
things we assumed in the plan. These feed the M2 report and the M5 draft.

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

# Ground-truth annotation guide

Two ground-truth sources, one file format, one rulebook.

- **C-doc** (documented datasets): every positive comes from the publisher's schema
  documentation, transcribed into `schema/<dataset>.yaml` with a citation. Two people
  independently assign each correspondence to a stratum; disagreements are adjudicated.
- **C-nat** (independent Kaggle uploads): no documentation exists, so pairs are annotated
  from scratch by two people independently.

Cohen's κ is reported per pair in both cases. Pairs below κ = 0.6 are re-annotated, not
quietly kept.

## What counts as a correspondence

A pair of columns corresponds if **the same real-world attribute is represented in both**,
such that a reasonable analyst joining the two tables would pair them.

- Value *domains* must be comparable. `orders.order_id` and `order_payments.order_id` carry
  the same identifier → correspondence.
- Similar values are not sufficient. Two unconnected tables both having a `price` column do
  **not** correspond unless the prices describe the same thing at the same grain.
- Structural/join keys count: Valentine's task is discovering joinable columns, and an
  identifier that appears in both tables is exactly what a dataset-discovery system should
  surface.

## Strata

| Stratum | Definition | Example |
|---|---|---|
| **S1** | documented key, near-identical name | `orders.order_id` ↔ `payment.order_id` |
| **S2** | same concept, materially different name | `product_category_name` (PT) ↔ `product_category_name_english` |
| **S3** | same concept, different format / unit / grain | `customer_zip_code_prefix` (int) ↔ `geolocation_zip_code_prefix` |
| **S4** | trap: similar name or type, different meaning → **negative** | two unrelated `*_timestamp` columns; `customer_id` vs `customer_unique_id` |

S4 is a negative stratum. It exists because false positives are invisible in a
recovery-only metric, and because it is where the matchers actually fail.

## Rules

1. **One label per candidate pair.** Positives get a stratum; S4 entries are stored as
   negatives with `stratum: S4`.
2. **Ambiguous cases are excluded, not guessed.** Use `label: skip` with a note. Skipped
   pairs are excluded from every score and their count is reported.
3. **Many-to-one is allowed** only when the semantics justify it (e.g. a normalised
   reference table). Record it; do not silently drop halves.
4. **Never infer a positive from a matcher's output.** Annotation happens before any probe
   run, and annotators do not see matcher scores.
5. **Ground truth is versioned with the data.** When a dataset's pinned version changes,
   the GT is re-checked and the version recorded.

## Negative space

Within a table pair, every candidate not labelled positive is negative unless marked
`skip`. For pairs larger than 40 × 40 columns, annotate per column the top-10 lexical
candidates plus 10 random controls, and record the sampling rule used.

## File format

`gt/<dataset_or_pair>.csv`:

```csv
table_a,col_a,table_b,col_b,label,stratum,annotator,note
olist_orders,order_id,olist_order_payments,order_id,1,S1,aj,documented FK
olist_products,product_category_name,product_category_name_translation,product_category_name_english,1,S2,jl,PT -> EN
olist_orders,order_purchase_timestamp,olist_orders,order_approved_at,0,S4,aj,all date columns look alike
```

After adjudication the file gains an `adjudicated` column; the raw per-annotator files are
kept in `gt/raw/<annotator>/` so κ stays recomputable.

## Adjudication

Run `python -m ground_truth.agreement --gt-dir ground_truth/gt` to produce:

- κ per pair and pooled, per annotator pair;
- the disagreement list, which must be resolved and the resolution written in `note`;
- a count of skipped pairs per dataset, reported in the EDA report.

## For C-doc: transcription and audit

1. Transcribe the published schema into `ground_truth/schema/<dataset>.yaml` — tables,
   columns, keys, and a `source:` URL for each claim.
2. Run the D9 audit (`swsn.audit`) against the actual files before using the schema as GT.
   Corrections are logged in the schema file with a reason, never applied silently.
3. Only then assign strata and generate the GT CSV.

# Baselines

Fixed before results are seen, so that the M4 comparison has a named target rather than
whichever number happens to look favourable afterwards.

## 1. Method baseline — COMA

> H.-H. Do, E. Rahm. *COMA — A System for Flexible Combination of Schema Matching
> Approaches.* VLDB 2002. DOI: 10.1016/B978-155860869-6/50060-3

The method the extension derives from. COMA is the right baseline for a *method* claim:
any improvement has to come from what we changed, not from a different algorithm family.

**What we compare:** the published combination strategy (schema + instance signals,
match/difference aggregation) as implemented by Valentine's `Coma`.

## 2. System baseline — Valentine's published matchers

> C. Koutras et al. *Valentine: Evaluating Matching Techniques for Dataset Discovery.*
> ICDE 2021. DOI: 10.1109/ICDE51399.2021.00047

The other four built-ins (`Cupid`, `DistributionBased`, `JaccardDistanceMatcher`,
`SimilarityFlooding`) are the system-level reference points. They tell us whether an
improvement is specific to the hybrid matcher or generic to the task. In particular:

- `JaccardDistanceMatcher` — the instance-only, explainable floor;
- `Cupid` and `SimilarityFlooding` — schema-only, therefore insensitive to value
  corruption, which makes them the control for the L2/L3 levels of the ladder;
- `DistributionBased` — instance-only via distributions, the natural comparison for
  value-normalisation effects.

## 3. Alternative approach — Starmie (context, not a baseline to beat)

> G. Fan et al. *Starmie: Semantics-aware Dataset Discovery from Data Lakes with
> Contextualized Column-based Representation Learning.* PVLDB 16(7), 2023.

Learned column embeddings rather than hand-crafted similarity. Not an implementation
baseline — it is not a drop-in replacement and reproducing it is out of scope — but it is
the reference point for the *novelty* discussion in M4: our contribution is a
normalisation-aware, interpretable similarity, not a learned representation. State the
limitation explicitly rather than claiming superiority.

## What "better" means

The extension is better if, on the same table pairs and the same metrics
(`evaluation/protocol.yaml`):

1. recovery@k on **S2 and S3** improves while **S1 does not regress**, and
2. the improvement is attributable — switching off the corresponding canonicalisation
   component in the M4 ablation removes the gain, and
3. the S4 false-positive rate does not increase.

An improvement that only shows up in aggregate F1 is not reportable: it is dominated by S1
and says nothing about the messy setting the project is about.

# Milestone 1 — Selection of the topics, determining the teams
**Window:** 19–26.10.2026

## Team
- Members: TBD (names, student IDs)
- Roles for later milestones: TBD
- Note: the milestone title explicitly covers *determining the teams*, so this must be filled in even though the form has no dedicated field.

## Project title
Valentine — thorough analysis of the tool and improving it on messy Kaggle datasets

> Note: the original title says "Throughout analysis"; "thorough" is probably meant. Worth fixing before submission.

## Brief project description (≤50 words)

> We analyse Valentine's schema-matching suite and improve it for messy Kaggle tables, where column names and values are noisy and ground truth is absent. Starting from the hybrid COMA matcher, we identify failure modes and extend matching with normalisation-aware preprocessing, measuring whether the extension improves match quality.

**Word count: 47.**

- Goal: analyse how Valentine's matchers behave outside their curated benchmarks and improve matching on noisy real-world tables.
- Initial method: COMA, Valentine's default hybrid schema + instance matcher. The remaining built-ins (Cupid, DistributionBased, JaccardDistanceMatcher, SimilarityFlooding) serve as reference points.
- The extension is described at method level only; the concrete data and its exploratory analysis are Milestone 2 deliverables and are deliberately not fixed here.

## Literature

### Core paper(s)
1. C. Koutras, G. Siachamis, A. Ionescu, K. Psarakis, J. Brons, M. Fragkoulis, C. Lofi, A. Bonifati, A. Katsifodimos.
   *Valentine: Evaluating Matching Techniques for Dataset Discovery.* ICDE 2021, pp. 468–479.
   DOI: https://doi.org/10.1109/ICDE51399.2021.00047 · arXiv: https://arxiv.org/abs/2010.07386
2. C. Koutras et al. *Valentine in Action: Matching Tabular Data at Scale.* PVLDB 14(12), 2021 (demo).
   https://www.vldb.org/pvldb/vol14/p2871-koutras.pdf
3. H.-H. Do, E. Rahm. *COMA — A System for Flexible Combination of Schema Matching Approaches.* VLDB 2002.
   DOI: https://doi.org/10.1016/B978-155860869-6/50060-3
   *(Implementation we start from.)*

Supporting: Valentine benchmark datasets — https://zenodo.org/records/5084605 · code — https://github.com/delftdata/valentine

### Alternative approach paper(s)
1. G. Fan et al. *Starmie: Semantics-aware Dataset Discovery from Data Lakes with Contextualized Column-based Representation Learning.* PVLDB 16(7), 2023.
   https://www.vldb.org/pvldb/vol16/p1726-fan.pdf
   — learned column embeddings (contrastive self-supervision, table transformer, HNSW index) instead of hand-crafted similarity measures.
2. Y. Liu, E. H. M. Pena, A. S. R. Santos, E. Wu, J. Freire. *Magneto: Combining Small and Large Language Models for Schema Matching.* PVLDB 18(8), 2025.
   https://arxiv.org/abs/2412.08194 · code: https://github.com/VIDA-NYU/magneto-matcher
   — SLM candidate retrieval + LLM reranking, with LLM-generated training data.
3. (Optional) M. Parciak et al. *Schema Matching with Large Language Models: an Experimental Study.* TaDA@VLDB 2024.
   https://arxiv.org/abs/2407.11852

### Method-transfer paper(s)
1. D. Ritze, O. Lehmberg, C. Bizer. *Matching HTML Tables to DBpedia.* WIMS 2015.
   DOI: https://doi.org/10.1145/2797115.2797118
   — schema + instance matching moved from relational database schemas to header-less, messy web tables matched against a knowledge base; directly relevant to our noisy-table setting.
2. (Optional) R. Dijkman, M. Dumas, L. García-Bañuelos. *Graph Matching Algorithms for Business Process Model Similarity Search.* BPM 2009, LNCS 5701, pp. 48–63.
   DOI: https://doi.org/10.1007/978-3-642-03848-8_5
   — the same graph-matching idea transferred from schema matching to process-model search.

## Assessment

| Item | Selection | Points |
|---|---|---|
| Submission date | on time (submit by 26.10.2026) | 2 |
| Project type | a new method addressing the same problem — **recommended**; fallback: adaptation to a new dataset | 3 (fallback 2) |
| Presentation | deck prepared (`milestone1-presentation.md`), not yet delivered | 2 after delivery (0 now) |
| Literature — core | Valentine ICDE 2021 (+ demo, COMA) | 1 |
| Literature — alternative approach | Starmie, Magneto | 1 |
| Literature — method transfer | T2K Match (web tables → DBpedia) | 1 |

**Current state (deck not yet presented): 8/10** with type 3 · 7/10 with type 2.
**Projected after the presentation: 10/10** with type 3 · 9/10 with type 2.

### Before submitting — checklist
- [ ] Fix the title typo: "Throughout" → "Thorough".
- [ ] Fill in team members and roles.
- [ ] Export the deck to PDF (or host it) and put the link in the **Presentation** field.
- [ ] Confirm the project-type claim (3 recommended — see note below).
- [ ] Paste the three literature categories into the form with links.
- [ ] Check the 47-word description pastes cleanly (no markdown symbols).

### Project-type decision (worth settling before submitting)
- **2 pts — safe:** Valentine's published matchers applied to a new dataset population (messy Kaggle tables). Max final score 9/10.
- **3 pts — "a new method that addresses the same problem":** only defensible if the deliverable is a genuinely new matching approach (e.g. a messy-data-robust COMA variant with type/unit-aware normalisation, null/header handling and data-driven threshold selection), not just running the existing suite on new data. Max final score 10/10.

Recommendation: decide once the improvement direction is fixed; if the plan is "analyse + tune + add preprocessing", claim 3 and describe the extension as the new method, otherwise claim 2 honestly.

## Scope boundary (Milestone 1 only)

Milestone 1 fixes the topic, team, goal, initial method and literature. It does **not** commit to:

- which Kaggle datasets/tables are used, how many, or how they are paired — Milestone 2;
- ground-truth annotation protocol or formats — Milestone 2;
- EDA notebooks, plots, dirtiness dimensions or the exploratory report — Milestone 2;
- the benchmark harness, failure taxonomy or ablation design — execution phase after Milestone 2.

What Milestone 1 does commit to is the method claim: an existing published suite (Valentine/COMA) extended with a normalisation-aware matching layer, evaluated on the messy-table setting named in the title.

## Open questions to confirm
- Presentation: what is expected now — link, date, or "not yet"? Currently 0/2.
- Is the 50-word description limit inclusive of the title? (Assumed no.)
- Team members and submission channel/format.

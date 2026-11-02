# Bibliography

Extends the M1 literature list with the works the M2 design introduced. M1 fixed three
categories (core / alternative approach / method transfer); the M2 additions are a fourth
group covering data quality, evaluation and robustness, and they are what M5's "properly
refers to chosen literature" point reads.

Verify pagination and DOIs against the publisher record before the M5 draft — this file is
a working list, not a finished reference section.

## Core — the method being studied and its lineage

1. C. Koutras, G. Siachamis, A. Ionescu, K. Psarakis, J. Brons, M. Fragkoulis, C. Lofi,
   A. Bonifati, A. Katsifodimos. *Valentine: Evaluating Matching Techniques for Dataset
   Discovery.* ICDE 2021, pp. 468–479. DOI: 10.1109/ICDE51399.2021.00047
2. C. Koutras et al. *Valentine in Action: Matching Tabular Data at Scale.* PVLDB 14(12),
   2021. https://www.vldb.org/pvldb/vol14/p2871-koutras.pdf
3. H.-H. Do, E. Rahm. *COMA — A System for Flexible Combination of Schema Matching
   Approaches.* VLDB 2002. DOI: 10.1016/B978-155860869-6/50060-3 — **method baseline**.

## Alternative approach — same problem, different machinery

4. G. Fan et al. *Starmie: Semantics-aware Dataset Discovery from Data Lakes with
   Contextualized Column-based Representation Learning.* PVLDB 16(7), 2023.
5. Y. Liu, E. H. M. Pena, A. S. R. Santos, E. Wu, J. Freire. *Magneto: Combining Small and
   Large Language Models for Schema Matching.* PVLDB 18(8), 2025.
   arXiv:2412.08194
6. M. Parciak et al. *Schema Matching with Large Language Models: an Experimental Study.*
   TaDA@VLDB 2024. arXiv:2407.11852

## Method transfer — same method, different setting

7. D. Ritze, O. Lehmberg, C. Bizer. *Matching HTML Tables to DBpedia.* WIMS 2015.
   DOI: 10.1145/2797115.2797118
8. R. Dijkman, M. Dumas, L. García-Bañuelos. *Graph Matching Algorithms for Business
   Process Model Similarity Search.* BPM 2009, LNCS 5701, pp. 48–63.

## Data quality — added in M2 (frames D1–D9)

9. E. Rahm, H. H. Do. *Data Cleaning: Problems and Current Approaches.* IEEE Data
   Engineering Bulletin 23(4), 2000, pp. 3–13.
   — the standard problem taxonomy; our D1–D7 dimensions are a concretisation of it for
   tabular schema matching, and the report should say so rather than presenting the
   taxonomy as invented.

10. E. Rahm, P. A. Bernstein. *A Survey of Approaches to Automatic Schema Matching.*
    VLDB Journal 10(4), 2001, pp. 334–350.
    — the vocabulary the method section is written in (schema-level vs instance-level,
    element-level vs structure-level). Cite it where the matcher design is described.

## Evaluation and robustness — added in M2 (frames the corruption ladder)

11. D. Hendrycks, T. Dietterich. *Benchmarking Neural Network Robustness to Common
    Corruptions and Perturbations.* ICLR 2019. arXiv:1903.12261
    — precedent for controlled degradation as an evaluation instrument: the ladder is a
    corruption benchmark, and this is the paper that establishes that design as legitimate
    rather than artificial.

12. *(to add during M3)* a schema-matching evaluation or robustness study, if the M4
    related-work section needs a closer comparison for "how matching quality is normally
    measured". Candidate to be selected after the M4 literature pass; do not cite a
    placeholder.

## Citing in the report

- Datasets: cite the Kaggle page as the primary source and the publisher's own
  documentation for the schema (which is our ground truth).
- Taxonomy: cite [9] for the problem, not for our specific dimensions.
- Ladder: cite [11] for the method, and frame ours as a domain adaptation of it.
- Baseline: [1] and [3] for the comparison, [4] for the alternative-approach discussion.

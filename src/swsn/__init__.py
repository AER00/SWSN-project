"""SWSN 2026/27 — Valentine on messy Kaggle tables.

Modules
-------
registry    dataset registry and shared enums (strata, pair types, dataset classes)
download    kagglehub wrapper with checksum verification and an offline path
profile     D1-D7 dirtiness profiling per column and per table
audit       D9: does the published schema actually hold in the files?
pairdiag    D8: name similarity x value overlap per column pair
corrupt     declared corruption ladder operators with a preserve-match contract
probe       Valentine runs, scoring, recovery@k
agreement   Cohen's kappa and the adjudication report
normalize   minimal canonicaliser used only for the M2 preview
extension   the M3/M4 deliverable: canonicalisation + NormalisedComa
"""

__version__ = "0.1.0"

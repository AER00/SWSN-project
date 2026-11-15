# Data

Raw datasets are **not** committed to this repository. They are downloaded from Kaggle by
`python -m swsn.download` (or `make data`) and written to `data/raw/<id>/`, which is
gitignored.

## Why not commit the files

Every source is a third-party dataset with its own licence, several of them
non-commercial, and some large enough to make the repository unusable. Instead the
repository records:

- the Kaggle slug and pinned version of each dataset (`data/datasets.yaml`);
- a SHA-256 per downloaded file, verified on every run;
- the licence text and attribution for each dataset (below);
- the date the data was fetched.

Anyone can therefore reproduce the exact files, and the repository stays small and
redistributable.

## Licensing and attribution

Licences are recorded verbatim in `datasets.yaml`; this table mirrors them. Nothing is used until its licence is recorded.

| id | Dataset | Publisher | Licence | URL |
|---|---|---|---|---|
| olist | Brazilian E-Commerce Public Dataset by Olist | Olist | CC BY-NC-SA 4.0 | https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce |
| instacart | Instacart Market Basket Analysis | Instacart | CC0: Public Domain | https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis |
| movielens | MovieLens 25M | GroupLens | not retrievable (dropped, HTTP 403) | https://www.kaggle.com/datasets/grouplens/movielens-25m-dataset |

C-nat entries (6, status `candidate`: licence and checksum recorded in `datasets.yaml`, G3/G4 pending) are added to this table once they pass the full gate. If a licence forbids
redistribution but permits local research use, that is stated explicitly and the dataset
stays download-only.

## Offline / manual download

If `kagglehub` is unavailable or the download is blocked:

1. Download the dataset archive from the Kaggle URL above.
2. Extract it into `data/raw/<id>/` so that the CSVs sit directly in that folder.
3. Run `make data OFFLINE=1` (or `python -m swsn.download --offline`), which verifies
   the files against the recorded checksums and skips the network step.

Record any manual step in your pull request so the rest of the team can reproduce it.

## Derived data

`data/processed/` holds canonicalised tables; `data/synthetic/` holds the corruption
ladder (L1–L4). Both are generated, gitignored, and reproducible from the registry plus
the seeds in `corruption/ladder.yaml`.

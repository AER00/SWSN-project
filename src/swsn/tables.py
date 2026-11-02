"""Loading tables by their documented name.

A table is named in the schema file by its dataset-facing name, which is also the basename
of the CSV it arrives in (``olist_orders_dataset`` -> ``olist_orders_dataset.csv``). Keeping
that convention in one place means the audit, the profiler and the probe all resolve the
same file from the same name.

Reading options are fixed here rather than sprinkled across notebooks, because the choice
is part of the measurement. UTF-8 with BOM stripping is the only setting any of these files
needs; everything else is deliberately left to pandas' inference so that type instability
(D2) stays visible instead of being papered over by an explicit dtype map.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_DATA_DIR = Path("data")


def table_path(dataset_id: str, table: str, data_dir: str | Path = DEFAULT_DATA_DIR) -> Path:
    path = Path(data_dir) / "raw" / dataset_id / f"{table}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"table {dataset_id}/{table}: expected {path}. Run `make data --only {dataset_id}`."
        )
    return path


def load_table(
    dataset_id: str,
    table: str,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    nrows: int | None = None,
) -> pd.DataFrame:
    # encoding="utf-8-sig" strips the BOM pandas' C parser already handles, and also
    # handles the Python-engine fallback, so the first column always has the documented
    # name. Verified against product_category_name_translation.csv, which carries one.
    return pd.read_csv(table_path(dataset_id, table, data_dir), encoding="utf-8-sig", nrows=nrows)


def load_tables(
    dataset_id: str,
    tables: list[str],
    data_dir: str | Path = DEFAULT_DATA_DIR,
    nrows: int | None = None,
) -> dict[str, pd.DataFrame]:
    return {t: load_table(dataset_id, t, data_dir, nrows) for t in tables}

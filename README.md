# Valentine on messy Kaggle tables

We’re testing how well [Valentine](https://delftdata.github.io/valentine/) finds columns that mean the same thing in different tables. For example, an order ID can have a different name or format in an orders table and a payments table. Our starting point is COMA, which compares both column names and cell values. We built a version called NormalisedComa that cleans up common differences in cell values before comparing them.

This is our SWSN 2026/27 course project. We use [Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and [Instacart](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis) because their documentation gives us known column relationships to check our matches against.

## Milestone 3 submission

- [Tools and method choices](docs/tools.md) explains what we used and why we started with COMA.
- **Introductory notebooks** cover [Valentine](notebooks/tool_valentine.ipynb), [kagglehub](notebooks/tool_kagglehub.ipynb), [RapidFuzz](notebooks/tool_rapidfuzz.ipynb), and [PyYAML](notebooks/tool_pyyaml.ipynb). The notebooks include their outputs.
- [Preprocessing demo](docs/extension.md#m3-preprocessing) shows what changes before and after normalisation using Olist values. The [preprocessing code](src/swsn/extension/canonicalise.py) handles missing-value markers, date formats, numbers and unit labels, and text formatting.
- [Kanban board](https://github.com/users/AER00/projects/2/views/1) and [M3 issues](https://github.com/AER00/SWSN-project/milestone/1) show who took each task and its target date. The course brief lists 16 November and the GitHub milestone lists 23 November.

## Run the notebooks

Install [uv](https://docs.astral.sh/uv/) and Make, then run these commands from the repository root. The setup uses Python 3.13 and fetches the language data that Valentine needs. The Valentine notebook uses Olist, while the kagglehub notebook downloads a small public dataset and checks it against the version and checksum in our registry.

```bash
make setup
uv run python -m swsn.download --only olist
uv run jupyter nbconvert --to notebook --execute --inplace \
    notebooks/tool_valentine.ipynb notebooks/tool_kagglehub.ipynb \
    notebooks/tool_rapidfuzz.ipynb notebooks/tool_pyyaml.ipynb
```

For the full analysis, run `make data` to fetch the datasets, `make eda` to run all notebooks, and `make test` to run the tests. `make triage` checks which datasets meet our criteria. `make bench` runs the baseline benchmark and `make figures` regenerates the plots.

The raw CSVs are kept locally. The [dataset registry](data/datasets.yaml) lists the versions, checksums, and licences. The [data README](data/README.md) explains where to put the files if you need to download them manually.

## How we test the matchers

We take the same table pairs and add different kinds of noise, from renamed headers to changed number formats and category labels. We track the known matches through these changes. Recovery@1 measures how often a documented match ranks first for its source column. We also break down the results by match type, since easy ID matches can dominate the overall score.

In the baseline benchmark, COMA’s average Recovery@1 fell from 0.958 on the original tables to 0.542 after header changes. Jaccard dropped from 0.708 after header changes to 0.403 when we also changed value formats. The [M2 report](reports/milestone2-eda.pdf) covers the data, plots, and limitations. Our [first M4 results](docs/extension.md#m4-matcher-evaluation) compare NormalisedComa with COMA and Jaccard and show what happens when we switch off each cleaning step.

## Where things are

| Folder | Contents |
|---|---|
| `notebooks/` | Exploratory analysis (00–06) and the four M3 tool demos |
| `src/swsn/` | Data loading, analysis, and benchmark code. The matcher and its preprocessing are in `extension/`. |
| `corruption/` and `ground_truth/` | Noise settings and documented column matches |
| `evaluation/` | Evaluation settings and benchmark results |
| `reports/` and `docs/` | M2 report, figures, method notes, and references |

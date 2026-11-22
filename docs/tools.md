# Tool inventory

Everything the project uses, with the reason it was chosen. This is the M3 "selected
tools" material, written early so it reflects what the code actually depends on rather
than what we remember using.

Rubric mapping: *tools appropriate for the chosen datasets* (1 pt) · *well-suited to the
chosen methods* (1 pt). Languages and team-management platforms are listed for
completeness but are excluded from the introductory-notebook requirement.

## Languages and environment

| Tool | Role | Why | Milestone |
|---|---|---|---|
| Python 3.13 | implementation language | Valentine requires `>=3.12,<3.16`; 3.13 has wheels for every dependency (3.15 lacks PuLP wheels on macOS) | M2 |
| uv | environment and dependency management | resolves and locks the whole graph; installs the required interpreter; `uv sync` reproduces the environment from `uv.lock` | M2 |
| Make | entry points for common tasks | gives all team members the same commands for setup, data retrieval, notebook execution and tests | M2 |
| Git + GitHub | version control and hosting | public repository is a graded deliverable | M2 |

## Data handling

| Tool | Role | Why | Milestone |
|---|---|---|---|
| pandas | table loading and manipulation | the format Valentine consumes; dtype inference is itself one of the measured dirtiness dimensions (D2) | M2 |
| PyArrow / Parquet | intermediate storage | sampling and canonicalised tables reload fast; preserves inferred types exactly | M2 |
| kagglehub | dataset download | public Dataset downloads work anonymously; pins versions | M2 |
| PyYAML | configuration | dataset registry, evaluation protocol and the ladder are data, not code — reviewable in a diff | M2 |
| rapidfuzz | string comparison | illustrates how tokenisation and case affect similarity on noisy labels and category values | M3 |

## Matching

| Tool | Role | Why | Milestone |
|---|---|---|---|
| valentine | the object of study | five built-in matchers, documented metrics, `BaseMatcher` extension point — the project's core dependency | M2 |

## Method and preprocessing choices

COMA is the baseline because it combines column-name similarity with evidence from
cell values. Olist and Instacart have documented relationships for evaluating
matches, while the corruption ladder lets us vary header and value noise on the
same table pairs. Jaccard provides a value-based comparison for the extension.

NormalisedComa combines COMA's name similarity with Jaccard overlap on canonical
value sets. The preprocessing uses explicit, independently switchable rules for
null tokens, dates, numeric formats and text so each contribution can be evaluated
on the same inputs. See the [Olist preprocessing demo](extension.md#m3-preprocessing).

## Analysis and presentation

| Tool | Role | Why | Milestone |
|---|---|---|---|
| Jupyter + ipykernel | EDA notebooks | the graded M2 artefact; one notebook per analysis layer | M2 |
| matplotlib + seaborn | figures | vector PDF/SVG export for reuse in the M5 draft and M6 final report | M2 |
| LaTeX | report typesetting | 2-page PDF with figures and a reference list; consistent typesetting across milestones | M2 |

## Engineering

| Tool | Role | Why | Milestone |
|---|---|---|---|
| pytest | tests | guards the profiler, the corruption generator and the metric wrappers against silent regressions | M2 |
| ruff | lint and formatting | one dependency, fast, no debate about style | M2 |
| GitHub Projects | Kanban board | project management is 3 points in M3–M5; lives next to the code | M2 |

## Introductory notebooks required by M3

M3 asks for a minimal notebook per selected tool (languages and team platforms excluded).
Only these need one, and each is short:

| Tool | Notebook | Content |
|---|---|---|
| valentine | `notebooks/tool_valentine.ipynb` | load two tables, run `Coma`, read `MatcherResults`, compute F1 against a GT list, register a trivial custom matcher |
| kagglehub | `notebooks/tool_kagglehub.ipynb` | download a public dataset, verify a checksum, cache behaviour |
| rapidfuzz | `notebooks/tool_rapidfuzz.ipynb` | ratio vs token-set ratio on column names and category values |
| PyYAML | `notebooks/tool_pyyaml.ipynb` | load the registry, validate the ladder config, fail loudly on a bad entry |

The EDA notebooks show [pandas table inventory](../notebooks/01_inventory.ipynb)
and [plots of dirtiness and match recovery](../notebooks/02_dirtiness.ipynb).
The [README](../README.md#run-the-notebooks) shows Make and uv setup commands.

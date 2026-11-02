.PHONY: setup nltk data eda probe test report lint all clean

PY := uv run python
OFFLINE ?= 0

setup: uv sync nltk

# Valentine's Coma and Cupid download these on first use (~52 MB). Fetching them here
# keeps the first matcher run fast and makes offline use possible after setup.
nltk:
	$(PY) -c "import nltk, pathlib; d = str(pathlib.Path.home() / 'nltk_data'); [nltk.download(r, quiet=True, download_dir=d) for r in ('punkt_tab','omw-1.4','stopwords','wordnet')]"

data:
	$(PY) -m swsn.download --config data/datasets.yaml $(if $(filter 1,$(OFFLINE)),--offline,)

eda:
	$(PY) -m jupyter nbconvert --to notebook --execute --inplace \
		--ExecutePreprocessor.timeout=900 notebooks/*.ipynb

probe:
	$(PY) -m swsn.probe --protocol evaluation/protocol.yaml

test:
	uv run pytest

lint:
	uv run ruff check src tests

report:
	@echo "Build reports/milestone2-eda.tex with your LaTeX toolchain; figures live in reports/figures/"

all: setup data test eda

clean:
	rm -rf data/raw data/processed data/synthetic .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +

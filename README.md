# Peeky Data

[![Tests](https://github.com/yasamansmi/peeky-data/actions/workflows/tests.yml/badge.svg)](https://github.com/yasamansmi/peeky-data/actions/workflows/tests.yml)

A small CSV exploration tool for checking a dataset before analysis. Built with Python, pandas, and Streamlit.

**[Open the demo](https://peeky-data.streamlit.app/)** · Start with the built-in fictional orders dataset; no upload required.

## What it does

- Summarizes rows, columns, blank cells, and repeated rows.
- Profiles each column and preserves text identifiers such as `001`.
- Shows numeric statistics and distributions using the same converted values.
- Shows all ten intervals for high-cardinality numeric columns, or the five most frequent values otherwise.
- Exports a JSON quality report with findings, suggested checks, and methodology.
- Gives actionable errors for empty files, invalid encoding, duplicate headers, malformed rows, and oversized inputs.

## Design decisions and limits

This is a descriptive profiler, not an automatic cleaning or data-validation service. It never removes rows or decides whether a repeated event is an error.

- Input: UTF-8 (including BOM), comma/semicolon/tab separators, up to 10 MB, 100,000 rows, and 200 columns. Quoted delimiters and multiline fields are supported. Each record must have the same field count as the header.
- Blank or whitespace-only cells are missing. Literal `NA` and `N/A` remain text because they can be valid categories.
- Numeric inference requires every nonblank value to parse. Leading-zero integers stay text; mixed columns stay text. Dates, currency formatting, decimal commas, and semantic identifiers are not inferred.
- Infinite numbers are flagged and excluded from statistics and distributions. Standard deviation uses `ddof=1`; undefined statistics are `null` in the report.
- Duplicate detection compares original cell text after blank normalization. Top-five percentages use all nonblank values, not just the displayed five; numeric distributions use finite values only.
- Uploads are processed in memory on the app server, not solely in the browser. The application does not write uploads to disk or send them to external APIs. Use non-sensitive data on the public demo. Reports include column names and aggregate statistics, but not individual records.

## Run locally

Tested with Python 3.13.3. Use Python 3.13 and an isolated environment:

```bash
git clone https://github.com/yasamansmi/peeky-data
cd peeky-data
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run dataframe_explorer_streamlit.py
```

Direct dependencies are pinned in `requirements.txt`. `requirements-lock.txt` records the full tested environment (including test dependencies) for a more tightly pinned installation:

```bash
pip install -r requirements-lock.txt
```

## Test

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Tests cover malformed CSVs, upload limits, encoding, quoted fields, leading-zero identifiers, missing values, duplicate rows, numeric conversion, complete bins, percentage denominators, non-finite values, JSON export, and Streamlit's sample/upload states. GitHub Actions runs them on Python 3.13.

## Project structure

- `data_quality.py`: parsing, profiling, distributions, and report generation; independent of the UI.
- `dataframe_explorer_streamlit.py`: Streamlit interface.
- `data/sample.csv`: intentionally imperfect fictional orders.
- `tests/test_quality.py`: analysis and app tests.

The older `dashboard_demo.gif` and `.mov` show the original interface and are retained as historical assets.

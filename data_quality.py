"""CSV validation and descriptive profiling, independent of Streamlit."""
import csv
import io
import json

import numpy as np
import pandas as pd

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 200


class CSVError(ValueError):
    """An actionable error suitable for display to the uploader."""


def load_csv(data: bytes, delimiter: str = ',') -> pd.DataFrame:
    if len(data) > MAX_BYTES:
        raise CSVError('Choose a CSV smaller than 10 MB.')
    if delimiter not in (',', ';', '\t'):
        raise CSVError('Choose comma, semicolon, or tab as the separator.')
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise CSVError('Save the file as CSV UTF-8, then upload it again.') from exc
    if not text.strip():
        raise CSVError('This file is empty. Add a header and at least one data row.')
    if '\x00' in text:
        raise CSVError('This does not look like a text CSV. Export it as CSV UTF-8.')
    reader = csv.reader(io.StringIO(text), delimiter=delimiter, strict=True)
    try:
        header = next(reader)
        if not header or any(not name.strip() for name in header):
            raise CSVError('Every column needs a name. Check the header row.')
        header = [name.strip() for name in header]
        if len(set(header)) != len(header):
            raise CSVError('Column names must be unique. Rename repeated headers.')
        if len(header) > MAX_COLUMNS:
            raise CSVError('Choose a file with 200 columns or fewer.')
        rows = []
        for row in reader:
            if not row:  # Ignore blank physical lines, not rows of empty cells.
                continue
            if len(row) != len(header):
                raise CSVError(f'Near line {reader.line_num}: expected {len(header)} fields, found {len(row)}. Check the separator and quotes.')
            rows.append(row)
            if len(rows) > MAX_ROWS:
                raise CSVError('Choose a file with 100,000 data rows or fewer.')
    except csv.Error as exc:
        raise CSVError('The CSV has broken quoting. Export it again with quoted text fields.') from exc
    if not rows:
        raise CSVError('This file has headers but no data rows.')
    # Preserve original text, including identifiers and literal NA/N/A categories.
    frame = pd.DataFrame(rows, columns=header, dtype='string')
    return frame.mask(frame.apply(lambda col: col.str.strip().eq('')))


def numeric_values(series: pd.Series):
    values = series.dropna().str.strip()
    if values.empty or values.str.match(r'^[+-]?0\d+$').any():
        return None  # Leading-zero identifiers stay text.
    try:
        return pd.to_numeric(values, errors='raise')
    except (ValueError, TypeError):
        return None


def profile(frame: pd.DataFrame) -> dict:
    columns = []
    for name in frame:
        raw = frame[name]
        numeric = numeric_values(raw)
        item = {'column': name, 'type': 'empty' if raw.dropna().empty else 'text',
                'missing': int(raw.isna().sum()),
                'missing_pct': round(float(raw.isna().mean() * 100), 2),
                'unique': int(raw.nunique()), 'non_finite': 0}
        if numeric is not None:
            finite = numeric[np.isfinite(numeric)]
            item['type'] = 'numeric'
            item['non_finite'] = int(len(numeric) - len(finite))
            item['stats'] = {
                key: (float(value) if pd.notna(value) and np.isfinite(value) else None)
                for key, value in {'min': finite.min(), 'max': finite.max(),
                                   'mean': finite.mean(), 'std': finite.std()}.items()
            }
        columns.append(item)
    return {'rows': len(frame), 'columns': len(frame.columns),
            'missing_cells': int(frame.isna().sum().sum()),
            'missing_pct': round(float(frame.isna().sum().sum() / frame.size * 100), 2),
            'duplicate_rows': int(frame.duplicated().sum()), 'column_details': columns}


def distribution(series: pd.Series) -> pd.DataFrame:
    numeric = numeric_values(series)
    if numeric is not None:
        values = numeric[np.isfinite(numeric)]
        if values.nunique() > 10:
            counts = pd.cut(values, bins=10).value_counts(sort=False).sort_index()
            return pd.DataFrame({'Value / interval': counts.index.astype(str),
                                 'Count': counts.values,
                                 'Percent': (counts.values / len(values) * 100).round(2)})
    else:
        values = series.dropna()
    counts = values.value_counts().head(5)
    return pd.DataFrame({'Value / interval': counts.index.astype(str), 'Count': counts.values,
                         'Percent': (counts.values / max(len(values), 1) * 100).round(2)})


def report_json(summary: dict) -> str:
    report = dict(summary)
    checks = []
    if summary['missing_cells']:
        checks.append('Review missing fields before choosing whether to fill or exclude them.')
    if summary['duplicate_rows']:
        checks.append('Confirm whether repeated rows represent duplicate records or valid repeated events.')
    if any(col['non_finite'] for col in summary['column_details']):
        checks.append('Review infinite numeric values; they are excluded from numeric statistics and distributions.')
    if any(col['unique'] == 1 for col in summary['column_details']):
        checks.append('Check constant columns for useful metadata or redundant features.')
    report['suggested_checks'] = checks or ['No issues were flagged by these basic checks. Validate against your domain rules.']
    report['methodology'] = ('Only blank/whitespace cells count as missing. NA/N/A remain text. '
        'Numeric inference requires every nonblank value to parse; leading-zero integers stay text. '
        'Standard deviation is sample standard deviation (ddof=1). Duplicates compare original cell text '
        'after blank normalization, excluding the header. No rows are removed. '
        'This report does not establish accuracy, fitness, or completeness of the data.')
    return json.dumps(report, indent=2, allow_nan=False)

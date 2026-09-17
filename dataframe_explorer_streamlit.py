"""Peeky Data: a small, testable CSV exploration tool."""
from pathlib import Path
import json

import pandas as pd
import streamlit as st

from data_quality import CSVError, distribution, load_csv, profile, report_json

st.set_page_config(page_title='Peeky Data · CSV explorer', page_icon='👀', layout='wide')
st.title('Peeky Data')
st.write('Get to know your CSV before you work with it.')
st.caption('Find missing values, repeated rows, and column patterns. Nothing is changed automatically.')

source = st.radio('Start exploring', ['Try the sample', 'Upload a CSV'], horizontal=True)
if source == 'Try the sample':
    data = (Path(__file__).parent / 'data/sample.csv').read_bytes()
    delimiter = ','
    st.info('Sample: 15 fictional orders, with missing values and one repeated row to investigate.')
else:
    st.caption('UTF-8 CSV · up to 10 MB, 100,000 rows, and 200 columns. Files are processed on the app server; this app does not save uploads to disk. Use non-sensitive data on the public demo.')
    separator = st.selectbox('Separator', ['Comma', 'Semicolon', 'Tab'])
    delimiter = {'Comma': ',', 'Semicolon': ';', 'Tab': '\t'}[separator]
    uploaded = st.file_uploader('Choose a CSV', type=['csv'])
    if uploaded is None:
        st.info('Upload a file, or select “Try the sample” above.')
        st.stop()
    data = uploaded.getvalue()

try:
    frame = load_csv(data, delimiter)
except CSVError as exc:
    st.error(str(exc))
    st.stop()

summary = profile(frame)
for area, label, value in zip(st.columns(4), ['Rows', 'Columns', 'Missing cells', 'Repeated rows'],
                              [summary['rows'], summary['columns'], summary['missing_cells'], summary['duplicate_rows']]):
    area.metric(label, f'{value:,}')
st.caption(f"{summary['missing_pct']}% of cells are blank · Repeated rows count occurrences after the first.")

overview, details, report = st.tabs(['Overview', 'Explore a column', 'Quality report'])
with overview:
    st.subheader('Where to look first')
    table = pd.DataFrame(summary['column_details']).drop(columns=['stats'], errors='ignore')
    st.dataframe(table.rename(columns={'column': 'Column', 'type': 'Inferred type', 'missing': 'Missing',
        'missing_pct': 'Missing (%)', 'unique': 'Distinct values', 'non_finite': 'Infinite values'}), hide_index=True, width='stretch')
    st.subheader('Data preview')
    st.caption('First 50 rows · Original values are preserved, including leading zeros.')
    st.dataframe(frame.head(50), hide_index=True, width='stretch')
with details:
    selected = st.selectbox('Column', frame.columns)
    item = next(col for col in summary['column_details'] if col['column'] == selected)
    if item['type'] == 'empty':
        st.info('This column contains only blank values.')
    else:
        if item['type'] == 'numeric':
            st.subheader('Numeric summary')
            st.dataframe(pd.DataFrame([item['stats']]), hide_index=True, width='stretch')
            st.caption('Finite values only. Standard deviation uses the sample formula; it needs at least two values.')
        if item['non_finite']:
            st.warning(f"{item['non_finite']} infinite values excluded from statistics and distribution.")
        values = distribution(frame[selected])
        st.subheader('Value distribution')
        st.caption('Numeric columns with more than 10 distinct finite values show all 10 equal-width intervals. Otherwise, the five most frequent values are shown. Percentages use all nonblank values (finite values for numeric columns).')
        st.dataframe(values, hide_index=True, width='stretch')
        if not values.empty:
            st.bar_chart(values.set_index('Value / interval')['Count'])
with report:
    st.subheader('Checks to take with you')
    report_text = report_json(summary)
    for check in json.loads(report_text)['suggested_checks']:
        st.write('• ' + check)
    st.download_button('Download quality report', report_text, file_name='peeky-data-quality.json', mime='application/json')
    st.caption('Includes counts, column statistics, methodology, and suggested checks. Contains column names but no individual rows.')
    with st.expander('How the analysis works'):
        st.write(json.loads(report_text)['methodology'])

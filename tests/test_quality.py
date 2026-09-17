import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import data_quality as dq


@pytest.mark.parametrize('data,message', [
    (b'', 'empty'), (b'a,b\n', 'no data'), (b'a,a\n1,2', 'unique'),
    (b'a, a\n1,2', 'unique'), (b',b\n1,2', 'name'),
    (b'a,b\n1,2,3', 'expected'), (b'a,b\n1', 'expected'),
    (b'a\n"broken', 'quoting'), (b'a\n\xff', 'UTF-8'),
    (b'a\n\x00', 'text CSV'),
])
def test_bad_files(data, message):
    with pytest.raises(dq.CSVError, match=message):
        dq.load_csv(data)


def test_limits(monkeypatch):
    monkeypatch.setattr(dq, 'MAX_BYTES', 2)
    with pytest.raises(dq.CSVError, match='10 MB'):
        dq.load_csv(b'a\n1')
    monkeypatch.setattr(dq, 'MAX_BYTES', 1000)
    monkeypatch.setattr(dq, 'MAX_ROWS', 1)
    with pytest.raises(dq.CSVError, match='100,000'):
        dq.load_csv(b'a\n1\n2')
    monkeypatch.setattr(dq, 'MAX_COLUMNS', 1)
    with pytest.raises(dq.CSVError, match='200'):
        dq.load_csv(b'a,b\n1,2')


def test_bom_quotes_and_separator():
    frame = dq.load_csv('\ufeffid;note\n001;"hello;\nworld"\n'.encode(), ';')
    assert frame.iloc[0].tolist() == ['001', 'hello;\nworld']


def test_missing_text_identifiers_and_duplicates():
    frame = dq.load_csv(b'id,value,note,empty\n001, 1 ,NA,\n002,2,N/A, \n002,2,N/A, \n')
    summary = dq.profile(frame)
    assert summary['duplicate_rows'] == 1
    assert summary['missing_cells'] == 3
    assert [c['type'] for c in summary['column_details']] == ['text', 'numeric', 'text', 'empty']
    assert summary['column_details'][1]['stats']['mean'] == pytest.approx(5 / 3)
    assert summary['column_details'][2]['missing'] == 0


def test_full_bins_and_numeric_text():
    frame = dq.load_csv(('n\n' + '\n'.join(str(i) for i in range(20))).encode())
    distribution = dq.distribution(frame.n)
    assert len(distribution) == 10
    assert distribution.Count.sum() == 20
    assert distribution.Percent.sum() == 100


def test_top_five_denominator():
    frame = dq.load_csv(b'x\na\na\nb\nc\nd\ne\nf\n')
    values = dq.distribution(frame.x)
    assert len(values) == 5
    assert values.iloc[0]['Percent'] == 28.57
    assert values.Count.sum() == 6


def test_nonfinite_and_single_value_report():
    frame = dq.load_csv(b'x,y\ninf,1\n-inf,\n2,\n')
    summary = dq.profile(frame)
    assert summary['column_details'][0]['non_finite'] == 2
    assert summary['column_details'][0]['stats']['mean'] == 2
    assert summary['column_details'][1]['stats']['std'] is None
    assert dq.distribution(frame.x).Count.sum() == 1
    parsed = json.loads(dq.report_json(summary), parse_constant=lambda _: pytest.fail('Invalid JSON number'))
    assert len(parsed['suggested_checks']) >= 2


def test_all_infinite_distribution():
    assert dq.distribution(dq.load_csv(b'x\ninf\n-inf').x).empty


def test_app_sample_and_upload_empty_state():
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'dataframe_explorer_streamlit.py')).run(timeout=20)
    assert not app.exception
    assert [metric.value for metric in app.metric] == ['15', '6', '4', '1']
    app.selectbox[0].select('order_value').run()
    assert not app.exception
    app.radio[0].set_value('Upload a CSV').run()
    assert not app.exception
    assert len(app.metric) == 0
    assert 'Upload a file' in app.info[0].value

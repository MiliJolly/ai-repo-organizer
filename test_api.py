"""
test_api.py
Basic API tests. Not comprehensive, just smoke tests to catch obvious breakage.
Run: pytest test_api.py -v

TODO: add proper fixtures, mock the CSV loading, write edge case tests
"""

import pytest
import json
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def test_get_customers(client):
    res = client.get('/api/customers')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert 'customers' in data
    assert 'total' in data
    assert isinstance(data['customers'], list)


def test_get_customers_with_segment(client):
    res = client.get('/api/customers?segment=VIP')
    assert res.status_code == 200
    data = json.loads(res.data)
    for c in data['customers']:
        assert c['segment'] == 'VIP'


def test_get_customer_by_id(client):
    res = client.get('/api/customers/10001')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['customer_id'] == 10001


def test_get_customer_not_found(client):
    res = client.get('/api/customers/99999')
    assert res.status_code == 404


def test_recommend(client):
    payload = {'customer_id': 10001, 'n': 3}
    res = client.post('/api/recommend',
                      data=json.dumps(payload),
                      content_type='application/json')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert 'recommendations' in data
    assert len(data['recommendations']) <= 3


def test_segment_vip(client):
    payload = {'clv': 8000, 'frequency': 15}
    res = client.post('/api/segment',
                      data=json.dumps(payload),
                      content_type='application/json')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['segment'] == 'VIP'


def test_segment_at_risk(client):
    payload = {'clv': 200, 'frequency': 1}
    res = client.post('/api/segment',
                      data=json.dumps(payload),
                      content_type='application/json')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['segment'] == 'At-Risk'


# TODO: test predict_churn endpoint
# currently skipping because it requires a trained model pkl
# @pytest.mark.skip(reason="requires churn_model.pkl")
# def test_predict_churn(client): ...

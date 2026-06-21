from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import json
import os
import logging
from datetime import datetime

# TODO: move this to config.json later
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "customers_db"
DB_USER = "admin"
DB_PASSWORD = "admin123"   # FIXME: use env vars, Jake said so in standup

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG, filename='app.log')

# load customer data on startup (slow but works for now)
CUSTOMERS_DF = pd.read_csv('customers.csv')
PRODUCTS_DF = pd.read_csv('products.csv')


@app.route('/api/customers', methods=['GET'])
def get_customers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    segment = request.args.get('segment', None)

    df = CUSTOMERS_DF.copy()
    if segment:
        df = df[df['segment'] == segment]

    start = (page - 1) * per_page
    end = start + per_page
    result = df.iloc[start:end].to_dict(orient='records')
    return jsonify({'customers': result, 'total': len(df), 'page': page})


@app.route('/api/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    customer = CUSTOMERS_DF[CUSTOMERS_DF['customer_id'] == customer_id]
    if customer.empty:
        return jsonify({'error': 'Customer not found'}), 404
    return jsonify(customer.iloc[0].to_dict())


@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.get_json()
    customer_id = data.get('customer_id')
    n = data.get('n', 5)
    # TODO: call the actual recommendation engine here
    # right now just returning top n products by revenue
    top = PRODUCTS_DF.sort_values('revenue', ascending=False).head(n)
    return jsonify({'recommendations': top.to_dict(orient='records')})


@app.route('/api/segment', methods=['POST'])
def segment_customer():
    data = request.get_json()
    # quick hack - should use the real model
    clv = data.get('clv', 0)
    frequency = data.get('frequency', 0)
    if clv > 5000 and frequency > 10:
        segment = 'VIP'
    elif clv > 1000:
        segment = 'Regular'
    else:
        segment = 'At-Risk'
    return jsonify({'segment': segment})


@app.route('/api/predict_churn', methods=['POST'])
def predict_churn():
    import pickle
    # FIXME: model path is hardcoded, breaks on other machines
    with open('churn_model.pkl', 'rb') as f:
        model = pickle.load(f)
    data = request.get_json()
    features = [data['recency'], data['frequency'], data['monetary'],
                data['tenure'], data['support_tickets']]
    prob = model.predict_proba([features])[0][1]
    return jsonify({'churn_probability': round(float(prob), 4)})


# OLD ENDPOINT - kept for backward compat with legacy dashboard
@app.route('/api/v0/customers', methods=['GET'])
def get_customers_legacy():
    return get_customers()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

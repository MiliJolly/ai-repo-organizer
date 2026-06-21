from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import json, os, logging
from datetime import datetime
from functools import wraps

# app_v2.py - rewriting app.py properly with auth and better structure
# started 2024-11-14, still WIP

app = Flask(__name__)

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-do-not-use-in-prod')

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-KEY')
        # TODO: validate against DB instead of env var
        if key != os.environ.get('API_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/api/v2/customers', methods=['GET'])
@require_api_key
def get_customers():
    try:
        df = pd.read_csv('customers.csv')
        segment = request.args.get('segment')
        if segment:
            df = df[df['segment'] == segment]
        return jsonify({'data': df.to_dict(orient='records'), 'count': len(df)})
    except Exception as e:
        logging.error(f"Error in get_customers: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v2/recommend', methods=['POST'])
@require_api_key
def recommend():
    body = request.get_json()
    cid = body.get('customer_id')
    if not cid:
        return jsonify({'error': 'customer_id required'}), 400
    # call recommendations module
    from recommendations import get_recommendations
    recs = get_recommendations(cid, n=body.get('n', 5))
    return jsonify({'customer_id': cid, 'recommendations': recs})


@app.route('/api/v2/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


# NOTE: /api/v2/segment is not done yet, using app.py version for now

if __name__ == '__main__':
    app.run(debug=False, port=5001)

"""
predict.py  -  run batch predictions or single inference
Usage:
    python predict.py --batch customers.csv --out predictions_out.csv
    python predict.py --customer 10042

TODO: integrate with app.py endpoint instead of running standalone
"""

import pickle
import pandas as pd
import numpy as np
import argparse
import json
import sys
from datetime import datetime

CHURN_MODEL_PATH = 'churn_model.pkl'
CLV_MODEL_PATH = 'clv_model.pkl'
FEATURES = ['recency', 'frequency', 'monetary', 'tenure', 'support_tickets',
            'email_opens', 'last_purchase_days', 'avg_order_value']


def load_model(path):
    try:
        with open(path, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        print(f"ERROR: model file not found at {path}")
        print("Run model_training.py --save first")
        sys.exit(1)


def predict_batch(input_path, output_path):
    churn_model = load_model(CHURN_MODEL_PATH)
    clv_model = load_model(CLV_MODEL_PATH)

    df = pd.read_csv(input_path)
    print(f"Running predictions for {len(df)} customers...")

    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        print(f"WARNING: missing features {missing}, filling with 0")
        for col in missing:
            df[col] = 0

    X = df[FEATURES].fillna(0)

    df['churn_probability'] = churn_model.predict_proba(X)[:, 1].round(4)
    df['churn_prediction'] = (df['churn_probability'] > 0.5).astype(int)
    df['predicted_clv'] = clv_model.predict(X).round(2)
    df['prediction_date'] = datetime.utcnow().date().isoformat()

    df.to_csv(output_path, index=False)
    print(f"Predictions saved to {output_path}")
    print(f"  Churn rate: {df['churn_prediction'].mean():.1%}")
    print(f"  Avg predicted CLV: ${df['predicted_clv'].mean():,.2f}")


def predict_single(customer_id):
    df = pd.read_csv('customers.csv')
    row = df[df['customer_id'] == int(customer_id)]
    if row.empty:
        print(f"Customer {customer_id} not found")
        sys.exit(1)

    churn_model = load_model(CHURN_MODEL_PATH)
    clv_model = load_model(CLV_MODEL_PATH)

    X = row[FEATURES].fillna(0)
    churn_prob = float(churn_model.predict_proba(X)[0][1])
    clv = float(clv_model.predict(X)[0])

    result = {
        'customer_id': customer_id,
        'churn_probability': round(churn_prob, 4),
        'churn_risk': 'HIGH' if churn_prob > 0.7 else ('MEDIUM' if churn_prob > 0.4 else 'LOW'),
        'predicted_clv': round(clv, 2),
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', help='Input CSV for batch prediction')
    parser.add_argument('--out', default='predictions_out.csv')
    parser.add_argument('--customer', help='Single customer ID')
    args = parser.parse_args()

    if args.batch:
        predict_batch(args.batch, args.out)
    elif args.customer:
        predict_single(args.customer)
    else:
        print("Specify --batch <file> or --customer <id>")
        sys.exit(1)

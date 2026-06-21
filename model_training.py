"""
model_training.py
Train churn prediction + CLV regression models on customer dataset.
Run: python model_training.py --model churn --save

Last updated by Sarah, 2024-10-22
NOTE: accuracy dropped to 0.71 after adding Q3 data, need to investigate
"""

import pandas as pd
import numpy as np
import pickle
import argparse
import json
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (classification_report, confusion_matrix,
                             mean_absolute_error, r2_score, roc_auc_score)
import warnings
warnings.filterwarnings('ignore')

# ---- hardcoded paths, fix before prod ----
DATA_PATH = 'customers.csv'
CHURN_MODEL_PATH = 'churn_model.pkl'
CLV_MODEL_PATH = 'clv_model.pkl'
RESULTS_PATH = 'model_results.json'

CHURN_FEATURES = ['recency', 'frequency', 'monetary', 'tenure', 'support_tickets',
                  'email_opens', 'last_purchase_days', 'avg_order_value']
CLV_FEATURES = ['frequency', 'monetary', 'tenure', 'avg_order_value',
                'product_categories', 'email_opens']


def load_and_prepare(path):
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows from {path}")

    # drop nulls - maybe should impute instead? ask ML team
    df = df.dropna(subset=CHURN_FEATURES + ['churned', 'clv'])
    print(f"After dropping nulls: {len(df)} rows")

    # encode segment
    le = LabelEncoder()
    df['segment_enc'] = le.fit_transform(df['segment'].fillna('Unknown'))
    return df


def train_churn_model(df, save=False):
    print("\n=== Training Churn Model ===")
    X = df[CHURN_FEATURES]
    y = df['churned'].astype(int)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y)

    # tried LogisticRegression - worse. GBM was best but too slow for inference
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=5,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_proba)

    print(f"AUC-ROC: {auc:.4f}")
    print(classification_report(y_test, y_pred))

    results = {
        'model': 'RandomForestClassifier',
        'auc': round(auc, 4),
        'timestamp': datetime.utcnow().isoformat(),
        'n_train': len(X_train),
        'n_test': len(X_test),
        'features': CHURN_FEATURES,
    }

    if save:
        with open(CHURN_MODEL_PATH, 'wb') as f:
            pickle.dump(model, f)
        print(f"Saved churn model to {CHURN_MODEL_PATH}")

    return model, results


def train_clv_model(df, save=False):
    print("\n=== Training CLV Model ===")
    X = df[CLV_FEATURES].fillna(0)
    y = df['clv']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42)

    model = GradientBoostingRegressor(
        n_estimators=150, max_depth=4, learning_rate=0.05, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print(f"MAE: {mae:.2f}  R2: {r2:.4f}")

    if save:
        with open(CLV_MODEL_PATH, 'wb') as f:
            pickle.dump(model, f)
        print(f"Saved CLV model to {CLV_MODEL_PATH}")

    return model, {'mae': round(mae, 2), 'r2': round(r2, 4)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['churn', 'clv', 'all'], default='all')
    parser.add_argument('--save', action='store_true')
    args = parser.parse_args()

    df = load_and_prepare(DATA_PATH)
    all_results = {}

    if args.model in ('churn', 'all'):
        _, res = train_churn_model(df, save=args.save)
        all_results['churn'] = res

    if args.model in ('clv', 'all'):
        _, res = train_clv_model(df, save=args.save)
        all_results['clv'] = res

    with open(RESULTS_PATH, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {RESULTS_PATH}")

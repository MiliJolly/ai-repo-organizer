"""
data_preprocessing.py
Clean and feature-engineer raw customer export from CRM.

Run before model_training.py.
Input:  raw_customers_export.csv  (from Salesforce)
Output: customers.csv

Last cleaned: 2024-09-30 by Dev
NOTE: the raw export has duplicate customer_ids from the Salesforce migration bug,
      deduplicated here by keeping the most recent record.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import os

RAW_PATH = 'raw_customers_export.csv'
OUT_PATH = 'customers.csv'

# column rename map (Salesforce field names → our names)
RENAME_MAP = {
    'Id': 'customer_id',
    'Contact_Email__c': 'email',
    'Account_Name': 'company',
    'Segment__c': 'segment',
    'Total_Revenue__c': 'monetary',
    'Last_Purchase_Date__c': 'last_purchase_date',
    'Created_Date': 'signup_date',
    'Support_Cases_Count__c': 'support_tickets',
    'Email_Opens_Last90__c': 'email_opens',
    'Is_Churned__c': 'churned',
    'CLV_Predicted__c': 'clv',
}


def load_raw(path):
    if not os.path.exists(path):
        print(f"WARNING: {path} not found, generating synthetic data for demo")
        return _generate_synthetic_data()
    df = pd.read_csv(path, low_memory=False)
    print(f"Raw data: {len(df)} rows, {len(df.columns)} columns")
    return df


def _generate_synthetic_data(n=9225):
    """Generate synthetic customer data for demo/testing."""
    np.random.seed(42)
    now = datetime.now()

    segments = np.random.choice(['VIP', 'Regular', 'At-Risk', 'New'],
                                 n, p=[0.14, 0.52, 0.22, 0.12])
    tenure = np.random.randint(1, 120, n)
    frequency = np.maximum(1, np.random.poisson(5, n))
    monetary = np.round(np.random.lognormal(6.5, 1.2, n), 2)
    recency = np.random.randint(1, 400, n)

    df = pd.DataFrame({
        'customer_id': range(10001, 10001 + n),
        'email': [f'customer{i}@example.com' for i in range(n)],
        'company': [f'Company {chr(65 + i % 26)}{i // 26}' for i in range(n)],
        'segment': segments,
        'recency': recency,
        'frequency': frequency,
        'monetary': monetary,
        'tenure': tenure,
        'support_tickets': np.random.poisson(1.2, n),
        'email_opens': np.random.randint(0, 80, n),
        'avg_order_value': np.round(monetary / frequency, 2),
        'last_purchase_days': recency,
        'last_purchase_date': [(now - timedelta(days=int(r))).strftime('%Y-%m-%d')
                               for r in recency],
        'signup_date': [(now - timedelta(days=int(t * 30))).strftime('%Y-%m-%d')
                        for t in tenure],
        'product_categories': np.random.randint(1, 8, n),
        'purchased_products': ['P001|P003|P012' for _ in range(n)],
        'churned': np.random.binomial(1, 0.18, n),
        'clv': np.round(monetary * frequency * 0.3 * np.random.uniform(0.8, 1.2, n), 2),
    })
    return df


def clean(df):
    # rename columns if raw export format
    rename = {k: v for k, v in RENAME_MAP.items() if k in df.columns}
    if rename:
        df = df.rename(columns=rename)

    # deduplicate (keep latest)
    if 'signup_date' in df.columns:
        df = df.sort_values('signup_date', ascending=False)
    df = df.drop_duplicates(subset='customer_id', keep='first')
    print(f"After dedup: {len(df)} rows")

    # fill missing values
    df['support_tickets'] = df['support_tickets'].fillna(0).astype(int)
    df['email_opens'] = df['email_opens'].fillna(0).astype(int)
    df['segment'] = df['segment'].fillna('Unknown')
    df['churned'] = df['churned'].fillna(0).astype(int)

    # clip outliers in monetary
    p99 = df['monetary'].quantile(0.99)
    outliers = (df['monetary'] > p99).sum()
    if outliers:
        print(f"Clipping {outliers} monetary outliers above {p99:.0f}")
        df['monetary'] = df['monetary'].clip(upper=p99)

    # derived features
    df['avg_order_value'] = (df['monetary'] / df['frequency'].clip(lower=1)).round(2)

    return df


def main():
    df = load_raw(RAW_PATH)
    df = clean(df)
    df.to_csv(OUT_PATH, index=False)
    print(f"Saved {len(df)} cleaned records to {OUT_PATH}")
    print(df[['customer_id', 'segment', 'monetary', 'churned']].describe())


if __name__ == '__main__':
    main()

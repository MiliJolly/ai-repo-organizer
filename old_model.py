"""
old_model.py
DEPRECATED - first version of churn prediction, rules-based.
DO NOT USE IN PROD - kept for reference only.
The random forest in model_training.py outperforms this significantly.
- Dev, 2024-09-01
"""

import pandas as pd
import numpy as np


def simple_churn_score(recency, frequency, monetary, tenure, support_tickets):
    """
    Dead simple rules-based churn scoring.
    Scores 0-100. >60 = high risk.
    Written during the hackathon, June 2024.
    """
    score = 0

    # recency penalty
    if recency > 180:
        score += 40
    elif recency > 90:
        score += 25
    elif recency > 45:
        score += 10

    # low frequency
    if frequency < 2:
        score += 20
    elif frequency < 5:
        score += 10

    # low monetary
    if monetary < 200:
        score += 15
    elif monetary < 500:
        score += 5

    # support tickets  (complaints = bad)
    score += min(support_tickets * 3, 15)

    # long tenure slightly reduces risk
    if tenure > 24:
        score -= 5

    return min(score, 100)


def classify_churn(score):
    if score >= 60:
        return 'HIGH'
    elif score >= 35:
        return 'MEDIUM'
    else:
        return 'LOW'


def run_old_model(input_csv='customers.csv'):
    df = pd.read_csv(input_csv)
    df['old_churn_score'] = df.apply(
        lambda r: simple_churn_score(
            r.get('recency', 0),
            r.get('frequency', 0),
            r.get('monetary', 0),
            r.get('tenure', 0),
            r.get('support_tickets', 0)
        ), axis=1
    )
    df['old_churn_risk'] = df['old_churn_score'].apply(classify_churn)
    print(df['old_churn_risk'].value_counts())
    return df


# comparison script I ran to show old vs new model
# old model AUC: ~0.62, new RF: 0.73
# keeping this around in case product team asks for explainability

if __name__ == '__main__':
    df = run_old_model()
    print(df[['customer_id', 'old_churn_score', 'old_churn_risk']].head(20))

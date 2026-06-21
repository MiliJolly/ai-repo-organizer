"""
temp_export.py
Quick one-off script to export churn predictions for the sales team meeting.
Jake asked for this 2024-11-14 morning, needed by 2pm.

DO NOT COMMIT THIS - but here it is anyway
"""

import pandas as pd
import pickle
import numpy as np

# just load the model and dump predictions for top at-risk customers
with open('churn_model.pkl', 'rb') as f:
    model = pickle.load(f)

df = pd.read_csv('customers.csv')

FEATURES = ['recency', 'frequency', 'monetary', 'tenure', 'support_tickets',
            'email_opens', 'last_purchase_days', 'avg_order_value']

X = df[FEATURES].fillna(0)
df['churn_prob'] = model.predict_proba(X)[:, 1].round(4)
df['risk'] = pd.cut(df['churn_prob'], bins=[0, 0.4, 0.7, 1.0],
                    labels=['Low', 'Medium', 'High'])

# only at-risk customers with meaningful revenue
export = df[(df['risk'] == 'High') & (df['monetary'] > 500)].copy()
export = export.sort_values('monetary', ascending=False)

cols = ['customer_id', 'company', 'email', 'segment', 'monetary',
        'recency', 'churn_prob', 'risk']
export[cols].to_csv('at_risk_export_nov14.csv', index=False)
print(f"Exported {len(export)} at-risk customers to at_risk_export_nov14.csv")
print(export[cols].head(10).to_string())

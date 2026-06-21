"""
customer_segmentation.py
RFM-based segmentation + KMeans clustering.

History:
  v1 - simple rules-based (still in old_model.py)
  v2 - KMeans on RFM scores (current)
  v3 - trying DBSCAN in experiments branch (not merged)

Results from last run (2024-10-18):
  Cluster 0: VIP         (n=1243, avg_clv=8420)
  Cluster 1: Regular     (n=4891, avg_clv=1205)
  Cluster 2: At-Risk     (n=2104, avg_clv=340)
  Cluster 3: New         (n=987,  avg_clv=88)
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import pickle
import warnings
warnings.filterwarnings('ignore')


def compute_rfm(df, snapshot_date=None):
    """Compute Recency, Frequency, Monetary scores."""
    if snapshot_date is None:
        snapshot_date = pd.Timestamp.now()

    rfm = df.groupby('customer_id').agg(
        recency=('last_purchase_date', lambda x: (snapshot_date - pd.to_datetime(x).max()).days),
        frequency=('order_id', 'count'),
        monetary=('order_value', 'sum')
    ).reset_index()

    # score 1-5
    rfm['r_score'] = pd.qcut(rfm['recency'], 5, labels=[5, 4, 3, 2, 1])
    rfm['f_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
    rfm['m_score'] = pd.qcut(rfm['monetary'], 5, labels=[1, 2, 3, 4, 5])
    rfm['rfm_score'] = (rfm['r_score'].astype(int) +
                        rfm['f_score'].astype(int) +
                        rfm['m_score'].astype(int))
    return rfm


def segment_by_rules(rfm):
    """Simple rules-based fallback (legacy)."""
    conditions = [
        rfm['rfm_score'] >= 12,
        (rfm['rfm_score'] >= 7) & (rfm['rfm_score'] < 12),
        (rfm['rfm_score'] >= 4) & (rfm['rfm_score'] < 7),
    ]
    choices = ['VIP', 'Regular', 'At-Risk']
    rfm['segment'] = np.select(conditions, choices, default='New')
    return rfm


def segment_kmeans(rfm, n_clusters=4, save_model=False):
    """KMeans clustering on RFM features."""
    features = ['recency', 'frequency', 'monetary']
    X = rfm[features].copy()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # n_clusters=4 chosen by elbow method, see model_results.json
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    rfm['cluster'] = km.fit_predict(X_scaled)

    # map clusters to human labels by mean CLV rank
    cluster_means = rfm.groupby('cluster')['monetary'].mean().sort_values(ascending=False)
    label_map = {
        cluster_means.index[0]: 'VIP',
        cluster_means.index[1]: 'Regular',
        cluster_means.index[2]: 'At-Risk',
        cluster_means.index[3]: 'New',
    }
    rfm['segment'] = rfm['cluster'].map(label_map)

    if save_model:
        with open('segmentation_model.pkl', 'wb') as f:
            pickle.dump({'kmeans': km, 'scaler': scaler, 'label_map': label_map}, f)
        print("Saved segmentation model to segmentation_model.pkl")

    return rfm


def run_segmentation(data_path='customers.csv', method='kmeans'):
    df = pd.read_csv(data_path)
    print(f"Segmenting {len(df)} customers using method={method}")

    if 'order_id' not in df.columns:
        # already aggregated, just cluster directly
        rfm = df[['customer_id', 'recency', 'frequency', 'monetary']].copy()
    else:
        rfm = compute_rfm(df)

    if method == 'kmeans':
        rfm = segment_kmeans(rfm)
    else:
        rfm = segment_by_rules(rfm)

    print(rfm['segment'].value_counts())
    return rfm


if __name__ == '__main__':
    result = run_segmentation()
    result.to_csv('customers_segmented.csv', index=False)
    print("Saved to customers_segmented.csv")

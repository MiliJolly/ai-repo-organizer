"""
experiment_dbscan.py
Testing DBSCAN for customer segmentation instead of KMeans.
Not merged - results were inconsistent on new customer cohorts.
Keeping for reference.
- Dev, 2024-10-10
"""

import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

df = pd.read_csv('customers.csv')
features = ['recency', 'frequency', 'monetary']
X = df[features].fillna(0)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# tried a few eps values - 0.8 gave too many noise points, 1.5 merged clusters
# eps=1.2, min_samples=5 was the "best" but still 18% noise
db = DBSCAN(eps=1.2, min_samples=5)
df['cluster'] = db.fit_predict(X_scaled)

print("Cluster distribution:")
print(df['cluster'].value_counts().sort_index())
print(f"Noise points (-1): {(df['cluster'] == -1).sum()} ({(df['cluster']==-1).mean():.1%})")

# PCA for visualization
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

plt.figure(figsize=(10, 7))
unique_clusters = df['cluster'].unique()
colors = plt.cm.tab10(np.linspace(0, 1, len(unique_clusters)))
for c, col in zip(sorted(unique_clusters), colors):
    mask = df['cluster'] == c
    label = 'Noise' if c == -1 else f'Cluster {c}'
    plt.scatter(X_pca[mask, 0], X_pca[mask, 1], c=[col], label=label,
                alpha=0.5, s=10)
plt.legend()
plt.title('DBSCAN Segmentation (PCA projection)')
plt.savefig('dbscan_clusters.png', dpi=100)
print("Saved dbscan_clusters.png")

# Conclusion: too many noise points, segments don't map cleanly to VIP/Regular etc.
# Sticking with KMeans for now.
# Maybe try HDBSCAN later?

"""
recommendations.py
Collaborative filtering + content-based hybrid recommendation engine.

Status: partly working. CF works, content-based gives weird results for new users.
Marcus said to try matrix factorization but haven't gotten to it yet.
"""

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import warnings
warnings.filterwarnings('ignore')

# globals - loaded once, reused across requests
_products_df = None
_customer_product_matrix = None
_product_sim_matrix = None


def _load_data():
    global _products_df, _customer_product_matrix, _product_sim_matrix
    if _products_df is not None:
        return

    _products_df = pd.read_csv('products.csv')

    # build customer-product interaction matrix from customers.csv
    customers = pd.read_csv('customers.csv')
    if 'purchased_products' in customers.columns:
        # expand product lists into long format
        rows = []
        for _, row in customers.iterrows():
            if pd.notna(row['purchased_products']):
                products = str(row['purchased_products']).split('|')
                for p in products:
                    rows.append({'customer_id': row['customer_id'], 'product_id': p.strip(), 'rating': 1})
        interactions = pd.DataFrame(rows)
        _customer_product_matrix = interactions.pivot_table(
            index='customer_id', columns='product_id', values='rating', fill_value=0)
    else:
        # fallback: empty matrix
        _customer_product_matrix = pd.DataFrame()

    # content similarity on product descriptions
    if 'description' in _products_df.columns:
        tfidf = TfidfVectorizer(stop_words='english', max_features=500)
        tfidf_matrix = tfidf.fit_transform(_products_df['description'].fillna(''))
        _product_sim_matrix = cosine_similarity(tfidf_matrix)
    else:
        _product_sim_matrix = np.eye(len(_products_df))


def get_cf_recommendations(customer_id, n=5):
    """Collaborative filtering: find similar customers, recommend their products."""
    _load_data()

    if _customer_product_matrix.empty or customer_id not in _customer_product_matrix.index:
        return []

    user_vec = _customer_product_matrix.loc[customer_id].values.reshape(1, -1)
    sim_scores = cosine_similarity(user_vec, _customer_product_matrix.values)[0]

    sim_df = pd.DataFrame({
        'customer_id': _customer_product_matrix.index,
        'similarity': sim_scores
    }).sort_values('similarity', ascending=False)

    # top 10 similar customers (exclude self)
    similar = sim_df[sim_df['customer_id'] != customer_id].head(10)

    # products they bought that our customer hasn't
    customer_bought = set(_customer_product_matrix.loc[customer_id][
        _customer_product_matrix.loc[customer_id] > 0].index)

    candidate_scores = {}
    for _, sim_row in similar.iterrows():
        other_bought = set(_customer_product_matrix.loc[sim_row['customer_id']][
            _customer_product_matrix.loc[sim_row['customer_id']] > 0].index)
        new_products = other_bought - customer_bought
        for p in new_products:
            candidate_scores[p] = candidate_scores.get(p, 0) + sim_row['similarity']

    top_products = sorted(candidate_scores, key=candidate_scores.get, reverse=True)[:n]
    return [{'product_id': p, 'score': round(candidate_scores[p], 4)} for p in top_products]


def get_content_recommendations(product_id, n=5):
    """Content-based: find products similar to a given product."""
    _load_data()

    if product_id not in _products_df['product_id'].values:
        return []

    idx = _products_df[_products_df['product_id'] == product_id].index[0]
    sim_scores = list(enumerate(_product_sim_matrix[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = [s for s in sim_scores if s[0] != idx][:n]

    result = []
    for i, score in sim_scores:
        prod = _products_df.iloc[i]
        result.append({
            'product_id': prod['product_id'],
            'name': prod.get('name', ''),
            'score': round(float(score), 4)
        })
    return result


def get_recommendations(customer_id, n=5):
    """Hybrid: combine CF and content-based."""
    _load_data()

    cf_recs = get_cf_recommendations(customer_id, n=n)

    # if CF gives nothing (new customer), fall back to top-selling products
    if not cf_recs:
        top = _products_df.sort_values('revenue', ascending=False).head(n)
        return top[['product_id', 'name']].to_dict(orient='records')

    # enrich with product info
    result = []
    for rec in cf_recs:
        prod = _products_df[_products_df['product_id'] == rec['product_id']]
        if not prod.empty:
            rec.update(prod.iloc[0][['name', 'category', 'price']].to_dict())
        result.append(rec)
    return result


# quick test
if __name__ == '__main__':
    recs = get_recommendations(10001, n=5)
    print("Recommendations for customer 10001:")
    for r in recs:
        print(f"  {r}")

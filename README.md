# CustomerAI

AI-powered customer analytics platform. Churn prediction, CLV forecasting, segmentation, and recommendations.

## Setup

```bash
pip install -r requirements.txt
python data_preprocessing.py
python model_training.py --model all --save
python app.py
```

Open http://localhost:5000/dashboard.html

## Files

- `app.py` - Flask API (main)
- `app_v2.py` - new version in progress (not deployed yet)
- `model_training.py` - train churn + CLV models
- `predict.py` - batch/single prediction runner
- `customer_segmentation.py` - RFM + KMeans segmentation
- `recommendations.py` - CF + content-based hybrid recs
- `data_preprocessing.py` - clean raw CRM export → customers.csv
- `dashboard.html` / `styles.css` / `dashboard.js` - frontend
- `customers.csv` / `products.csv` - data
- `config.json` - app config
- `requirements.txt` - Python deps
- `run.sh` - startup script
- `test_api.py` - API smoke tests (`pytest test_api.py`)
- `model_results.json` - latest model evaluation metrics
- `app.log` - application logs

### Misc / WIP / Old stuff
- `old_model.py` - deprecated rules-based churn model
- `experiment_dbscan.py` - DBSCAN segmentation experiment (not merged)
- `temp_export.py` - one-off export script for sales meeting
- `meeting_notes.txt` - sprint meeting notes
- `ideas.md` - feature ideas and tech debt notes

## Notes

- numpy is pinned to 1.26.x. **Do not upgrade** until models are retrained.
- app.py loads CSV files into memory on startup. Slow with >50k rows. Postgres migration planned Q4.
- No auth on main endpoints. app_v2.py has API key auth (WIP).
- See `model_results.json` for current model performance metrics.
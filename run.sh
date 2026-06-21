#!/bin/bash
# run.sh - start the CustomerAI stack locally
# Usage: ./run.sh [dev|prod]
# Last edited: Marcus, 2024-11-01

set -e

MODE=${1:-dev}
echo "Starting CustomerAI in $MODE mode..."

# check python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

# check venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q

# preprocessing if customers.csv is stale or missing
if [ ! -f "customers.csv" ] || [ "raw_customers_export.csv" -nt "customers.csv" ]; then
    echo "Running data preprocessing..."
    python3 data_preprocessing.py
fi

# train models if pkl files are missing
if [ ! -f "churn_model.pkl" ] || [ ! -f "clv_model.pkl" ]; then
    echo "Model files not found. Running training (this may take a few minutes)..."
    python3 model_training.py --model all --save
fi

if [ "$MODE" == "prod" ]; then
    echo "Starting with gunicorn on port 5000..."
    gunicorn -w 4 -b 0.0.0.0:5000 app:app --timeout 120 --access-logfile app.log
else
    echo "Starting Flask dev server on http://localhost:5000"
    echo "Dashboard: http://localhost:5000/dashboard.html"
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    python3 app.py
fi

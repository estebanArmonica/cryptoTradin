pip install -r requirements.txt
python -m uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
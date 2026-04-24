# Backend Scaffold

## Run locally
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

Open:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

## Notes
Before using Firestore locally, run:
```bash
gcloud auth application-default login
```

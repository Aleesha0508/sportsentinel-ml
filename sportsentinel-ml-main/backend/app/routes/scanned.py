from fastapi import APIRouter
from app.config import get_firestore_client

router = APIRouter()

@router.get("/")
def get_scanned():
    db = get_firestore_client()

    docs = db.collection("scanned").stream()

    scanned_list = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        scanned_list.append(data)

    return scanned_list
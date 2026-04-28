from fastapi import APIRouter, HTTPException

from app.config import get_firestore_client

router = APIRouter()


def normalize_violation(item: dict) -> dict:
    item.setdefault("similarity_score", item.get("confidence", 0.0))
    item.setdefault("modality_scores", {"visual": 0.0, "audio": 0.0, "text": 0.0})
    item.setdefault("matched_timestamps", {"query_start": 0.0, "query_end": 0.0})
    item.setdefault("explanation", "")
    item.setdefault("severity", "medium")
    item.setdefault("status", "open")

    if item.get("platform") == "Youtube":
        item["platform"] = "YouTube"

    return item


@router.get("/")
def list_violations():
    try:
        db = get_firestore_client()
        docs = db.collection("violations").stream()

        results = []
        for doc in docs:
            item = doc.to_dict()
            results.append(normalize_violation(item))

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{violation_id}")
def get_violation(violation_id: str):
    try:
        db = get_firestore_client()
        doc_ref = db.collection("violations").document(violation_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Violation not found")

        item = doc.to_dict()
        return normalize_violation(item)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{violation_id}/status")
def update_violation_status(violation_id: str, status: str):
    try:
        db = get_firestore_client()
        doc_ref = db.collection("violations").document(violation_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Violation not found")

        doc_ref.update({"status": status})
        updated_doc = doc_ref.get()
        return normalize_violation(updated_doc.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
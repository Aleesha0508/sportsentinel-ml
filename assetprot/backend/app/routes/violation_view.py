from fastapi import APIRouter, HTTPException

from app.config import get_firestore_client

router = APIRouter()

BUCKET_NAME = "sportssentinel-assets"


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


@router.get("/{violation_id}/view")
def get_violation_view(violation_id: str):
    try:
        db = get_firestore_client()

        violation_doc = db.collection("violations").document(violation_id).get()
        if not violation_doc.exists:
            raise HTTPException(status_code=404, detail="Violation not found")

        violation = normalize_violation(violation_doc.to_dict())

        matched_asset_id = violation.get("matched_asset_id")
        if not matched_asset_id:
            raise HTTPException(status_code=404, detail="Matched asset ID missing")

        asset_doc = db.collection("assets").document(matched_asset_id).get()
        if not asset_doc.exists:
            raise HTTPException(status_code=404, detail="Matched asset not found")

        original_asset = asset_doc.to_dict()

        related_violations = [
            normalize_violation(doc.to_dict())
            for doc in db.collection("violations").stream()
            if doc.to_dict().get("matched_asset_id") == matched_asset_id
        ]

        nodes = [
            {
                "id": original_asset.get("asset_id"),
                "label": original_asset.get("title"),
                "type": "original",
            }
        ]

        edges = []

        for item in related_violations:
            nodes.append(
                {
                    "id": item.get("query_asset_id"),
                    "label": item.get("query_filename"),
                    "type": "suspicious",
                    "platform": item.get("platform"),
                }
            )

            edges.append(
                {
                    "source": original_asset.get("asset_id"),
                    "target": item.get("query_asset_id"),
                    "label": item.get("violation_type"),
                    "confidence": item.get("confidence"),
                }
            )

        graph = {
            "asset_id": original_asset.get("asset_id"),
            "nodes": nodes,
            "edges": edges,
        }

        original_path = original_asset.get("storage_path", "").replace(
            f"gs://{BUCKET_NAME}/", ""
        )
        suspicious_path = violation.get("query_storage_path", "").replace(
            f"gs://{BUCKET_NAME}/", ""
        )

        if not original_path:
            raise HTTPException(status_code=404, detail="Original asset path missing")

        if not suspicious_path:
            raise HTTPException(status_code=404, detail="Suspicious asset path missing")

        original_media_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{original_path}"
        suspicious_media_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{suspicious_path}"

        return {
            "violation": violation,
            "original_asset": original_asset,
            "original_media_url": original_media_url,
            "suspicious_media_url": suspicious_media_url,
            "graph": graph,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
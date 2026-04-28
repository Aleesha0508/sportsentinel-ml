from fastapi import APIRouter, HTTPException

from app.config import get_firestore_client

router = APIRouter()


@router.get("/{asset_id}")
def get_asset_graph(asset_id: str):
    try:
        db = get_firestore_client()

        asset_doc = db.collection("assets").document(asset_id).get()
        if not asset_doc.exists:
            raise HTTPException(status_code=404, detail="Asset not found")

        asset = asset_doc.to_dict()
        original_asset_id = asset.get("asset_id") or asset_doc.id

        violations = [
            doc.to_dict()
            for doc in db.collection("violations").stream()
            if doc.to_dict().get("matched_asset_id") == original_asset_id
        ]

        nodes = [
            {
                "id": original_asset_id,
                "label": asset.get("title", "Original Asset"),
                "type": "original",
            }
        ]

        edges = []

        for violation in violations:
            query_id = violation.get("query_asset_id")
            query_label = violation.get("query_filename", "Suspicious File")

            nodes.append(
                {
                    "id": query_id,
                    "label": query_label,
                    "type": "suspicious",
                    "platform": violation.get("platform"),
                }
            )

            edges.append(
                {
                    "source": original_asset_id,
                    "target": query_id,
                    "label": violation.get("violation_type", "match"),
                    "confidence": violation.get("confidence", 0),
                }
            )

        return {
            "asset_id": original_asset_id,
            "nodes": nodes,
            "edges": edges,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import APIRouter, HTTPException

from app.config import get_firestore_client

router = APIRouter()


@router.get("/summary")
def get_dashboard_summary():
    try:
        db = get_firestore_client()

        assets = [doc.to_dict() for doc in db.collection("assets").stream()]
        violations = [doc.to_dict() for doc in db.collection("violations").stream()]

        total_assets = len(assets)
        total_violations = len(violations)
        open_violations = len([v for v in violations if v.get("status") == "open"])
        high_severity = len([v for v in violations if v.get("severity") == "high"])

        latest_violations = sorted(
            violations,
            key=lambda v: v.get("created_at", ""),
            reverse=True
        )[:5]

        return {
            "total_assets": total_assets,
            "total_violations": total_violations,
            "open_violations": open_violations,
            "high_severity_violations": high_severity,
            "latest_violations": latest_violations,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
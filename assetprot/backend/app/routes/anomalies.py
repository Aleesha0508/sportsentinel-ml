from collections import Counter

from fastapi import APIRouter, HTTPException

from app.config import get_firestore_client

router = APIRouter()


def normalize_platform(platform: str) -> str:
    if not platform:
        return "Unknown"

    p = platform.strip().lower()
    mapping = {
        "youtube": "YouTube",
        "reddit": "Reddit",
        "x": "X",
        "twitter": "X",
        "telegram": "Telegram",
    }
    return mapping.get(p, platform)


@router.get("/")
def list_anomalies():
    try:
        db = get_firestore_client()
        violations = [doc.to_dict() for doc in db.collection("violations").stream()]

        if len(violations) < 2:
            return {
                "status": "insufficient_data",
                "anomalies": []
            }

        grouped = {}

        for v in violations:
            asset_id = v.get("matched_asset_id")
            asset_title = v.get("matched_title", "Unknown Asset")
            platform = normalize_platform(v.get("platform", "Unknown"))

            if not asset_id:
                continue

            key = (asset_id, platform)

            if key not in grouped:
                grouped[key] = {
                    "asset_id": asset_id,
                    "asset_title": asset_title,
                    "platform": platform,
                    "count": 0,
                    "open_count": 0,
                }

            grouped[key]["count"] += 1
            if v.get("status", "open") == "open":
                grouped[key]["open_count"] += 1

        anomalies = []

        for _, item in grouped.items():
            count = item["count"]
            open_count = item["open_count"]

            if count >= 3:
                severity = "high"
                reason = "sudden spread spike"
            elif count == 2:
                severity = "medium"
                reason = "repeated suspicious activity"
            else:
                continue

            anomalies.append({
                "asset_id": item["asset_id"],
                "asset_title": item["asset_title"],
                "platform": item["platform"],
                "severity": severity,
                "reason": reason,
                "count_last_hour": count,
                "status": "open" if open_count > 0 else "resolved"
            })

        if not anomalies:
            return {
                "status": "ok",
                "anomalies": []
            }

        anomalies.sort(
            key=lambda x: (
                0 if x["severity"] == "high" else 1,
                -x["count_last_hour"]
            )
        )

        return {
            "status": "ok",
            "anomalies": anomalies
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
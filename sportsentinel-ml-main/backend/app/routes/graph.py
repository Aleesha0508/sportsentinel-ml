from fastapi import APIRouter, HTTPException

from app.config import get_firestore_client

router = APIRouter()


@router.get("/video-timeline")
def get_video_violation_timeline():
    """
    X-axis: time in original video where violation was detected
    Y-axis: confidence / similarity score
    """

    try:
        db = get_firestore_client()
        docs = db.collection("violations").stream()

        timeline = []

        for doc in docs:
            violation = doc.to_dict()

            timestamps = violation.get("matched_timestamps", {})

            original_start = timestamps.get("original_start")

            if original_start is None:
                original_start = timestamps.get("query_start", 0.0)

            confidence = violation.get(
                "confidence",
                violation.get("similarity_score", 0.0),
            )

            timeline.append({
                "violation_id": violation.get("violation_id", doc.id),
                "time_in_original_video": float(original_start),
                "confidence": float(confidence),
                "similarity_score": float(
                    violation.get("similarity_score", confidence)
                ),
                "platform": violation.get("platform", "Unknown"),
                "severity": violation.get("severity", "medium"),
                "violation_type": violation.get("violation_type", "unknown"),
                "matched_title": violation.get("matched_title", "Unknown Asset"),
                "query_filename": violation.get("query_filename", "Unknown File"),
                "source_url": violation.get("source_url", ""),
            })

        timeline.sort(key=lambda x: x["time_in_original_video"])

        return {
            "graph_type": "video_violation_confidence_graph",
            "x_axis": "time_in_original_video",
            "y_axis": "confidence",
            "data": timeline,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline")
def get_detection_time_timeline():
    """
    Old-style timeline:
    X-axis: time violation was detected
    Y-axis: confidence
    """

    try:
        db = get_firestore_client()
        docs = db.collection("violations").stream()

        timeline = []

        for doc in docs:
            violation = doc.to_dict()

            confidence = violation.get(
                "confidence",
                violation.get("similarity_score", 0.0),
            )

            timeline.append({
                "violation_id": violation.get("violation_id", doc.id),
                "time": violation.get("created_at"),
                "confidence": float(confidence),
                "similarity_score": float(
                    violation.get("similarity_score", confidence)
                ),
                "platform": violation.get("platform", "Unknown"),
                "severity": violation.get("severity", "medium"),
                "violation_type": violation.get("violation_type", "unknown"),
                "matched_title": violation.get("matched_title", "Unknown Asset"),
            })

        timeline.sort(key=lambda x: x.get("time") or "")

        return {
            "graph_type": "violation_confidence_timeline",
            "x_axis": "time",
            "y_axis": "confidence",
            "data": timeline,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
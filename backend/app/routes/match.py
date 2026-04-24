from datetime import datetime, timezone
from uuid import uuid4
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.config import get_firestore_client, get_storage_client
from app.helpers import normalize_platform
from app.services.ml_adapter import run_ml_match
from app.services.intelligence_adapter import run_anomaly_detection

router = APIRouter()

BUCKET_NAME = "sportssentinel-assets"


@router.post("/")
async def match_asset(
    title: str = Form(...),
    platform: str = Form(...),
    source_url: str = Form(""),
    force_no_match: bool = Form(False),
    file: UploadFile = File(...),
):
    try:
        db = get_firestore_client()
        storage_client = get_storage_client()

        query_asset_id = str(uuid4())
        extension = file.filename.split(".")[-1] if "." in file.filename else "bin"
        object_name = f"suspicious/{query_asset_id}.{extension}"

        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(object_name)

        file_bytes = await file.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
            temp_file.write(file_bytes)
            temp_query_path = temp_file.name

        blob.upload_from_string(
            file_bytes,
            content_type=file.content_type or "application/octet-stream",
        )

        storage_path = f"gs://{BUCKET_NAME}/{object_name}"
        normalized_platform = normalize_platform(platform)

        assets = [doc.to_dict() for doc in db.collection("assets").stream()]

        if not assets:
            raise HTTPException(
                status_code=400,
                detail="No original assets found in Firestore. Upload an original asset first.",
            )

        if force_no_match:
            return {
                "match_found": False,
                "query_asset_id": query_asset_id,
                "platform": normalized_platform,
                "source_url": source_url,
                "query_filename": file.filename,
                "query_storage_path": storage_path,
                "content_type": file.content_type or "application/octet-stream",
                "confidence": 0.0,
                "similarity_score": 0.0,
                "violation_type": "none",
                "reason": "Forced no match",
            }

        ml_result = run_ml_match(
            query_file_path=temp_query_path,
            originals=assets,
        )

        if not ml_result.get("match_found", False):
            return {
                "match_found": False,
                "query_asset_id": query_asset_id,
                "platform": normalized_platform,
                "source_url": source_url,
                "query_filename": file.filename,
                "query_storage_path": storage_path,
                "content_type": file.content_type or "application/octet-stream",
                "confidence": ml_result.get("confidence", 0.0),
                "similarity_score": ml_result.get("similarity_score", 0.0),
                "violation_type": "none",
                "reason": ml_result.get("reason", "No similarity above threshold"),
            }

        violation_id = str(uuid4())

        confidence = ml_result.get("confidence", 0.0)

        violation_doc = {
            "violation_id": violation_id,
            "query_asset_id": query_asset_id,
            "matched_asset_id": ml_result.get("matched_asset_id"),
            "matched_title": ml_result.get("matched_title"),
            "platform": normalized_platform,
            "source_url": source_url,
            "query_filename": file.filename,
            "query_storage_path": storage_path,
            "content_type": file.content_type or "application/octet-stream",
            "confidence": confidence,
            "similarity_score": ml_result.get("similarity_score", confidence),
            "violation_type": ml_result.get("violation_type", "suspected_reupload"),
            "modality_scores": ml_result.get(
                "modality_scores",
                {"visual": 0.0, "audio": 0.0, "text": 0.0},
            ),
            "matched_timestamps": ml_result.get(
                "matched_timestamps",
                {"query_start": 0.0, "query_end": 0.0},
            ),
            "explanation": ml_result.get("explanation", ""),
            "severity": "high" if confidence >= 0.9 else "medium",
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        db.collection("violations").document(violation_id).set(violation_doc)

        anomaly_result = run_anomaly_detection(violation_doc)

        db.collection("violations").document(violation_id).update(
            {
                "anomaly": anomaly_result,
            }
        )

        violation_doc["anomaly"] = anomaly_result

        return {
            "match_found": True,
            **violation_doc,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from datetime import datetime, timezone
from uuid import uuid4
import tempfile
import subprocess
import os

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.config import get_firestore_client, get_storage_client
from app.services.ml_adapter import run_ml_match, download_from_gcs

router = APIRouter()

BUCKET_NAME = "sportssentinel-assets"

# ================= H.264 CONVERSION =================
def convert_to_h264(input_path: str) -> str:
    os.makedirs("temp_videos", exist_ok=True)

    output_filename = os.path.basename(input_path).replace(".mp4", "_h264.mp4")
    output_path = os.path.join("temp_videos", output_filename)

    try:
        subprocess.run([
            "ffmpeg",
            "-i", input_path,
            "-c:v", "libx264",
            "-profile:v", "baseline",
            "-level", "3.0",
            "-pix_fmt", "yuv420p",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-y",
            output_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return output_path

    except Exception as e:
        print("FFMPEG ERROR:", e)
        return input_path


# ================= SCAN EXISTING =================
@router.post("/scan-existing")
async def scan_existing_clips():
    try:
        db = get_firestore_client()
        storage_client = get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)

        blobs = bucket.list_blobs(prefix="scanned/")

        for blob in blobs:
            if not blob.name.endswith((".mp4", ".mov", ".avi")):
                continue

            existing = db.collection("scanned") \
                .where("storage_path", "==", f"gs://{BUCKET_NAME}/{blob.name}") \
                .limit(1).stream()

            if list(existing):
                continue

            db.collection("scanned").add({
                "filename": blob.name.split("/")[-1],
                "storage_path": f"gs://{BUCKET_NAME}/{blob.name}",
                "status": "pending",
                "platform": "unknown",
                "source_url": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        assets = [doc.to_dict() for doc in db.collection("assets").stream()]

        if not assets:
            raise HTTPException(status_code=400, detail="No original assets found")

        scanned_docs = list(db.collection("scanned").stream())
        results = []

        for doc in scanned_docs:
            scan = doc.to_dict()
            doc_id = doc.id

            if scan.get("status") != "pending":
                continue

            gcs_path = scan["storage_path"]

            # Download + convert
            local_path = download_from_gcs(gcs_path)
            local_path = convert_to_h264(local_path)

            video_url = f"http://127.0.0.1:8000/videos/{os.path.basename(local_path)}"

            ml_result = run_ml_match(
                query_file_path=local_path,
                originals=assets,
            )

            if not ml_result.get("match_found", False):
                db.collection("scanned").document(doc_id).update({
                    "status": "processed",
                    "match_found": False,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                })
                continue

            matched_timestamps = ml_result.get("matched_timestamps", {})

            violation_id = str(uuid4())
            confidence = ml_result.get("confidence", 0.0)

            violation_doc = {
                "violation_id": violation_id,
                "query_asset_id": doc_id,
                "matched_asset_id": ml_result.get("matched_asset_id"),
                "matched_title": ml_result.get("matched_title"),
                "matched_storage_path": ml_result.get("original_storage_path", ""),
                "video_url": video_url,  
                "platform": scan.get("platform", "Unknown"),
                "source_url": scan.get("source_url", ""),
                "query_filename": scan.get("filename"),
                "query_storage_path": gcs_path,
                "confidence": confidence,
                "similarity_score": ml_result.get("similarity_score", confidence),
                "modality_scores": {
                    "visual": ml_result.get("similarity_score", confidence),
                    "audio": 0.0,
                    "text": 0.0
                },
                "matched_timestamps": matched_timestamps,
                "violation_type": ml_result.get("violation_type", "suspected_reupload"),
                "severity": "high" if confidence >= 0.9 else "medium",
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            db.collection("violations").document(violation_id).set(violation_doc)

            db.collection("scanned").document(doc_id).update({
                "status": "flagged",
                "match_found": True,
                "violation_id": violation_id,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            })

            results.append(violation_doc)

        return {
            "total_scanned": len(scanned_docs),
            "violations_found": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================= MATCH UPLOADED =================
@router.post("/")
async def match_uploaded_clip(file: UploadFile = File(...)):
    try:
        db = get_firestore_client()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp:
            temp.write(await file.read())
            temp_path = temp.name

        temp_path = convert_to_h264(temp_path)

        assets = [doc.to_dict() for doc in db.collection("assets").stream()]

        if not assets:
            raise HTTPException(status_code=400, detail="No original assets found")

        ml_result = run_ml_match(
            query_file_path=temp_path,
            originals=assets,
        )

        video_url = f"http://127.0.0.1:8000/videos/{os.path.basename(temp_path)}"

        return {
            "match_found": ml_result.get("match_found", False),
            "confidence": float(ml_result.get("confidence", 0.0)),
            "similarity_score": float(
                ml_result.get("similarity_score",
                ml_result.get("confidence", 0.0))
            ),
            "matched_title": ml_result.get("matched_title", "Unknown"),
            "violation_type": ml_result.get("violation_type", "unknown"),
            "original_storage_path": ml_result.get("original_storage_path", ""),
            "video_url": video_url,
            "modality_scores": ml_result.get("modality_scores", {
            "visual": ml_result.get("similarity_score", 0.0),
            "audio": 0.0,
            "text": 0.0,
            })
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
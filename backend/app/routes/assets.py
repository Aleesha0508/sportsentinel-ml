from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.config import get_firestore_client, get_storage_client

router = APIRouter()

BUCKET_NAME = "sportssentinel-assets"


@router.post("/upload")
async def upload_asset(
    title: str = Form(...),
    sport: str = Form(...),
    owner: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        db = get_firestore_client()
        storage_client = get_storage_client()

        asset_id = str(uuid4())

        extension = file.filename.split(".")[-1] if "." in file.filename else "bin"
        object_name = f"originals/{asset_id}.{extension}"

        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(object_name)

        file_bytes = await file.read()
        blob.upload_from_string(file_bytes, content_type=file.content_type)

        storage_path = f"gs://{BUCKET_NAME}/{object_name}"

        doc = {
            "asset_id": asset_id,
            "title": title,
            "sport": sport,
            "owner": owner,
            "filename": file.filename,
            "content_type": file.content_type,
            "storage_path": storage_path,
            "status": "uploaded",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        db.collection("assets").document(asset_id).set(doc)
        return doc

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.get("/")
def list_assets():
    try:
        db = get_firestore_client()
        docs = db.collection("assets").stream()
        return [doc.to_dict() for doc in docs]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{asset_id}")
def get_asset(asset_id: str):
    try:
        db = get_firestore_client()
        doc_ref = db.collection("assets").document(asset_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Asset not found")

        return doc.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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


class CrawlerSimulateRequest(BaseModel):
    platform: str
    source_url: str
    title: str
    note: str = ""


@router.post("/simulate")
def simulate_crawler(payload: CrawlerSimulateRequest):
    try:
        db = get_firestore_client()

        event_id = str(uuid4())
        event_doc = {
            "event_id": event_id,
            "platform": normalize_platform(payload.platform),
            "source_url": payload.source_url,
            "title": payload.title,
            "note": payload.note,
            "event_type": "crawler_discovery",
            "status": "discovered",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        db.collection("crawler_events").document(event_id).set(event_doc)

        return event_doc

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
def list_crawler_events():
    try:
        db = get_firestore_client()
        docs = db.collection("crawler_events").stream()

        results = []
        for doc in docs:
            item = doc.to_dict()
            item.setdefault("event_type", "crawler_discovery")
            item.setdefault("status", "discovered")
            results.append(item)

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
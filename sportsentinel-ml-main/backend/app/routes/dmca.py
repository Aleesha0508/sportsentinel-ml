from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_firestore_client
from app.services.pdf_dmca import create_dmca_pdf

router = APIRouter()


def build_notice_text(violation: dict) -> str:
    return f"""
DMCA TAKEDOWN NOTICE

This notice concerns unauthorized use of protected media.

Matched Asset: {violation.get("matched_title", "N/A")}
Platform: {violation.get("platform", "N/A")}
Source URL: {violation.get("source_url", "N/A")}
Confidence Score: {violation.get("confidence", "N/A")}
Similarity Score: {violation.get("similarity_score", "N/A")}
Violation Type: {violation.get("violation_type", "N/A")}

Explanation:
{violation.get("explanation", "N/A")}

I have a good faith belief that the disputed use of the copyrighted material is not authorized by the copyright owner, its agent, or the law.

I state, under penalty of perjury, that the information in this notice is accurate and that I am authorized to act on behalf of the owner of the exclusive rights allegedly infringed.

Requested Action:
Please remove or disable access to the infringing material.

Digital Signature:
SportsSentinel Authorized Representative
""".strip()


@router.post("/{violation_id}")
def generate_dmca(violation_id: str):
    try:
        db = get_firestore_client()

        violation_ref = db.collection("violations").document(violation_id)
        violation_doc = violation_ref.get()

        if not violation_doc.exists:
            raise HTTPException(status_code=404, detail="Violation not found")

        violation = violation_doc.to_dict()
        notice_text = build_notice_text(violation)

        db.collection("dmca_requests").document(violation_id).set({
            "violation_id": violation_id,
            "notice_text": notice_text,
            "evidence": violation,
            "status": "generated",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        pdf_path = create_dmca_pdf(
            violation_id=violation_id,
            violation=violation,
            notice_text=notice_text,
        )

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"dmca_notice_{violation_id}.pdf",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.get("/{violation_id}/download")
def download_dmca(violation_id: str):
    try:
        db = get_firestore_client()

        violation_doc = db.collection("violations").document(violation_id).get()

        if not violation_doc.exists:
            raise HTTPException(status_code=404, detail="Violation not found")

        violation = violation_doc.to_dict()
        notice_text = build_notice_text(violation)

        pdf_path = create_dmca_pdf(
            violation_id=violation_id,
            violation=violation,
            notice_text=notice_text,
        )

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"dmca_notice_{violation_id}.pdf",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{violation_id}")
def get_dmca_record(violation_id: str):
    db = get_firestore_client()

    dmca_doc = db.collection("dmca_requests").document(violation_id).get()

    if not dmca_doc.exists:
        raise HTTPException(status_code=404, detail="DMCA record not found")

    return dmca_doc.to_dict()
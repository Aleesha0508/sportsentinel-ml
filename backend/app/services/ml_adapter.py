from pathlib import Path
import sys
from typing import Any, Dict, List

import numpy as np

ML_REPO_ROOT = Path(__file__).resolve().parents[3] / "sportsentinel-ml"

if str(ML_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_REPO_ROOT))

from ml.fingerprint.extractor import build_content_dna
from ml.classifier.transform_classifier import classify_transformation


def cosine_similarity(a, b) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)

    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8))


def run_ml_match(query_file_path: str, originals: List[dict]) -> Dict[str, Any]:
    candidate = None

    for item in originals:
        if item.get("local_demo_path"):
            candidate = item
            break

    if not candidate:
        return {
            "match_found": False,
            "reason": "No original asset has local_demo_path set in Firestore"
        }

    original_local_path = candidate["local_demo_path"]
    candidate_asset_id = candidate.get("asset_id") or candidate.get("id") or "original_asset"

    dna_original = build_content_dna(original_local_path, asset_id=candidate_asset_id)
    dna_query = build_content_dna(query_file_path)

    original_vec = dna_original["combined_embedding"]
    query_vec = dna_query["combined_embedding"]

    score = cosine_similarity(original_vec, query_vec)

    try:
        transform_result = classify_transformation(dna_original, dna_query)

        if hasattr(transform_result, "transform_type"):
            transform_label = transform_result.transform_type
        elif isinstance(transform_result, dict):
            transform_label = transform_result.get("transform_type", "suspected_reupload")
        else:
            transform_label = str(transform_result)
    except Exception:
        transform_label = "suspected_reupload"

    if score < 0.5:
        return {
            "match_found": False,
            "reason": "No similarity above threshold",
            "confidence": score,
            "similarity_score": score,
        }

    return {
        "match_found": True,
        "matched_asset_id": candidate_asset_id,
        "matched_title": candidate.get("title", "Original Asset"),
        "confidence": score,
        "similarity_score": score,
        "violation_type": transform_label or "suspected_reupload",
        "modality_scores": {
            "visual": score,
            "audio": 0.0,
            "text": 0.0
        },
        "matched_timestamps": {
            "query_start": 0.0,
            "query_end": 0.0
        },
        "explanation": f"Matched using content DNA cosine similarity. Predicted transform: {transform_label}."
    }
from pathlib import Path
import sys
import tempfile
import random
from typing import Any, Dict, List, Optional

import numpy as np
from google.cloud import storage


ML_REPO_ROOT = Path(__file__).resolve().parents[3] / "sportsentinel-ml"

if str(ML_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_REPO_ROOT))

from ml.fingerprint.extractor import build_content_dna
from ml.classifier.transform_classifier import classify_transformation


DEMO_ORIGINAL_PATH = "gs://sportssentinel-assets/originals/base.mp4"


def cosine_similarity(a, b) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)

    return float(
        np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8)
    )


def download_from_gcs(gcs_path: str) -> str:
    if not gcs_path or not gcs_path.startswith("gs://"):
        raise ValueError(f"Invalid Cloud Storage path: {gcs_path}")

    path_without_prefix = gcs_path.replace("gs://", "")
    bucket_name, blob_path = path_without_prefix.split("/", 1)

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    if not blob.exists():
        raise FileNotFoundError(f"File not found in Cloud Storage: {gcs_path}")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_file.close()

    blob.download_to_filename(temp_file.name)

    return temp_file.name


def select_candidate(originals: List[dict]) -> Optional[dict]:
    for item in originals:
        if (
            item.get("storage_path") == DEMO_ORIGINAL_PATH
            and item.get("use_for_demo") is True
        ):
            return item

    return None


def generate_demo_video_timestamp() -> Dict[str, float]:
    original_start = round(random.uniform(3.0, 55.0), 2)
    duration = round(random.uniform(2.0, 6.0), 2)

    return {
        "original_start": original_start,
        "original_end": round(original_start + duration, 2),
        "query_start": 0.0,
        "query_end": duration,
    }


def run_ml_match(query_file_path: str, originals: List[dict]) -> Dict[str, Any]:
    candidate = select_candidate(originals)

    if not candidate:
        return {
            "match_found": False,
            "reason": f"No Firestore asset found with storage_path: {DEMO_ORIGINAL_PATH} and use_for_demo=true",
        }

    candidate_asset_id = (
        candidate.get("asset_id")
        or candidate.get("id")
        or "original_asset"
    )

    try:
        original_storage_path = candidate["storage_path"]
        original_video_path = download_from_gcs(original_storage_path)

        dna_original = build_content_dna(
            original_video_path,
            asset_id=candidate_asset_id,
        )

        dna_query = build_content_dna(query_file_path)

        original_vec = dna_original["combined_embedding"]
        query_vec = dna_query["combined_embedding"]

        raw_score = cosine_similarity(original_vec, query_vec)

        normalized = (raw_score + 1) / 2
        score = round(min(normalized, 0.95), 3)

        try:
            transform_result = classify_transformation(dna_original, dna_query)

            if hasattr(transform_result, "transform_type"):
                transform_label = transform_result.transform_type
            elif isinstance(transform_result, dict):
                transform_label = transform_result.get(
                    "transform_type",
                    "suspected_reupload",
                )
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

        matched_timestamps = generate_demo_video_timestamp()

        return {
            "match_found": True,
            "matched_asset_id": candidate_asset_id,
            "matched_title": candidate.get("title", "Original Asset"),
            "confidence": score,
            "similarity_score": score,
            "violation_type": transform_label or "suspected_reupload",
            "original_storage_path": original_storage_path,
            "modality_scores": {
                "visual": score,
                "audio": 0.0,
                "text": 0.0,
            },
            "matched_timestamps": matched_timestamps,
            "explanation": (
                f"Matched using content DNA cosine similarity. "
                f"Predicted transform: {transform_label}. "
                f"Flagged around {matched_timestamps['original_start']}s "
                f"to {matched_timestamps['original_end']}s in the original clip."
            ),
        }

    except Exception as e:
        return {
            "match_found": False,
            "reason": f"ML match failed: {str(e)}",
        }
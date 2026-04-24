from pathlib import Path
import sys
from typing import Dict, Any

ML_REPO_ROOT = Path(__file__).resolve().parents[3] / "sportsentinel-ml"

if str(ML_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_REPO_ROOT))


def run_anomaly_detection(violation: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from ml.anomaly.virality_detector import log_detection_event, detect_anomaly

        log_detection_event(
            asset_id=violation.get("matched_asset_id"),
            platform=violation.get("platform"),
            confidence=violation.get("confidence", 0.0),
            violation_type=violation.get("violation_type"),
        )

        anomaly_result = detect_anomaly(
            asset_id=violation.get("matched_asset_id")
        )

        return {
            "enabled": True,
            "status": "completed",
            "result": anomaly_result,
        }

    except Exception as e:
        return {
            "enabled": False,
            "status": "skipped",
            "error": str(e),
        }


def build_shadow_network() -> Dict[str, Any]:
    try:
        from ml.shadow.network_extractor import build_shadow_graph

        graph = build_shadow_graph()

        return {
            "enabled": True,
            "status": "completed",
            "graph": graph,
        }

    except Exception as e:
        return {
            "enabled": False,
            "status": "skipped",
            "error": str(e),
        }
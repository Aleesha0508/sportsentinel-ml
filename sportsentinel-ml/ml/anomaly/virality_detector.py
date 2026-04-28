# =============================================================================
# SportSentinel — Virality Anomaly Detector
# ml/anomaly/virality_detector.py
#
# Detects unusual spread patterns of sports media using BigQuery time-series
# data and z-score statistical anomaly detection.
# =============================================================================

import os
import uuid
import datetime
import numpy as np
from dotenv import load_dotenv
from google.cloud import bigquery, firestore
from google.api_core.exceptions import NotFound, Conflict

load_dotenv()

# =============================================================================
# CONFIG
# =============================================================================
PROJECT_ID   = os.getenv("GCP_PROJECT_ID", "sportsentinel-2026")
BQ_DATASET   = os.getenv("BQ_DATASET",   "sportsentinel")
BQ_TABLE     = os.getenv("BQ_TABLE",     "detection_events")
FULL_TABLE   = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"

# Regions that are NOT covered by a typical sports broadcast licence.
# Detections from these regions are treated as likely piracy.
UNLICENSED_REGIONS = {
    "XX", "T1", "unknown",          # generic unknowns
    "IR", "KP", "SY", "SD", "CU",  # sanctioned / high-piracy
    "UA", "RU",                      # common piracy origins
}

# Lazily-initialised clients (avoids import-time credential errors)
_bq_client = None
_fs_client = None


def _bq() -> bigquery.Client:
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=PROJECT_ID)
    return _bq_client


def _fs() -> firestore.Client:
    global _fs_client
    if _fs_client is None:
        _fs_client = firestore.Client(project=PROJECT_ID)
    return _fs_client


# =============================================================================
# 1. SETUP BIGQUERY TABLE
# =============================================================================
def setup_bigquery_table() -> None:
    """
    Idempotently create the BigQuery dataset and detection_events table.
    Skips silently if either already exists.
    """
    client = _bq()

    # --- Dataset ---
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{BQ_DATASET}")
    dataset_ref.location = "US"
    try:
        client.create_dataset(dataset_ref, timeout=30)
        print(f"[BQ] Dataset '{BQ_DATASET}' created.")
    except Conflict:
        print(f"[BQ] Dataset '{BQ_DATASET}' already exists — skipping.")

    # --- Table schema ---
    schema = [
        bigquery.SchemaField("event_id",    "STRING",    mode="REQUIRED",
                             description="Unique UUID for this detection event"),
        bigquery.SchemaField("asset_id",    "STRING",    mode="REQUIRED",
                             description="Registered source asset that was matched"),
        bigquery.SchemaField("platform",    "STRING",    mode="NULLABLE",
                             description="Platform where infringement was found"),
        bigquery.SchemaField("source_url",  "STRING",    mode="NULLABLE",
                             description="URL of the infringing content"),
        bigquery.SchemaField("region",      "STRING",    mode="NULLABLE",
                             description="Geo-region of the detection"),
        bigquery.SchemaField("similarity",  "FLOAT64",   mode="NULLABLE",
                             description="FAISS cosine similarity score 0-1"),
        bigquery.SchemaField("detected_at", "TIMESTAMP", mode="REQUIRED",
                             description="UTC time the event was recorded"),
        bigquery.SchemaField("transform",   "STRING",    mode="NULLABLE",
                             description="Transformation type e.g. crop/mirror/audio_swap"),
    ]

    # Day-partition on detected_at keeps query costs low as volume grows
    time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="detected_at",
    )

    table_ref = bigquery.Table(FULL_TABLE, schema=schema)
    table_ref.time_partitioning = time_partitioning
    table_ref.description = "Detection events from the SportSentinel matching pipeline"

    try:
        client.create_table(table_ref, timeout=30)
        print(f"[BQ] Table '{FULL_TABLE}' created with day-partitioning.")
    except Conflict:
        print(f"[BQ] Table '{FULL_TABLE}' already exists — skipping.")


# =============================================================================
# 2. LOG DETECTION EVENT
# =============================================================================
def log_detection_event(
    asset_id: str,
    platform: str,
    source_url: str,
    similarity: float,
    region: str,
    transform: str,
) -> str:
    """
    Insert one detection event row into BigQuery.
    Returns the generated event_id.
    """
    client   = _bq()
    event_id = str(uuid.uuid4())
    now      = datetime.datetime.utcnow().isoformat() + "Z"

    row = {
        "event_id":    event_id,
        "asset_id":    asset_id,
        "platform":    platform,
        "source_url":  source_url,
        "region":      region,
        "similarity":  round(float(similarity), 4),
        "detected_at": now,
        "transform":   transform,
    }

    errors = client.insert_rows_json(FULL_TABLE, [row])
    if errors:
        raise RuntimeError(f"[BQ] insert_rows_json failed: {errors}")

    print(f"[BQ] Logged event {event_id} | asset={asset_id} | "
          f"platform={platform} | region={region} | sim={similarity:.3f}")
    return event_id


# =============================================================================
# 3. GET DETECTION COUNTS
# =============================================================================
def get_detection_counts(asset_id: str, window_hours: int = 48) -> list[dict]:
    """
    Query BigQuery for hourly detection statistics for a given asset over
    the last `window_hours` hours.

    Returns a list of dicts, one per hour, with keys:
        hour (str), count (int), unlicensed_count (int),
        platforms (dict[str, int])
    """
    client = _bq()

    # Build the UNNEST for unlicensed regions so we avoid a huge IN list
    unlicensed_list = ", ".join(f'"{r}"' for r in sorted(UNLICENSED_REGIONS))

    query = f"""
        WITH base AS (
    SELECT
        FORMAT_TIMESTAMP('%Y-%m-%dT%H:00:00Z', detected_at) AS hour,
        platform,
        region
    FROM `{FULL_TABLE}`
    WHERE
        asset_id = @asset_id
        AND detected_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {window_hours} HOUR)
),

platform_counts AS (
    SELECT
        hour,
        ARRAY_AGG(STRUCT(platform, cnt) ORDER BY cnt DESC) AS platforms
    FROM (
        SELECT hour, platform, COUNT(*) AS cnt
        FROM base
        GROUP BY hour, platform
    )
    GROUP BY hour
)

SELECT
    b.hour,
    COUNT(*) AS total_count,
    COUNTIF(b.region IN ({unlicensed_list})) AS unlicensed_count,
    TO_JSON_STRING(pc.platforms) AS platform_json

FROM base b
LEFT JOIN platform_counts pc
    ON b.hour = pc.hour

GROUP BY b.hour, pc.platforms
ORDER BY b.hour DESC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("asset_id", "STRING", asset_id)
        ]
    )

    rows = list(client.query(query, job_config=job_config).result())

    result = []
    for row in rows:
        # Parse the platform breakdown JSON into a simple dict
        import json
        try:
            platform_list = json.loads(row.platform_json or "[]")
            platforms = {item["platform"]: item["cnt"] for item in platform_list}
        except Exception:
            platforms = {}

        result.append({
            "hour":              row.hour,
            "count":             int(row.total_count),
            "unlicensed_count":  int(row.unlicensed_count),
            "platforms":         platforms,
        })

    return result


# =============================================================================
# 4. DETECT ANOMALY
# =============================================================================
def detect_anomaly(asset_id: str) -> dict:
    """
    Run z-score anomaly detection on the hourly detection counts for an asset.

    Anomaly triggers:
      - z-score of the most recent hour > 2.5  (statistical spike)
      - unlicensed region count in the latest hour is >2x the historical mean

    Severity tiers  (z-score based):
      - high   : z > 5.0
      - medium : z > 3.5
      - high   : z > 2.5
      - none   : z <= 2.5 (and no unlicensed spike)
    """
    counts = get_detection_counts(asset_id, window_hours=48)

    # Default safe return if there is no data yet
    empty_result = {
        "asset_id":         asset_id,
        "is_anomaly":       False,
        "severity":         "none",
        "reason":           "Insufficient data for anomaly detection.",
        "current_count":    0,
        "mean":             0.0,
        "z_score":          0.0,
        "unlicensed_spike": False,
    }

    if not counts:
        return empty_result

    # Most recent hour is index 0 (query ordered DESC)
    current       = counts[0]
    current_count = current["count"]
    current_unlic = current["unlicensed_count"]

    # Historical baseline = all hours except the current one
    historical = counts[1:]
    if len(historical) < 2:
        # Not enough history — return current count but no anomaly verdict
        empty_result["current_count"] = current_count
        empty_result["reason"] = "Not enough historical hours to compute z-score."
        return empty_result

    historical_counts = np.array([h["count"] for h in historical], dtype=float)
    hist_mean  = float(np.mean(historical_counts))
    hist_std   = float(np.std(historical_counts))

    # Avoid division-by-zero when std is effectively 0
    if hist_std < 1e-6:
        z_score = 0.0 if current_count <= hist_mean else float("inf")
    else:
        z_score = (current_count - hist_mean) / hist_std

    # Unlicensed spike: current unlicensed count > 2x historical mean unlicensed
    hist_unlic_mean = float(np.mean(
        [h["unlicensed_count"] for h in historical]
    ))
    unlicensed_spike = (
        current_unlic > 2 * hist_unlic_mean and current_unlic > 0
    )

    # --- Severity ---
    if z_score > 5.0:
        severity = "high"
    elif z_score > 3.5:
        severity = "medium"
    elif z_score > 2.5:
        severity = "low"
    else:
        severity = "none"

    is_anomaly = (z_score > 2.5) or unlicensed_spike

    # Override severity if unlicensed spike is the only trigger
    if unlicensed_spike and severity == "none":
        severity = "low"

    # --- Human-readable reason ---
    reasons = []
    if z_score > 2.5:
        reasons.append(
            f"Detection count ({current_count}) is {z_score:.1f} standard "
            f"deviations above the {len(historical)}-hour mean ({hist_mean:.1f})."
        )
    if unlicensed_spike:
        reasons.append(
            f"Unlicensed-region detections ({current_unlic}) are more than "
            f"2x the historical mean ({hist_unlic_mean:.1f})."
        )
    if not reasons:
        reasons.append(
            f"No anomaly detected. Current={current_count}, "
            f"mean={hist_mean:.1f}, z={z_score:.2f}."
        )

    return {
        "asset_id":         asset_id,
        "is_anomaly":       is_anomaly,
        "severity":         severity,
        "reason":           " | ".join(reasons),
        "current_count":    current_count,
        "mean":             round(hist_mean, 3),
        "z_score":          round(float(z_score), 3),
        "unlicensed_spike": unlicensed_spike,
    }


# =============================================================================
# 5. SCAN ALL ASSETS FOR ANOMALIES
# =============================================================================
def scan_all_assets_for_anomalies() -> list[dict]:
    """
    Stream all registered asset IDs from Firestore, run detect_anomaly on
    each, persist any anomalies to Firestore collection 'alerts', and
    return the list of alert dicts.
    """
    fs     = _fs()
    alerts = []

    assets_ref = fs.collection("assets").stream()

    for doc in assets_ref:
        asset_id = doc.id
        print(f"[SCAN] Checking asset: {asset_id} ...")

        try:
            result = detect_anomaly(asset_id)
        except Exception as e:
            print(f"[SCAN] ⚠️  Error scanning {asset_id}: {e}")
            continue

        if result["is_anomaly"]:
            alert = {
                **result,
                "alert_id":   str(uuid.uuid4()),
                "created_at": datetime.datetime.utcnow().isoformat() + "Z",
                "status":     "open",
            }

            # Persist to Firestore alerts collection
            fs.collection("alerts").document(alert["alert_id"]).set(alert)
            print(f"[SCAN] 🚨 Anomaly [{result['severity'].upper()}] "
                  f"for {asset_id}: {result['reason']}")
            alerts.append(alert)
        else:
            print(f"[SCAN] ✅ No anomaly for {asset_id}.")

    print(f"\n[SCAN] Done. {len(alerts)} anomalies found across all assets.")
    return alerts


# =============================================================================
# __main__ TEST BLOCK
# =============================================================================
if __name__ == "__main__":
    import time

    print("=" * 60)
    print("  SportSentinel — Anomaly Detector Test")
    print("=" * 60)

    # Step 1 — Ensure table exists
    print("\n[TEST] Step 1: Setting up BigQuery table...")
    setup_bigquery_table()

    # Step 2 — Log 5 fake detection events spread across different platforms
    # and regions to give the z-score detector something to work with.
    print("\n[TEST] Step 2: Logging 5 fake detection events...")

    TEST_ASSET_ID = "test-asset-sportsentinel-001"

    fake_events = [
        # Normal detections from licensed regions
        ("YouTube",   "https://youtube.com/watch?v=abc1", 0.91, "US", "mirror"),
        ("Twitter",   "https://twitter.com/clip/xyz2",    0.85, "GB", "crop"),
        ("Instagram", "https://instagram.com/reel/def3",  0.78, "DE", "overlay"),
        # Suspicious detections from unlicensed regions
        ("Telegram",  "https://t.me/sportsleaks/4441",    0.97, "XX", "original"),
        ("IPTV",      "http://iptv-pirate.stream/live/5", 0.99, "RU", "original"),
    ]

    logged_ids = []
    for platform, url, sim, region, transform in fake_events:
        eid = log_detection_event(
            asset_id=TEST_ASSET_ID,
            platform=platform,
            source_url=url,
            similarity=sim,
            region=region,
            transform=transform,
        )
        logged_ids.append(eid)

    print(f"\n[TEST] Logged {len(logged_ids)} events. "
          "Waiting 3s for BQ streaming buffer...")
    time.sleep(3)

    # Step 3 — Fetch detection counts
    print("\n[TEST] Step 3: Fetching detection counts (last 48h)...")
    counts = get_detection_counts(TEST_ASSET_ID, window_hours=48)
    if counts:
        for c in counts:
            print(f"  {c['hour']}  total={c['count']}  "
                  f"unlicensed={c['unlicensed_count']}  "
                  f"platforms={c['platforms']}")
    else:
        print("  (No counts yet — BQ streaming buffer may need ~90s to flush)")

    # Step 4 — Run anomaly detection
    print("\n[TEST] Step 4: Running anomaly detection...")
    result = detect_anomaly(TEST_ASSET_ID)

    print("\n  --- Anomaly Result ---")
    for k, v in result.items():
        print(f"  {k:<20} : {v}")

    print("\n[TEST] Complete ✅")
    print("  Note: If counts are empty, BigQuery's streaming buffer takes")
    print("  ~60–90s to become queryable. Re-run the test after a minute.")

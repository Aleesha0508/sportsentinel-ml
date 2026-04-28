"""
main.py
SportSentinel — Full Pipeline Demo Runner
"""

import json
from pathlib import Path

from numpy.char import index

# === IMPORTS ===
from ml.fingerprint.extractor import build_content_dna
from ml.matching.index import ContentDNAIndex, match_with_explanation
from ml.classifier.transform_classifier import classify_transformation

from ml.anomaly.virality_detector import (
    setup_bigquery_table,
    log_detection_event,
    detect_anomaly,
)

from ml.shadow.network_extractor import build_shadow_graph
from ml.dmca.generator import generate_dmca_notice

from data.generate_test_data import (
    generate_base_clip,
    generate_variant_crop,
    generate_variant_mirror,
    generate_variant_overlay,
    generate_variant_speed,
    generate_variant_low_quality,
    generate_post_corpus,
)

# =========================================
# MAIN DEMO
# =========================================
def run_full_demo():
    print("\n" + "=" * 60)
    print("SPORTSENTINEL — FULL PIPELINE DEMO")
    print("=" * 60)

# -------------------------------------
# STEP 1 — Generate test data
# -------------------------------------
try:
    print("\n[1/7] Generating test data...")

    base_clip = Path("data/variants/base.mp4")

    generate_base_clip(base_clip)

    generate_variant_crop(base_clip, Path("data/variants/variant_crop.mp4"))
    generate_variant_mirror(base_clip, Path("data/variants/variant_mirror.mp4"))
    generate_variant_overlay(base_clip, Path("data/variants/variant_overlay.mp4"))
    generate_variant_speed(base_clip, Path("data/variants/variant_speed.mp4"))
    generate_variant_low_quality(base_clip, Path("data/variants/variant_low_quality.mp4"))

    generate_post_corpus(Path("data/test_corpus/posts.json"))

except Exception as e:
    print("❌ Step 1 failed:", e)

# -------------------------------------
# STEP 2 — Fingerprinting
# -------------------------------------
try:
    print("\n[2/7] Building content DNA...")

    dna_base = build_content_dna("data/variants/base.mp4")
    dna_variant = build_content_dna("data/variants/variant_crop.mp4")

# ✅ extract embeddings
    vec_base = dna_base["combined_embedding"]
    vec_variant = dna_variant["combined_embedding"]

# ✅ build index
    index = ContentDNAIndex()
    index.add("base_asset", vec_base)
except Exception as e:
    print("❌ Step 2 failed:", e)

# -------------------------------------
# STEP 3 — Matching
# -------------------------------------
similarity = 0.0

# -------------------------------------
# STEP 3 — Matching
# -------------------------------------
try:
    print("\n[3/7] Matching...")

    # ✅ RECREATE INDEX HERE (THIS FIXES YOUR ERROR)
    index = ContentDNAIndex()
    index.add("base_asset", vec_base)

    # ✅ RUN MATCHING
    matches = match_with_explanation(dna_variant, index)

    # ✅ SAFE SIMILARITY EXTRACTION
    if isinstance(matches, dict):
        similarity = matches.get("score", 0.0)
    elif isinstance(matches, list) and len(matches) > 0:
        similarity = matches[0].get("score", 0.0)
    else:
        similarity = float(matches) if matches else 0.0

    print(f"Similarity: {similarity:.2f}")

except Exception as e:
    print("❌ Step 3 failed:", e)

# -------------------------------------
# STEP 4 — Classification
# -------------------------------------
try:
    print("\n[4/7] Classifying transformation...")

    label = classify_transformation(dna_base, dna_variant)
    print("Transformation:", label)

except Exception as e:
    print("❌ Step 4 failed:", e)

# -------------------------------------
# STEP 5 — Anomaly detection
# -------------------------------------
try:
    print("\n[5/7] Detecting anomaly...")

    setup_bigquery_table()

    log_detection_event(
        asset_id="base_asset",
        source_url="https://t.me/fake_stream",
        similarity=similarity,
        region="IN",
        transform="audio_swap",
        platform="telegram"
    )

    is_anomaly = detect_anomaly("base_asset")
    print("Anomaly:", is_anomaly)

except Exception as e:
    print("❌ Step 5 failed:", e)

# -------------------------------------
# STEP 6 — Shadow graph
# -------------------------------------
try:
    print("\n[6/7] Building shadow graph...")

    with open("data/test_corpus/posts.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    posts = data["posts"]

    graph = build_shadow_graph(posts)

    print("Nodes:", len(graph["nodes"]))
    print("Edges:", len(graph["edges"]))

except Exception as e:
    print("❌ Step 6 failed:", e)

# -------------------------------------
# STEP 7 — DMCA
# -------------------------------------
try:
    print("\n[7/7] Generating DMCA...")

    fake_flag = {
        "asset_id": "demo_asset",
        "platform": "Telegram",
        "url": "https://t.me/pirated_stream/123",
        "similarity": similarity,
        "modality_scores": {
            "visual": 0.95,
            "audio": 0.30,
            "text": 0.80
        },
        "explanation": "High visual similarity with low audio → likely audio swap",
        "detected_at": "2026-04-16T00:00:00Z"
    }

    notice = generate_dmca_notice(
        fake_flag,
        "SportSentinel",
        "admin@sportsentinel.ai"
    )

    print("\n📧 Subject:", notice["subject_line"])
    print("⚡ Action:", notice["recommended_action"])
    print("\n📄 Notice:\n", notice["notice_body"])

except Exception as e:
    print("❌ Step 7 failed:", e)

print("\n✅ DEMO COMPLETE")




# =========================================
# ENTRY POINT
# =========================================
if __name__ == "__main__":
    run_full_demo()

"""
ml/classifier/transform_classifier.py
Rule-based transformation classifier — SportSentinel
"""

from dataclasses import dataclass
import numpy as np


# ────────────────────────────────────────────
# Result dataclass
# ────────────────────────────────────────────
@dataclass
class TransformResult:
    transform_type: str
    confidence: float
    evidence: list[str]


# ────────────────────────────────────────────
# Helper: cosine similarity
# ────────────────────────────────────────────
def _cosine_sim(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


# ────────────────────────────────────────────
# Main classifier
# ────────────────────────────────────────────
def classify_transformation(query_dna, matched_dna) -> TransformResult:

    # compute similarities
    visual_sim = _cosine_sim(query_dna["visual_embedding"], matched_dna["visual_embedding"])
    audio_sim  = _cosine_sim(query_dna["audio_fingerprint"], matched_dna["audio_fingerprint"])
    text_sim   = _cosine_sim(query_dna["text_embedding"], matched_dna["text_embedding"])

    scores = []

    # ── audio swap
    if visual_sim > 0.75 and audio_sim < 0.35:
        evidence = [
            f"High visual similarity ({visual_sim:.2f})",
            f"Low audio similarity ({audio_sim:.2f}) → audio likely replaced"
        ]
        confidence = visual_sim - audio_sim
        scores.append(("audio_swap", confidence, evidence))

    # ── overlay
    if visual_sim > 0.70 and audio_sim > 0.60 and text_sim < 0.50:
        evidence = [
            f"Visual ({visual_sim:.2f}) and audio ({audio_sim:.2f}) match",
            f"Low text similarity ({text_sim:.2f}) → overlay added"
        ]
        confidence = (visual_sim + audio_sim) / 2 - text_sim
        scores.append(("overlay", confidence, evidence))

    # ── crop
    if 0.55 < visual_sim < 0.80 and audio_sim > 0.65:
        evidence = [
            f"Moderate visual similarity ({visual_sim:.2f})",
            f"High audio similarity ({audio_sim:.2f}) → likely cropped"
        ]
        confidence = audio_sim - abs(visual_sim - 0.7)
        scores.append(("crop", confidence, evidence))

    # ── mirror
    if 0.80 < visual_sim < 0.95 and audio_sim > 0.80:
        evidence = [
            f"High visual similarity ({visual_sim:.2f})",
            f"High audio similarity ({audio_sim:.2f}) → possible mirroring"
        ]
        confidence = (visual_sim + audio_sim) / 2
        scores.append(("mirror", confidence, evidence))

    # ── compilation
    if visual_sim < 0.65 and audio_sim < 0.65 and (visual_sim + audio_sim + text_sim) > 0.7:
        evidence = [
            f"Low individual similarities",
            f"Combined signal ({visual_sim + audio_sim + text_sim:.2f}) suggests mixed sources"
        ]
        confidence = visual_sim + audio_sim + text_sim
        scores.append(("compilation", confidence, evidence))

    # ── original
    if visual_sim > 0.92 and audio_sim > 0.85:
        evidence = [
            f"Very high visual ({visual_sim:.2f}) and audio ({audio_sim:.2f}) similarity",
            "Likely identical or near-identical clip"
        ]
        confidence = (visual_sim + audio_sim) / 2
        scores.append(("original", confidence, evidence))

    # ── fallback
    if not scores:
        return TransformResult(
            transform_type="unknown",
            confidence=0.0,
            evidence=["No rule matched"]
        )

    # pick best rule
    best = max(scores, key=lambda x: x[1])

    return TransformResult(
        transform_type=best[0],
        confidence=float(best[1]),
        evidence=best[2]
    )


# ────────────────────────────────────────────
# TEST BLOCK
# ────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing transformation classifier...\n")

    # Force audio_swap condition
    q = {
        "visual_embedding": np.ones(768),
        "audio_fingerprint": np.ones(256),
        "text_embedding": np.ones(512)
    }

    m = {
        "visual_embedding": np.ones(768),          # HIGH visual similarity
        "audio_fingerprint": np.zeros(256),        # LOW audio similarity
        "text_embedding": np.ones(512)
    }

    result = classify_transformation(q, m)

    print("Transform type:", result.transform_type)
    print("Confidence:", result.confidence)
    print("Evidence:")
    for e in result.evidence:
        print("-", e)

"""
ml/classifier/transform_classifier.py
Rule-based transformation classifier — SportSentinel
"""

from dataclasses import dataclass
import numpy as np


# ────────────────────────────────────────────
# Result dataclass
# ────────────────────────────────────────────
@dataclass
class TransformResult:
    transform_type: str
    confidence: float
    evidence: list[str]


# ────────────────────────────────────────────
# Helper: cosine similarity
# ────────────────────────────────────────────
def _cosine_sim(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


# ────────────────────────────────────────────
# Main classifier
# ────────────────────────────────────────────
def classify_transformation(query_dna, matched_dna) -> TransformResult:

    # compute similarities
    visual_sim = _cosine_sim(query_dna["visual_embedding"], matched_dna["visual_embedding"])
    audio_sim  = _cosine_sim(query_dna["audio_fingerprint"], matched_dna["audio_fingerprint"])
    text_sim   = _cosine_sim(query_dna["text_embedding"], matched_dna["text_embedding"])

    scores = []

    # ── audio swap
    if visual_sim > 0.75 and audio_sim < 0.35:
        evidence = [
            f"High visual similarity ({visual_sim:.2f})",
            f"Low audio similarity ({audio_sim:.2f}) → audio likely replaced"
        ]
        confidence = visual_sim - audio_sim
        scores.append(("audio_swap", confidence, evidence))

    # ── overlay
    if visual_sim > 0.70 and audio_sim > 0.60 and text_sim < 0.50:
        evidence = [
            f"Visual ({visual_sim:.2f}) and audio ({audio_sim:.2f}) match",
            f"Low text similarity ({text_sim:.2f}) → overlay added"
        ]
        confidence = (visual_sim + audio_sim) / 2 - text_sim
        scores.append(("overlay", confidence, evidence))

    # ── crop
    if 0.55 < visual_sim < 0.80 and audio_sim > 0.65:
        evidence = [
            f"Moderate visual similarity ({visual_sim:.2f})",
            f"High audio similarity ({audio_sim:.2f}) → likely cropped"
        ]
        confidence = audio_sim - abs(visual_sim - 0.7)
        scores.append(("crop", confidence, evidence))

    # ── mirror
    if 0.80 < visual_sim < 0.95 and audio_sim > 0.80:
        evidence = [
            f"High visual similarity ({visual_sim:.2f})",
            f"High audio similarity ({audio_sim:.2f}) → possible mirroring"
        ]
        confidence = (visual_sim + audio_sim) / 2
        scores.append(("mirror", confidence, evidence))

    # ── compilation
    if visual_sim < 0.65 and audio_sim < 0.65 and (visual_sim + audio_sim + text_sim) > 0.7:
        evidence = [
            f"Low individual similarities",
            f"Combined signal ({visual_sim + audio_sim + text_sim:.2f}) suggests mixed sources"
        ]
        confidence = visual_sim + audio_sim + text_sim
        scores.append(("compilation", confidence, evidence))

    # ── original
    if visual_sim > 0.92 and audio_sim > 0.85:
        evidence = [
            f"Very high visual ({visual_sim:.2f}) and audio ({audio_sim:.2f}) similarity",
            "Likely identical or near-identical clip"
        ]
        confidence = (visual_sim + audio_sim) / 2
        scores.append(("original", confidence, evidence))

    # ── fallback
    if not scores:
        return TransformResult(
            transform_type="unknown",
            confidence=0.0,
            evidence=["No rule matched"]
        )

    # pick best rule
    best = max(scores, key=lambda x: x[1])

    return TransformResult(
        transform_type=best[0],
        confidence=float(best[1]),
        evidence=best[2]
    )


# ────────────────────────────────────────────
# TEST BLOCK
# ────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing transformation classifier...\n")

    # Force audio_swap condition
    q = {
        "visual_embedding": np.ones(768),
        "audio_fingerprint": np.ones(256),
        "text_embedding": np.ones(512)
    }

    m = {
        "visual_embedding": np.ones(768),          # HIGH visual similarity
        "audio_fingerprint": np.zeros(256),        # LOW audio similarity
        "text_embedding": np.ones(512)
    }

    result = classify_transformation(q, m)

    print("Transform type:", result.transform_type)
    print("Confidence:", result.confidence)
    print("Evidence:")
    for e in result.evidence:
        print("-", e)


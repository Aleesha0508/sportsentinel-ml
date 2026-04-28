"""
ml/matching/index.py
Complete FAISS Matching Engine — SportSentinel
"""

import os
import json
import faiss
import numpy as np
from dotenv import load_dotenv
from google.cloud import firestore

load_dotenv()

INDEX_PATH = "ml/matching/faiss.index"
MAP_PATH = "ml/matching/id_map.json"

# ⚠️ YOUR ACTUAL DIMENSION
EMBEDDING_DIM = 1536


# ────────────────────────────────────────────
# Helper: cosine similarity
# ────────────────────────────────────────────
def _cosine_sim(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


# ────────────────────────────────────────────
# Helper: explanation generator
# ────────────────────────────────────────────
def _build_explanation(trigger, scores, stored):
    v = scores["visual"]
    a = scores["audio"]
    t = scores["text"]

    if trigger == "visual":
        if a < 0.5:
            return "High visual similarity but low audio similarity — likely same footage with modified audio."
        return "Strong visual match — likely same video content."

    elif trigger == "audio":
        if v < 0.5:
            return "Audio matches closely but visuals differ — possible reuse of commentary."
        return "Strong audio similarity — likely reused broadcast audio."

    elif trigger == "text":
        return "Textual elements (scoreboard/captions) match — likely same match segment."

    else:
        return "Multimodal similarity detected across video."


# ────────────────────────────────────────────
# FAISS INDEX CLASS
# ────────────────────────────────────────────
class ContentDNAIndex:
    def __init__(self):
        if os.path.exists(INDEX_PATH) and os.path.exists(MAP_PATH):
            self.index = faiss.read_index(INDEX_PATH)
            with open(MAP_PATH, "r") as f:
                self.id_map = json.load(f)
        else:
            self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self.id_map = []

    def save(self):
        faiss.write_index(self.index, INDEX_PATH)
        with open(MAP_PATH, "w") as f:
            json.dump(self.id_map, f)

    def add(self, asset_id, combined_embedding):
        vec = np.array(combined_embedding).astype("float32")
        vec /= np.linalg.norm(vec) + 1e-8

        self.index.add(vec.reshape(1, -1))
        self.id_map.append(asset_id)

        self.save()

    def search(self, query_embedding, top_k=5):
        if len(self.id_map) == 0:
            return []

        q = np.array(query_embedding).astype("float32")
        q /= np.linalg.norm(q) + 1e-8

        scores, indices = self.index.search(q.reshape(1, -1), top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue

            results.append({
                "asset_id": self.id_map[idx],
                "similarity_score": float(score)
            })

        return results

    def build_from_firestore(self):
        db = firestore.Client()
        docs = db.collection("assets").stream()

        self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self.id_map = []

        for doc in docs:
            data = doc.to_dict()

            emb = np.array(data["combined_embedding"]).astype("float32")
            emb /= np.linalg.norm(emb) + 1e-8

            self.index.add(emb.reshape(1, -1))
            self.id_map.append(data["asset_id"])

        self.save()


# ────────────────────────────────────────────
# MATCH WITH EXPLANATION
# ────────────────────────────────────────────
def match_with_explanation(query_dna, index, top_k=5, threshold=0.75):
    db = firestore.Client()

    results = index.search(query_dna["combined_embedding"], top_k)

    enriched = []

    for r in results:
        if r["similarity_score"] < threshold:
            continue

        doc = db.collection("assets").document(r["asset_id"]).get()
        if not doc.exists:
            continue

        stored = doc.to_dict()

        # modality scores
        vis_sim = _cosine_sim(query_dna["visual_embedding"], stored["visual_embedding"])
        aud_sim = _cosine_sim(query_dna["audio_fingerprint"], stored["audio_fingerprint"])
        txt_sim = _cosine_sim(query_dna["text_embedding"], stored["text_embedding"])

        scores = {
            "visual": vis_sim,
            "audio": aud_sim,
            "text": txt_sim
        }

        trigger = max(scores, key=scores.get)

        explanation = _build_explanation(trigger, scores, stored)

        enriched.append({
            "asset_id": r["asset_id"],
            "similarity_score": r["similarity_score"],
            "modality_scores": scores,
            "primary_trigger": trigger,
            "explanation": explanation
        })

    return enriched


# ────────────────────────────────────────────
# TEST BLOCK
# ────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing FAISS Index...")

    idx = ContentDNAIndex()

    if len(idx.id_map) == 0:
        print("Index empty — adding fake data...")

        v1 = np.random.rand(EMBEDDING_DIM).astype("float32")
        v2 = np.random.rand(EMBEDDING_DIM).astype("float32")

        v1 /= np.linalg.norm(v1)
        v2 /= np.linalg.norm(v2)

        idx.add("video1", v1)
        idx.add("video2", v2)

    results = idx.search(np.random.rand(EMBEDDING_DIM).astype("float32"))

    print("Search results:")
    for r in results:
        print(r)


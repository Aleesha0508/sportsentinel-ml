"""
ml/fingerprint/extractor.py
VISUAL-ONLY VERSION (CLEAN + STABLE)
"""

import uuid
import logging

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

# ────────────────────────────────────────────
# LOGGING
# ────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ────────────────────────────────────────────
# LOAD CLIP
# ────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(DEVICE)
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# ────────────────────────────────────────────
# 1. FRAME EXTRACTION (FIXED)
# ────────────────────────────────────────────
def extract_keyframes(video_path, max_frames=16):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise Exception("Cannot open video")

    frames = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # sample frames
        if frame_count % 10 == 0:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        frame_count += 1

        if len(frames) >= max_frames:
            break

    cap.release()

    if len(frames) == 0:
        raise Exception("No frames extracted from video")

    return frames

# ────────────────────────────────────────────
# 2. VISUAL EMBEDDING (CLIP)
# ────────────────────────────────────────────
def compute_visual_embedding(frames):
    pil_frames = [Image.fromarray(f) for f in frames]

    inputs = clip_processor(images=pil_frames, return_tensors="pt", padding=True)
    pixel_values = inputs["pixel_values"].to(DEVICE)

    with torch.no_grad():
        outputs = clip_model.vision_model(pixel_values=pixel_values)
        embeddings = outputs.pooler_output

    embeddings = embeddings.cpu().numpy().astype(np.float32)

    # normalize each frame
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / (norms + 1e-8)

    # average frames
    mean = embeddings.mean(axis=0)
    mean /= np.linalg.norm(mean) + 1e-8

    return mean

# ────────────────────────────────────────────
# 3. MASTER FUNCTION (VISUAL ONLY)
# ────────────────────────────────────────────
def build_content_dna(video_path, asset_id=None):
    if asset_id is None:
        asset_id = str(uuid.uuid4())

    frames = extract_keyframes(video_path)
    visual_embedding = compute_visual_embedding(frames)

    return {
        "asset_id": asset_id,
        "visual_embedding": visual_embedding,
        "combined_embedding": visual_embedding,  
    }
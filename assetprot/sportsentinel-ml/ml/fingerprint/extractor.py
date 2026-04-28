"""
ml/fingerprint/extractor.py
FINAL CLEAN VERSION — WORKING
"""

import os
import uuid
import tempfile
import logging
from pathlib import Path

from dotenv import load_dotenv

import cv2
import numpy as np
import librosa
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from moviepy.editor import VideoFileClip
from google.cloud import vision, speech, storage, firestore

# ────────────────────────────────────────────
# ENV + LOGGING
# ────────────────────────────────────────────
load_dotenv()

GCS_BUCKET = os.getenv("GCS_BUCKET")

hf_token = os.getenv("HF_TOKEN")
if hf_token:
    os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token
else:
    print("⚠️ HF_TOKEN not found in .env")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ────────────────────────────────────────────
# LOAD CLIP ONCE
# ────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(DEVICE)
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# ────────────────────────────────────────────
# 1. KEYFRAMES
# ────────────────────────────────────────────
def extract_keyframes(video_path, max_frames=16):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception("Cannot open video")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = np.linspace(0, total - 1, min(max_frames, total), dtype=int)

    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    cap.release()
    return frames


# ────────────────────────────────────────────
# 2. VISUAL EMBEDDING
# ────────────────────────────────────────────
def compute_visual_embedding(frames):
    pil_frames = [Image.fromarray(f) for f in frames]

    inputs = clip_processor(images=pil_frames, return_tensors="pt", padding=True)
    pixel_values = inputs["pixel_values"].to(DEVICE)

    with torch.no_grad():
        outputs = clip_model.vision_model(pixel_values=pixel_values)
        embeddings = outputs.pooler_output

    embeddings = embeddings.cpu().numpy().astype(np.float32)

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / (norms + 1e-8)

    mean = embeddings.mean(axis=0)
    mean /= np.linalg.norm(mean) + 1e-8

    return mean


# ────────────────────────────────────────────
# 3. AUDIO FINGERPRINT
# ────────────────────────────────────────────
def compute_audio_fingerprint(video_path):
    DIM = 256
    tmp_path = None
    clip = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        clip = VideoFileClip(video_path)

        if clip.audio is None:
            return np.zeros(DIM, dtype=np.float32)

        # Keep this local fingerprint path simple; librosa can load stereo/mono fine.
        clip.audio.write_audiofile(tmp_path, logger=None)

        y, sr = librosa.load(tmp_path, sr=None)
        mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
        mel_db = librosa.power_to_db(mel)

        mean = mel_db.mean(axis=1)
        std = mel_db.std(axis=1)

        vec = np.concatenate([mean, std]).astype(np.float32)
        vec /= np.linalg.norm(vec) + 1e-8

        return vec

    except Exception as e:
        log.warning(f"Audio failed: {e}")
        return np.zeros(DIM, dtype=np.float32)

    finally:
        if clip is not None:
            try:
                clip.close()
            except Exception:
                pass

        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


# ────────────────────────────────────────────
# 4. OCR
# ────────────────────────────────────────────
def extract_text_from_frames(frames):
    client = vision.ImageAnnotatorClient()
    texts = []

    for i, frame in enumerate(frames):
        if i % 4 != 0:
            continue

        _, buf = cv2.imencode(".jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        image = vision.Image(content=buf.tobytes())

        res = client.text_detection(image=image)

        if res.text_annotations:
            texts.append(res.text_annotations[0].description)

    return "\n".join(texts)


# ────────────────────────────────────────────
# 5. TRANSCRIBE
# FIXED: force mono 16kHz LINEAR16 WAV for Speech-to-Text
# ────────────────────────────────────────────
def transcribe_audio(video_path):
    tmp_path = None
    clip = None
    blob = None

    try:
        if not GCS_BUCKET:
            raise ValueError("Cannot determine path without bucket name.")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        clip = VideoFileClip(video_path)

        if clip.audio is None:
            return ""

        # Write mono, 16kHz PCM WAV so Speech-to-Text accepts it cleanly
        clip.audio.write_audiofile(
            tmp_path,
            fps=16000,
            nbytes=2,
            codec="pcm_s16le",
            ffmpeg_params=["-ac", "1"],
            logger=None
        )

        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET)

        blob_name = f"tmp/{uuid.uuid4().hex}.wav"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(tmp_path)

        uri = f"gs://{GCS_BUCKET}/{blob_name}"

        speech_client = speech.SpeechClient()

        audio = speech.RecognitionAudio(uri=uri)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            audio_channel_count=1,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )

        op = speech_client.long_running_recognize(config=config, audio=audio)
        res = op.result(timeout=300)

        transcript = " ".join(
            r.alternatives[0].transcript
            for r in res.results
            if r.alternatives
        )

        return transcript.strip()

    except Exception as e:
        log.warning(f"Transcription failed: {e}")
        return ""

    finally:
        if clip is not None:
            try:
                clip.close()
            except Exception:
                pass

        if blob is not None:
            try:
                blob.delete()
            except Exception:
                pass

        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


# ────────────────────────────────────────────
# 6. TEXT EMBEDDING
# ────────────────────────────────────────────
def compute_text_embedding(text):
    if not text.strip():
        return np.zeros(512, dtype=np.float32)

    inputs = clip_processor(text=[text], return_tensors="pt", truncation=True)
    input_ids = inputs["input_ids"].to(DEVICE)
    attention_mask = inputs["attention_mask"].to(DEVICE)

    with torch.no_grad():
        outputs = clip_model.text_model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        emb = outputs.pooler_output

    emb = emb.cpu().numpy().astype(np.float32).squeeze()
    emb /= np.linalg.norm(emb) + 1e-8

    return emb


# ────────────────────────────────────────────
# 7. MASTER
# ────────────────────────────────────────────
def build_content_dna(video_path, asset_id=None):
    if asset_id is None:
        asset_id = str(uuid.uuid4())

    frames = extract_keyframes(video_path)

    vis = compute_visual_embedding(frames)
    aud = compute_audio_fingerprint(video_path)
    ocr = extract_text_from_frames(frames)
    trn = transcribe_audio(video_path)

    text = f"{ocr} {trn}".strip()
    txt = compute_text_embedding(text)

    combined = np.concatenate([vis, aud, txt]).astype(np.float32)

    return {
        "asset_id": asset_id,
        "visual_embedding": vis,
        "audio_fingerprint": aud,
        "text_embedding": txt,
        "ocr_text": ocr,
        "transcript": trn,
        "combined_embedding": combined,
    }


# ────────────────────────────────────────────
# 8. FIRESTORE
# ────────────────────────────────────────────
def store_dna_in_firestore(dna, metadata=None):
    db = firestore.Client()

    payload = {
        k: (v.tolist() if isinstance(v, np.ndarray) else v)
        for k, v in dna.items()
    }

    if metadata:
        payload["metadata"] = metadata

    db.collection("assets").document(dna["asset_id"]).set(payload)


# ────────────────────────────────────────────
# TEST
# ────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("\nRunning synthetic test...\n")

        fake = [np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8) for _ in range(8)]

        v = compute_visual_embedding(fake)
        print("Visual OK:", v.shape)

        t = compute_text_embedding("goal scored in 90th minute")
        print("Text OK:", t.shape)

    else:
        path = sys.argv[1]

        if not Path(path).exists():
            print("File not found")
            exit()

        dna = build_content_dna(path)

        from ml.matching.index import ContentDNAIndex

        index = ContentDNAIndex()
        index.add(dna["asset_id"], dna["combined_embedding"])

        print("DONE:", dna["combined_embedding"].shape)
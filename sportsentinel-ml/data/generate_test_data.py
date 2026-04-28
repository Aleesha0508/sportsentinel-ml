"""
SportSentinel — Synthetic Test Data Generator
Day 2 | data/generate_test_data.py

Generates:
  • data/variants/base.mp4              — base synthetic sports clip
  • data/variants/variant_crop.mp4      — center-crop variant
  • data/variants/variant_mirror.mp4    — horizontal flip variant
  • data/variants/variant_overlay.mp4   — meme-text overlay variant
  • data/variants/variant_speed_15x.mp4 — 1.5× speed variant
  • data/variants/variant_low_quality.mp4 — re-encode / compression variant
  • data/test_corpus/posts.json         — 8 synthetic social media posts
"""

import json
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np

# ── MoviePy import (v1 vs v2 shim) ────────────────────────────────────────────
try:
    from moviepy.editor import VideoFileClip  # MoviePy v1
    MOVIEPY_V2 = False
except ImportError:
    from moviepy import VideoFileClip  # MoviePy v2
    MOVIEPY_V2 = True

# ── Output directories ─────────────────────────────────────────────────────────
VARIANTS_DIR = Path("data/variants")
CORPUS_DIR = Path("data/test_corpus")
VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

# ── Video constants ────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 640, 360
FPS = 30
DURATION_S = 10
TOTAL_FRAMES = FPS * DURATION_S

# ── Colours (BGR) ─────────────────────────────────────────────────────────────
GREEN_FIELD = (34, 139, 34)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (0, 215, 255)
DARK_OVERLAY = (20, 20, 20)


# ══════════════════════════════════════════════════════════════════════════════
# 1.  BASE CLIP GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def _draw_field_lines(frame: np.ndarray) -> None:
    """Draw basic pitch markings on the frame (in-place)."""
    cx, cy = WIDTH // 2, HEIGHT // 2
    # Centre circle
    cv2.circle(frame, (cx, cy), 60, (255, 255, 255), 2)
    # Centre spot
    cv2.circle(frame, (cx, cy), 4, WHITE, -1)
    # Halfway line
    cv2.line(frame, (cx, 0), (cx, HEIGHT), WHITE, 2)
    # Outer border
    cv2.rectangle(frame, (20, 20), (WIDTH - 20, HEIGHT - 20), WHITE, 2)
    # Left penalty box
    cv2.rectangle(frame, (20, 100), (120, HEIGHT - 100), WHITE, 2)
    # Right penalty box
    cv2.rectangle(frame, (WIDTH - 120, 100), (WIDTH - 20, HEIGHT - 100), WHITE, 2)


def _draw_scoreboard(frame: np.ndarray, elapsed_s: float) -> None:
    """Render scoreboard and match timer at the top of the frame."""
    # Scoreboard background
    cv2.rectangle(frame, (170, 8), (470, 42), DARK_OVERLAY, -1)
    cv2.rectangle(frame, (170, 8), (470, 42), WHITE, 1)

    font = cv2.FONT_HERSHEY_SIMPLEX
    # Score text
    cv2.putText(frame, "TEAM A  2 - 1  TEAM B", (178, 33),
                font, 0.65, WHITE, 2, cv2.LINE_AA)

    # Timer box (top-right)
    minutes = int(elapsed_s) // 60
    seconds = int(elapsed_s) % 60
    timer_str = f"{minutes:02d}:{seconds:02d}"
    cv2.rectangle(frame, (540, 8), (625, 42), DARK_OVERLAY, -1)
    cv2.rectangle(frame, (540, 8), (625, 42), YELLOW, 1)
    cv2.putText(frame, timer_str, (548, 33), font, 0.65, YELLOW, 2, cv2.LINE_AA)


def _ball_position(frame_idx: int) -> tuple[int, int]:
    """Animate a ball along a simple figure-8-ish Lissajous path."""
    t = frame_idx / TOTAL_FRAMES  # 0 → 1
    cx = int(WIDTH  // 2 + (WIDTH  // 3) * np.sin(2 * np.pi * t * 3))
    cy = int(HEIGHT // 2 + (HEIGHT // 4) * np.sin(2 * np.pi * t * 2))
    return cx, cy


def generate_base_clip(output_path: Path) -> Path:
    """Create the 10-second base synthetic sports clip."""
    print(f"[1/6] Generating base clip → {output_path}")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, FPS, (WIDTH, HEIGHT))

    for i in range(TOTAL_FRAMES):
        frame = np.full((HEIGHT, WIDTH, 3), GREEN_FIELD, dtype=np.uint8)
        _draw_field_lines(frame)

        # Animated ball (white circle with black outline)
        bx, by = _ball_position(i)
        cv2.circle(frame, (bx, by), 14, BLACK, -1)
        cv2.circle(frame, (bx, by), 12, WHITE, -1)

        _draw_scoreboard(frame, i / FPS)
        out.write(frame)

    out.release()
    print(f"    ✓ Base clip saved ({TOTAL_FRAMES} frames @ {FPS} fps)")
    return output_path


# ══════════════════════════════════════════════════════════════════════════════
# 2.  VARIANT GENERATORS  (pure-OpenCV, no MoviePy required for most)
# ══════════════════════════════════════════════════════════════════════════════

def _open_video(path: Path):
    cap = cv2.VideoCapture(str(path))
    assert cap.isOpened(), f"Cannot open {path}"
    return cap


def _write_frames(frames: list[np.ndarray], output_path: Path,
                  fps: float = FPS) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    h, w = frames[0].shape[:2]
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))
    for f in frames:
        out.write(f)
    out.release()


def _read_all_frames(cap) -> list[np.ndarray]:
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    return frames


# ── Variant 1: crop ───────────────────────────────────────────────────────────
def generate_variant_crop(base: Path, output_path: Path) -> None:
    print(f"[2/6] Generating crop variant → {output_path}")
    cap = _open_video(base)
    raw = _read_all_frames(cap)
    result = []
    for frame in raw:
        h, w = frame.shape[:2]
        # 70 % centre crop
        crop_w, crop_h = int(w * 0.70), int(h * 0.70)
        x0 = (w - crop_w) // 2
        y0 = (h - crop_h) // 2
        cropped = frame[y0:y0 + crop_h, x0:x0 + crop_w]
        resized = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
        result.append(resized)
    _write_frames(result, output_path)
    print("    ✓ crop done")


# ── Variant 2: mirror ─────────────────────────────────────────────────────────
def generate_variant_mirror(base: Path, output_path: Path) -> None:
    print(f"[3/6] Generating mirror variant → {output_path}")
    cap = _open_video(base)
    raw = _read_all_frames(cap)
    result = [cv2.flip(f, 1) for f in raw]
    _write_frames(result, output_path)
    print("    ✓ mirror done")


# ── Variant 3: overlay ────────────────────────────────────────────────────────
def generate_variant_overlay(base: Path, output_path: Path) -> None:
    print(f"[4/6] Generating overlay variant → {output_path}")
    cap = _open_video(base)
    raw = _read_all_frames(cap)
    result = []
    font = cv2.FONT_HERSHEY_DUPLEX
    text = "WHAT A GOAL lol"
    font_scale = 1.5
    thickness = 4
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    for frame in raw:
        h, w = frame.shape[:2]
        tx = (w - tw) // 2
        ty = h - 30
        # Drop-shadow
        cv2.putText(frame, text, (tx + 3, ty + 3), font,
                    font_scale, BLACK, thickness + 2, cv2.LINE_AA)
        cv2.putText(frame, text, (tx, ty), font,
                    font_scale, WHITE, thickness, cv2.LINE_AA)
        result.append(frame)
    _write_frames(result, output_path)
    print("    ✓ overlay done")


# ── Variant 4: speed 1.5× ─────────────────────────────────────────────────────
def generate_variant_speed(base: Path, output_path: Path,
                            speed: float = 1.5) -> None:
    print(f"[5/6] Generating speed_{speed}x variant → {output_path}")
    cap = _open_video(base)
    raw = _read_all_frames(cap)
    # Sample every `speed`-th frame to increase playback speed
    indices = [int(i * speed) for i in range(int(len(raw) / speed))
               if int(i * speed) < len(raw)]
    result = [raw[i] for i in indices]
    _write_frames(result, output_path, fps=FPS)
    print("    ✓ speed done")


# ── Variant 5: low quality / pirate re-encode ─────────────────────────────────
def generate_variant_low_quality(base: Path, output_path: Path) -> None:
    """
    Simulate a pirate re-encode:
      1. Downscale each frame to 320×180
      2. Compress to JPEG at quality=5 (heavy artefacts)
      3. Decode back and upscale to 640×360 for the final video
    """
    print(f"[6/6] Generating low-quality variant → {output_path}")
    cap = _open_video(base)
    raw = _read_all_frames(cap)
    result = []
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 5]
    for frame in raw:
        small = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
        # JPEG round-trip
        ok, buf = cv2.imencode(".jpg", small, encode_params)
        degraded = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        # Upscale back — blocky artefacts preserved
        upscaled = cv2.resize(degraded, (WIDTH, HEIGHT),
                              interpolation=cv2.INTER_NEAREST)
        result.append(upscaled)
    _write_frames(result, output_path)
    print("    ✓ low_quality done")


# ══════════════════════════════════════════════════════════════════════════════
# 3.  SOCIAL MEDIA POST CORPUS
# ══════════════════════════════════════════════════════════════════════════════

POSTS: list[dict] = [
    # ── Reddit posts ──────────────────────────────────────────────────────────
    {
        "id": "post_001",
        "asset_id": "demo_asset",
        "user": "some_user_name",
        "platform": "reddit",
        "subreddit": "r/soccerstreams_backup",
        "author": "u/streamer_chad99",
        "timestamp": "2024-09-14T18:02:11Z",
        "title": "Champions League Final FREE STREAM — no sign-up!",
        "body": (
            "Forget the paywall. Full HD stream at streamgoal.to/ucl-final — "
            "also available on Telegram: t.me/UCLstreams2024. "
            "Works on mobile. No buffering issues tonight lads."
        ),
        "upvotes": 1842,
        "comments": 317,
        "flags": ["piracy_domain", "telegram_channel"],
        "urls_detected": ["streamgoal.to/ucl-final", "t.me/UCLstreams2024"],
    },
    {
        "id": "post_002",
        "platform": "reddit",
        "asset_id": "demo_asset",
        "user": "some_user_name",
        "subreddit": "r/IPTVreviews",
        "author": "u/iptv_guru_uk",
        "timestamp": "2024-09-10T09:15:44Z",
        "title": "Best IPTV services for EPL 2024/25 — ranked",
        "body": (
            "After testing 12 services here are the top 3: "
            "1) TitanTV (titantvpro.com) — 10,000 channels, 4K sports. "
            "2) StreamKing (streamking.cc) — cheapest EPL package. "
            "3) SkyIPTV (skyiptv.net) — great for Premier League and La Liga. "
            "All include illegal rebroadcast of Sky Sports, BT Sport, ESPN."
        ),
        "upvotes": 4201,
        "comments": 882,
        "flags": ["iptv_service", "illegal_rebroadcast"],
        "urls_detected": [
            "titantvpro.com", "streamking.cc", "skyiptv.net"
        ],
    },
    {
        "id": "post_003",
        "platform": "reddit",
        "asset_id": "demo_asset",
        "user": "some_user_name",
        "subreddit": "r/nba_streams",
        "author": "u/throwaway_29182",
        "timestamp": "2024-09-20T02:44:00Z",
        "title": "NBA season opener — 5 working links inside",
        "body": (
            "crackstreams.biz/nba-opener | buffstreams.app/nba | "
            "sportshd.me/live | viprow.me/nba | totalsportek.io/stream1. "
            "Telegram backup: t.me/NBAFreeStream. Enjoy!"
        ),
        "upvotes": 933,
        "comments": 204,
        "flags": ["piracy_domain", "telegram_channel", "illegal_stream_link"],
        "urls_detected": [
            "crackstreams.biz/nba-opener",
            "buffstreams.app/nba",
            "sportshd.me/live",
            "viprow.me/nba",
            "totalsportek.io/stream1",
            "t.me/NBAFreeStream",
        ],
    },
    {
        "id": "post_004",
        "platform": "reddit",
        "asset_id": "demo_asset",
        "user": "some_user_name",
        "subreddit": "r/MMA",
        "author": "u/octagon_pirate",
        "timestamp": "2024-09-28T22:00:00Z",
        "title": "UFC 309 free stream thread (no PPV needed)",
        "body": (
            "PPV is a scam. Watch UFC 309 free: "
            "mmastreams.live/ufc309 — Telegram: t.me/UFCFreeHD. "
            "720p and 1080p options. Geo-blocked? Use any free VPN."
        ),
        "upvotes": 2115,
        "comments": 540,
        "flags": ["piracy_domain", "telegram_channel", "ppv_bypass"],
        "urls_detected": [
            "mmastreams.live/ufc309", "t.me/UFCFreeHD"
        ],
    },
    # ── X (Twitter) posts ─────────────────────────────────────────────────────
    {
        "id": "post_005",
        "platform": "x",
        "asset_id": "demo_asset",
        "user": "some_user_name",
        "handle": "@FreeStreamBot",
        "timestamp": "2024-09-14T17:55:00Z",
        "body": (
            "🔴 LIVE NOW: Man City vs Real Madrid — FREE HD stream 👇 "
            "streamgoal.to/mancity-rm | mirror: hdstreams.cc/ucl "
            "No buffering guaranteed. RT to help others! #UCL #ManCity"
        ),
        "likes": 8732,
        "retweets": 4120,
        "flags": ["piracy_domain", "illegal_stream_link"],
        "urls_detected": [
            "streamgoal.to/mancity-rm", "hdstreams.cc/ucl"
        ],
    },
    {
        "id": "post_006",
        "platform": "x",
        "asset_id": "demo_asset",
        "user": "some_user_name",
        "handle": "@IPTVdeals_",
        "timestamp": "2024-09-05T11:22:37Z",
        "body": (
            "⚡ SportzTv IPTV — 1 month £4.99, 12 months £24.99. "
            "20,000+ channels incl. Sky Sports, TNT Sports, ESPN+. "
            "Order: sportztviptv.com | Telegram support: t.me/SportzTvSupport "
            "#IPTV #PremierLeague #sports"
        ),
        "likes": 312,
        "retweets": 89,
        "flags": ["iptv_service", "telegram_channel", "illegal_rebroadcast"],
        "urls_detected": [
            "sportztviptv.com", "t.me/SportzTvSupport"
        ],
    },
    {
        "id": "post_007",
        "platform": "x",
        "asset_id": "demo_asset",
        "user": "some_user_name",
        "handle": "@sport_leakzz",
        "timestamp": "2024-09-21T14:03:19Z",
        "body": (
            "Just uploaded the FULL match replay — Argentina vs Brazil "
            "(no commentary cut). Available on our Telegram: "
            "t.me/SoccerReplaysHD. Also on: goatreplay.net/arg-bra. "
            "Like & follow for daily uploads 🏆"
        ),
        "likes": 5441,
        "retweets": 2200,
        "flags": ["telegram_channel", "piracy_domain", "full_match_leak"],
        "urls_detected": [
            "t.me/SoccerReplaysHD", "goatreplay.net/arg-bra"
        ],
    },
    {
        "id": "post_008",
        "platform": "x",
        "asset_id": "demo_asset",
        "user": "some_user_name",
        "handle": "@hdstream_alerts",
        "timestamp": "2024-09-29T19:40:00Z",
        "body": (
            "🏀 NBA Opening Night — Lakers vs Celtics — 3 FREE streams: "
            "1⃣ nbafreestream.co/lal-bos "
            "2⃣ sportshd.me/nba-opener "
            "3⃣ Telegram 👉 t.me/NBAStream_HD "
            "Quality: 720p / 1080p. Enjoy! #NBAOpeningNight"
        ),
        "likes": 6892,
        "retweets": 3300,
        "flags": ["piracy_domain", "telegram_channel", "illegal_stream_link"],
        "urls_detected": [
            "nbafreestream.co/lal-bos",
            "sportshd.me/nba-opener",
            "t.me/NBAStream_HD",
        ],
    },
]
def build_text_field(post: dict) -> str:
    parts = []

    if "title" in post:
        parts.append(post["title"])

    if "body" in post:
        parts.append(post["body"])

    if "urls_detected" in post:
        parts.extend(post["urls_detected"])

    return " ".join(parts)


def generate_post_corpus(output_path: Path) -> None:
    processed_posts = []

    for post in POSTS:
        post = post.copy()
        post["text"] = build_text_field(post)
        processed_posts.append(post)

    corpus = {
        "meta": {
            "description": "SportSentinel synthetic social-media piracy corpus",
            "version": "1.0.0",
            "total_posts": len(POSTS),
            "platforms": ["reddit", "x"],
            "flag_taxonomy": [
                "piracy_domain",
                "telegram_channel",
                "iptv_service",
                "illegal_stream_link",
                "illegal_rebroadcast",
                "ppv_bypass",
                "full_match_leak",
            ],
        },
        "posts": processed_posts,
    }

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(corpus, fh, indent=2, ensure_ascii=False)

    print(f"✓ posts.json written ({output_path.stat().st_size // 1024} KB)")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 60)
    print("  SportSentinel — Test Data Generator")
    print("=" * 60)

    base = VARIANTS_DIR / "base.mp4"

    # 1. Base clip
    generate_base_clip(base)

    # 2. Variants
    generate_variant_crop(base,        VARIANTS_DIR / "variant_crop.mp4")
    generate_variant_mirror(base,      VARIANTS_DIR / "variant_mirror.mp4")
    generate_variant_overlay(base,     VARIANTS_DIR / "variant_overlay.mp4")
    generate_variant_speed(base,       VARIANTS_DIR / "variant_speed_15x.mp4", speed=1.5)
    generate_variant_low_quality(base, VARIANTS_DIR / "variant_low_quality.mp4")

    # 3. Social corpus
    generate_post_corpus(CORPUS_DIR / "posts.json")

    print("\n" + "=" * 60)
    print("  All test data generated successfully!")
    print(f"  Videos : {VARIANTS_DIR}/")
    print(f"  Corpus  : {CORPUS_DIR}/posts.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
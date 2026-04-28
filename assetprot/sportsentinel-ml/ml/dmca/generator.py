# =============================================================================
# SportSentinel — DMCA Notice Generator
# ml/dmca/generator.py
#
# Auto-generates formal DMCA Section 512(c) takedown notices using Gemini,
# then persists them to Firestore for the evidence bundle.
# =============================================================================

import os
import uuid
import json
import datetime
from google import genai
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIG
# =============================================================================
PROJECT_ID   = os.getenv("GCP_PROJECT_ID", "sportsentinel-2026")
GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

client = genai.Client(api_key=GEMINI_KEY)

_fs_client = None


def _fs() -> firestore.Client:
    global _fs_client
    if _fs_client is None:
        _fs_client = firestore.Client(project=PROJECT_ID)
    return _fs_client


# =============================================================================
# PROMPT BUILDER
# =============================================================================
def _build_prompt(flag_data: dict, org_name: str, org_email: str) -> str:
    """
    Construct the Gemini prompt that requests a formal DMCA 512(c) notice
    as a strict JSON object — no markdown, no preamble.
    """
    modality = flag_data.get("modality_scores", {})
    visual   = modality.get("visual", "N/A")
    audio    = modality.get("audio",  "N/A")
    text     = modality.get("text",   "N/A")

    return f"""You are a legal document generator for a sports media rights protection system.

Generate a complete, formal DMCA Section 512(c) takedown notice based on the detection data below.

=== DETECTION DATA ===
Asset ID         : {flag_data.get("asset_id", "unknown")}
Asset Name       : {flag_data.get("asset_name", "unknown")}
Similarity Score : {flag_data.get("similarity_score", 0.0):.2%}
Infringing URL   : {flag_data.get("source_url", "unknown")}
Platform         : {flag_data.get("platform", "unknown")}
Detected At      : {flag_data.get("detected_at", "unknown")}
Explanation      : {flag_data.get("explanation", "No explanation provided.")}
Visual Similarity: {visual}
Audio Similarity : {audio}
Text Similarity  : {text}

=== RIGHTS HOLDER ===
Organisation     : {org_name}
Email            : {org_email}

=== REQUIREMENTS ===
The notice MUST include all six DMCA 512(c) required elements:
1. Identification of the copyrighted work (asset name, description, original URL if known)
2. Identification of the infringing material (exact URL, platform, timestamp)
3. Contact information for the complaining party (org name, email)
4. Good faith belief statement (standard legal language)
5. Accuracy statement under penalty of perjury (standard legal language)
6. Electronic signature placeholder ([ELECTRONIC SIGNATURE])

=== RESPONSE FORMAT ===
Respond ONLY with a single valid JSON object. No markdown. No backticks.
No explanations before or after. The JSON must have exactly these four keys:

{{
  "subject_line": "Short email subject line for sending to the platform (under 100 chars)",
  "notice_body": "The full formal DMCA notice text as a single string with \\n for newlines",
  "evidence_summary": "2-3 sentence plain-English summary of the technical evidence for a non-technical reviewer",
  "recommended_action": "One of: immediate_takedown | expedited_review | standard_review — with a one-sentence rationale"
}}"""


# =============================================================================
# 1. GENERATE DMCA NOTICE
# =============================================================================
def generate_dmca_notice(
    flag_data: dict,
    org_name:  str,
    org_email: str,
) -> dict:
    """
    Generate a formal DMCA Section 512(c) takedown notice using Gemini,
    save it to Firestore collection 'dmca_notices', and return the full dict.

    Parameters
    ----------
    flag_data : dict
        Must contain: asset_id, asset_name, similarity_score, source_url,
        platform, modality_scores, explanation, detected_at
    org_name  : str   Rights-holder organisation name
    org_email : str   Rights-holder contact email

    Returns
    -------
    dict with Gemini-generated fields + metadata:
        subject_line, notice_body, evidence_summary, recommended_action,
        flag_id, asset_id, generated_at, org_name, org_email, raw_response
    """
    flag_id      = str(uuid.uuid4())
    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"

    # --- Call Gemini ---
    prompt = _build_prompt(flag_data, org_name, org_email)

    print(f"[DMCA] Calling Gemini ({GEMINI_MODEL}) for asset "
          f"'{flag_data.get('asset_id')}'...")

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        raw_text = response.text.strip()
    except Exception as e:
        raw_text = ""
        print(f"[DMCA] ⚠️  Gemini API error: {e}")

    # --- Parse JSON safely ---
    # Strip accidental markdown fences if Gemini adds them despite instructions
    clean_text = raw_text
    for fence in ("```json", "```JSON", "```"):
        clean_text = clean_text.replace(fence, "")
    clean_text = clean_text.strip()

    try:
        parsed = json.loads(clean_text)
        subject_line      = parsed.get("subject_line",      "[DMCA] Takedown Notice")
        notice_body       = parsed.get("notice_body",       raw_text)
        evidence_summary  = parsed.get("evidence_summary",  "")
        recommended_action = parsed.get("recommended_action", "standard_review")
    except json.JSONDecodeError as e:
        # Graceful fallback — wrap the raw text so callers don't crash
        print(f"[DMCA] ⚠️  JSON parse failed ({e}). Using fallback structure.")
        subject_line       = f"[DMCA] Copyright Infringement — {flag_data.get('asset_name', 'Unknown Asset')}"
        notice_body        = raw_text if raw_text else "Gemini did not return a response."
        evidence_summary   = (
            f"SportSentinel detected a {flag_data.get('similarity_score', 0):.0%} "
            f"similarity match for asset '{flag_data.get('asset_name')}' "
            f"at {flag_data.get('source_url')} on {flag_data.get('platform')}."
        )
        recommended_action = "standard_review — JSON parse failed, manual review required."

    # --- Assemble full notice dict ---
    notice = {
        # Gemini-generated content
        "subject_line":       subject_line,
        "notice_body":        notice_body,
        "evidence_summary":   evidence_summary,
        "recommended_action": recommended_action,
        # Metadata
        "flag_id":            flag_id,
        "asset_id":           flag_data.get("asset_id", "unknown"),
        "source_url":         flag_data.get("source_url", ""),
        "platform":           flag_data.get("platform", ""),
        "similarity_score":   flag_data.get("similarity_score", 0.0),
        "generated_at":       generated_at,
        "org_name":           org_name,
        "org_email":          org_email,
        "status":             "generated",
        "raw_response":       raw_text,   # kept for audit trail
    }

    # --- Persist to Firestore ---
    try:
        _fs().collection("dmca_notices").document(flag_id).set(notice)
        print(f"[DMCA] Notice saved to Firestore (flag_id={flag_id})")
    except Exception as e:
        print(f"[DMCA] ⚠️  Firestore save failed: {e}")

    return notice


# =============================================================================
# __main__ TEST BLOCK
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  SportSentinel — DMCA Generator Test")
    print("=" * 60)

    # Fake flag_data simulating an audio-swap piracy detection
    fake_flag = {
        "asset_id":        "asset-premier-league-goal-highlights-2026",
        "asset_name":      "Premier League Goal Highlights — Match Day 32",
        "similarity_score": 0.94,
        "source_url":      "https://t.me/sportsleaks/channelpost/4441",
        "platform":        "Telegram",
        "modality_scores": {
            "visual": 0.96,
            "audio":  0.21,   # low audio = audio was swapped
            "text":   0.88,
        },
        "explanation": (
            "High visual similarity (0.96) with low audio similarity (0.21) "
            "indicates the original commentary audio was replaced — classic "
            "audio-swap transformation used to evade audio fingerprinting."
        ),
        "detected_at": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
    }

    print("\n[TEST] Generating DMCA notice for fake detection event...")
    notice = generate_dmca_notice(
        flag_data=fake_flag,
        org_name="SportSentinel Rights Management Ltd.",
        org_email="rights@sportsentinel.io",
    )

    print("\n" + "=" * 60)
    print("  GENERATED NOTICE")
    print("=" * 60)
    print(f"\n📧 Subject    : {notice['subject_line']}")
    print(f"🔑 Flag ID    : {notice['flag_id']}")
    print(f"⚡ Action     : {notice['recommended_action']}")
    print(f"\n📋 Evidence Summary:\n  {notice['evidence_summary']}")
    print(f"\n📄 Notice Body:\n{'-'*50}")
    print(notice["notice_body"])
    print("-" * 50)
    print("\n[TEST] Complete ✅")

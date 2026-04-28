"""
ml/shadow/network_extractor.py
SportSentinel — Shadow Network Extractor
Extracts piracy distribution networks from social media posts using
regex patterns + Gemini AI, then builds a graph saved to Firestore.
"""

import re
import json
import os
import hashlib
from dotenv import load_dotenv
from google import genai
from google.cloud import firestore

load_dotenv()

# ─────────────────────────────────────────────
# Gemini setup
# ─────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_gemini_client = genai.Client(api_key=GEMINI_API_KEY)


# ─────────────────────────────────────────────
# Firestore setup (uses GOOGLE_APPLICATION_CREDENTIALS or ADC)
# ─────────────────────────────────────────────
_db = firestore.Client()

# ─────────────────────────────────────────────
# Whitelisted domains (obvious, non-piracy)
# ─────────────────────────────────────────────
DOMAIN_WHITELIST = {
    "google.com", "youtube.com", "twitter.com", "x.com",
    "facebook.com", "instagram.com", "reddit.com", "tiktok.com",
    "wikipedia.org", "apple.com", "microsoft.com", "amazon.com",
    "espn.com", "bbc.com", "cnn.com", "nytimes.com",
}

# ─────────────────────────────────────────────
# Regex Patterns
# ─────────────────────────────────────────────

# Domains: common TLDs including piracy-heavy ones
_RE_DOMAIN = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
    r"(?:com|net|org|io|co|tv|live|stream|online|site|xyz|top|club|"
    r"info|gg|me|to|cc|biz|pro|app|watch|sports|uk|de|fr|es|ca|au)\b",
    re.IGNORECASE,
)

# Telegram channel/group links: t.me/channelname or @channelname
_RE_TELEGRAM = re.compile(
    r"(?:https?://)?t\.me/([a-zA-Z0-9_]{3,})"
    r"|@([a-zA-Z0-9_]{3,})",
    re.IGNORECASE,
)

# IPTV signals: keywords associated with piracy IPTV panels/playlists
_RE_IPTV = re.compile(
    r"\b(?:xtream(?:[_\-]?codes?)?|m3u(?:8)?|stalker[_\-]?(?:portal)?|"
    r"xtream[_\-]?(?:ui|api)?|panel|reseller[_\-]?panel|"
    r"playlist|iptv[_\-]?(?:code|sub|panel|list|smarters)?)\b",
    re.IGNORECASE,
)

# Stream URLs: links ending in .m3u8, .ts, /live, /stream
_RE_STREAM_URL = re.compile(
    r"https?://[^\s\"'<>]+"
    r"(?:\.m3u8|\.ts|/live(?:[/?][^\s\"'<>]*)?|/stream(?:[/?][^\s\"'<>]*)?)\b",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _filter_domains(raw_domains: list[str]) -> list[str]:
    """Remove whitelisted and obviously non-piracy domains."""
    cleaned = []
    for d in raw_domains:
        d_lower = d.lower()
        if d_lower not in DOMAIN_WHITELIST:
            cleaned.append(d_lower)
    return list(dict.fromkeys(cleaned))  # deduplicate, preserve order


def _extract_telegram_handles(matches) -> list[str]:
    """Flatten telegram regex group tuples into clean handle list."""
    handles = []
    for m in matches:
        handle = m[0] or m[1]  # group 1 = t.me/X, group 2 = @X
        if handle:
            handles.append(handle.lower())
    return list(dict.fromkeys(handles))


def _make_node_id(entity_type: str, label: str) -> str:
    raw = f"{entity_type}:{label.lower()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ─────────────────────────────────────────────
# Core extraction
# ─────────────────────────────────────────────

def extract_entities_from_post(post_text: str) -> dict:
    """
    Extract piracy-network entities from a single post.

    Returns:
        {
            "domains":          [str, ...],
            "telegram_channels":[str, ...],
            "stream_urls":      [str, ...],
            "iptv_signals":     [str, ...],
            "iptv_providers":   [str, ...],   # Gemini only
            "sport":            str | None,   # Gemini only
            "threat_level":     "low"|"medium"|"high"
        }
    """
    # ── Regex pass ────────────────────────────
    raw_domains   = _RE_DOMAIN.findall(post_text)
    domains       = _filter_domains(raw_domains)

    tg_matches    = _RE_TELEGRAM.findall(post_text)
    telegram_chs  = _extract_telegram_handles(tg_matches)

    stream_urls   = list(dict.fromkeys(_RE_STREAM_URL.findall(post_text)))
    iptv_signals  = list(dict.fromkeys(
        [m.lower() for m in _RE_IPTV.findall(post_text)]
    ))

    # ── Gemini pass ───────────────────────────
    prompt = f"""You are a sports piracy analyst. Analyse the following social media post and extract piracy indicators.

POST:
\"\"\"{post_text}\"\"\"

Return ONLY a valid JSON object with exactly these keys:
{{
  "domains": ["list of piracy-related domain names missed by regex, no whitelisted sites"],
  "telegram_channels": ["telegram channel/group handles (without @) missed by regex"],
  "iptv_providers": ["commercial IPTV provider brand names mentioned"],
  "sport": "name of sport or league, or null if none",
  "threat_level": "low or medium or high"
}}

Rules:
- threat_level is high if direct stream links, IPTV credentials, or reseller panels are present
- threat_level is medium if domain/telegram sharing or IPTV provider names are present
- threat_level is low otherwise
- Return ONLY the JSON — no markdown, no explanation, no extra text."""

    gemini_result: dict = {}
    try:
        response = _gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw_text = response.text.strip()
        # Strip accidental markdown fences if model ignores instructions
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
        gemini_result = json.loads(raw_text)
    except Exception as exc:
        print(f"[WARN] Gemini extraction failed: {exc}")

    # ── Merge results ─────────────────────────
    g_domains  = _filter_domains(gemini_result.get("domains", []))
    g_tg       = [h.lstrip("@").lower() for h in gemini_result.get("telegram_channels", [])]
    g_providers = gemini_result.get("iptv_providers", [])
    sport       = gemini_result.get("sport") or None
    threat      = gemini_result.get("threat_level", "low")
    if threat not in {"low", "medium", "high"}:
        threat = "low"

    merged_domains  = list(dict.fromkeys(domains + g_domains))
    merged_telegram = list(dict.fromkeys(telegram_chs + g_tg))

    return {
        "domains":           merged_domains,
        "telegram_channels": merged_telegram,
        "stream_urls":       stream_urls,
        "iptv_signals":      iptv_signals,
        "iptv_providers":    list(dict.fromkeys(g_providers)),
        "sport":             sport,
        "threat_level":      threat,
    }


# ─────────────────────────────────────────────
# Graph builder
# ─────────────────────────────────────────────

def build_shadow_graph(posts: list[dict]) -> dict:
    """
    Build a piracy distribution network graph from a list of posts.

    Args:
        posts: list of dicts with keys: text, platform, url

    Returns:
        {"nodes": [...], "edges": [...]}
        Also saves graph to Firestore collection "shadow_graphs" / doc "latest".
    """
    node_map: dict[str, dict] = {}   # node_id -> node dict
    edge_map: dict[str, dict] = {}   # edge_id -> edge dict

    def _upsert_node(label: str, entity_type: str, threat: str):
        nid = _make_node_id(entity_type, label)
        if nid in node_map:
            node_map[nid]["count"] += 1
            # Escalate threat level if higher signal seen
            _levels = {"low": 0, "medium": 1, "high": 2}
            if _levels.get(threat, 0) > _levels.get(node_map[nid]["threat"], 0):
                node_map[nid]["threat"] = threat
        else:
            node_map[nid] = {
                "id":     nid,
                "label":  label,
                "type":   entity_type,
                "threat": threat,
                "count":  1,
            }
        return nid

    def _upsert_edge(nid_a: str, nid_b: str):
        # Canonical ordering so A-B == B-A
        if nid_a == nid_b:
            return
        a, b = sorted([nid_a, nid_b])
        eid = f"{a}__{b}"
        if eid in edge_map:
            edge_map[eid]["co_mention"] += 1
        else:
            edge_map[eid] = {
                "id":         eid,
                "source":     a,
                "target":     b,
                "co_mention": 1,
            }

    for post in posts:
        text     = post.get("text", "")
        entities = extract_entities_from_post(text)
        threat   = entities["threat_level"]

        # Collect node ids created for this post (for edge building)
        post_node_ids: list[str] = []

        for domain in entities["domains"]:
            post_node_ids.append(_upsert_node(domain, "domain", threat))

        for ch in entities["telegram_channels"]:
            post_node_ids.append(_upsert_node(ch, "telegram", threat))

        for url in entities["stream_urls"]:
            post_node_ids.append(_upsert_node(url, "stream_url", threat))

        for sig in entities["iptv_signals"]:
            post_node_ids.append(_upsert_node(sig, "iptv_signal", threat))

        for prov in entities["iptv_providers"]:
            post_node_ids.append(_upsert_node(prov, "iptv_provider", threat))

        # Build edges: all pairs of entities co-mentioned in this post
        for i in range(len(post_node_ids)):
            for j in range(i + 1, len(post_node_ids)):
                _upsert_edge(post_node_ids[i], post_node_ids[j])

    graph = {
        "nodes": list(node_map.values()),
        "edges": list(edge_map.values()),
    }

    # ── Firestore save ────────────────────────
    try:
        doc_ref = _db.collection("shadow_graphs").document("latest")
        doc_ref.set({
            "nodes":      graph["nodes"],
            "edges":      graph["edges"],
            "post_count": len(posts),
        })
        print(f"[INFO] Graph saved to Firestore: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges.")
    except Exception as exc:
        print(f"[WARN] Firestore save failed: {exc}")

    return graph


# ─────────────────────────────────────────────
# __main__
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import pathlib

    corpus_path = pathlib.Path("data/test_corpus/posts.json")
    if not corpus_path.exists():
        print(f"[ERROR] Test corpus not found at {corpus_path}. "
              "Create the file with a JSON array of post objects "
              "(keys: text, platform, url).")
        raise SystemExit(1)

    with corpus_path.open("r", encoding="utf-8") as fh:
        posts = json.load(fh)

    print(f"[INFO] Loaded {len(posts)} posts from {corpus_path}")
    result = build_shadow_graph(posts)

    print("\n=== Shadow Graph Result ===")
    print(json.dumps(result, indent=2))

def normalize_platform(platform: str) -> str:
    if not platform:
        return "Unknown"

    p = platform.strip().lower()
    mapping = {
        "youtube": "YouTube",
        "reddit": "Reddit",
        "x": "X",
        "twitter": "X",
        "telegram": "Telegram",
    }
    return mapping.get(p, platform)
    
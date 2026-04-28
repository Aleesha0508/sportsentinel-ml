def gs_to_public_url(gs_path: str) -> str:
    if not gs_path.startswith("gs://"):
        return gs_path

    path_without_prefix = gs_path.replace("gs://", "", 1)
    parts = path_without_prefix.split("/", 1)

    if len(parts) != 2:
        return ""

    bucket_name, object_path = parts
    return f"https://storage.googleapis.com/{bucket_name}/{object_path}"
import requests
import json
from pathlib import Path
from .config import LAUNCHER_DIR

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def fetch_manifest(force: bool = False) -> dict:
    cache_path = LAUNCHER_DIR / "version_manifest.json"
    if not force and cache_path.exists():
        try:
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    r = requests.get(MANIFEST_URL, timeout=15)
    r.raise_for_status()
    data = r.json()
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def fetch_version_meta(version_id: str, url: str) -> dict:
    cache_path = LAUNCHER_DIR / f"version_{version_id}.json"
    if cache_path.exists():
        try:
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data

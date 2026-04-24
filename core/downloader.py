"""
Downloader — fetches the game client jar, libraries, natives, and assets.
"""
import requests
import hashlib
import json
import os
import platform
import zipfile
from pathlib import Path
from .config import ASSETS_DIR, LIBRARIES_DIR

_OS = platform.system().lower()   # 'windows', 'linux', 'darwin'


# ── Low-level helpers ──────────────────────────────────────────────────────────

def verify_sha1(path, sha1: str) -> bool:
    if not sha1 or not os.path.exists(path):
        return False
    sha = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha.update(data)
        return sha.hexdigest() == sha1
    except Exception:
        return False


def download_file(url: str, dest, sha1: str = None, progress_callback=None):
    dest = Path(dest)
    if sha1 and verify_sha1(dest, sha1):
        if progress_callback:
            progress_callback(1.0)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    downloaded = 0
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total and progress_callback:
                    progress_callback(downloaded / total)
    if progress_callback:
        progress_callback(1.0)


# ── Version client jar ────────────────────────────────────────────────────────

def download_version_client(version_meta: dict, callback=None) -> Path:
    client = version_meta["downloads"]["client"]
    dest   = LIBRARIES_DIR / "client" / version_meta["id"] / f"{version_meta['id']}.jar"
    download_file(client["url"], dest, client["sha1"], progress_callback=callback)
    return dest


# ── Libraries + natives ───────────────────────────────────────────────────────

def _os_classifier() -> str:
    """Return the natives classifier string for the current OS."""
    if _OS == "windows":
        return "natives-windows"
    elif _OS == "darwin":
        return "natives-macos" if platform.machine().lower() == "arm64" else "natives-osx"
    return "natives-linux"


def _lib_applies(lib: dict) -> bool:
    """Return True if this library should be used on the current OS."""
    rules = lib.get("rules")
    if not rules:
        return True
    import re
    os_map = {"Darwin": "osx", "Windows": "windows", "Linux": "linux"}
    cur_os = os_map.get(platform.system(), "linux")
    result = False
    for rule in rules:
        action = rule.get("action", "allow") == "allow"
        os_cond = rule.get("os", {})
        if os_cond:
            if os_cond.get("name", cur_os) != cur_os:
                continue
            if "version" in os_cond:
                try:
                    if not re.search(os_cond["version"], platform.version()):
                        continue
                except re.error:
                    pass
        result = action
    return result


def download_libraries(version_meta: dict, callback=None) -> Path:
    """
    Download all library JARs and extract natives into a per-version directory.
    Returns the natives directory path.
    """
    version_id   = version_meta["id"]
    natives_dir  = LIBRARIES_DIR / "natives" / version_id
    natives_dir.mkdir(parents=True, exist_ok=True)

    libs  = version_meta.get("libraries", [])
    total = len(libs)
    classifier = _os_classifier()

    for idx, lib in enumerate(libs):
        if not _lib_applies(lib):
            if callback and total:
                callback((idx + 1) / total)
            continue

        downloads = lib.get("downloads", {})

        # ── Main artifact ──────────────────────────────────────────────────
        artifact = downloads.get("artifact")
        if artifact and artifact.get("url"):
            dest = LIBRARIES_DIR / artifact["path"]
            download_file(artifact["url"], dest, artifact.get("sha1"))

        # ── Natives classifier ─────────────────────────────────────────────
        # Try exact classifier first, then fall back to os-only name variants
        classifiers = downloads.get("classifiers", {})
        native_jar  = None
        for candidate in [classifier, classifier.replace("-macos", "-osx"),
                          "natives-" + _OS]:
            if candidate in classifiers:
                native_jar = classifiers[candidate]
                break

        # Older format: lib["natives"] maps os → classifier token
        if native_jar is None and "natives" in lib:
            os_map2 = {"Darwin": "osx", "Windows": "windows", "Linux": "linux"}
            cur_os2 = os_map2.get(platform.system(), "linux")
            token   = lib["natives"].get(cur_os2)
            if token:
                # token may contain ${arch} placeholder
                import re as _re
                arch = "64" if platform.machine() in ("x86_64", "AMD64", "aarch64") else "32"
                token = token.replace("${arch}", arch)
                if token in classifiers:
                    native_jar = classifiers[token]

        if native_jar and native_jar.get("url"):
            native_path = LIBRARIES_DIR / native_jar["path"]
            download_file(native_jar["url"], native_path, native_jar.get("sha1"))
            # Extract into natives directory (skip META-INF)
            try:
                with zipfile.ZipFile(native_path) as zf:
                    for entry in zf.infolist():
                        if entry.filename.startswith("META-INF"):
                            continue
                        zf.extract(entry, natives_dir)
            except Exception:
                pass

        if callback and total:
            callback((idx + 1) / total)

    if callback:
        callback(1.0)

    return natives_dir


# ── Asset index + objects ─────────────────────────────────────────────────────

def download_asset_index(version_meta: dict, callback=None) -> dict:
    """Download the asset index JSON and return its parsed contents."""
    asset_index = version_meta.get("assetIndex")
    if not asset_index:
        return {}
    dest = ASSETS_DIR / "indexes" / f"{asset_index['id']}.json"
    download_file(asset_index["url"], dest, asset_index.get("sha1"), progress_callback=callback)
    try:
        with open(dest, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def download_assets(version_meta: dict, callback=None):
    """Download all asset objects referenced by the asset index."""
    index = download_asset_index(version_meta)
    objects = index.get("objects", {})
    total   = len(objects)
    if total == 0:
        return

    virtual   = index.get("virtual", False)
    map_res   = index.get("map_to_resources", False)

    for i, (name, info) in enumerate(objects.items()):
        h    = info["hash"]
        prefix = h[:2]
        url  = f"https://resources.download.minecraft.net/{prefix}/{h}"
        dest = ASSETS_DIR / "objects" / prefix / h
        download_file(url, dest, h)   # hash IS the sha1

        # Legacy (pre-1.7.2): also copy into virtual/legacy tree
        if virtual or map_res:
            vdest = ASSETS_DIR / "virtual" / "legacy" / name
            if not vdest.exists():
                vdest.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(dest, vdest)

        if callback and total:
            callback((i + 1) / total)

    if callback:
        callback(1.0)

import requests
import json
from pathlib import Path
from .config import LIBRARIES_DIR

FABRIC_META    = "https://meta.fabricmc.net/v2/versions/loader"
FABRIC_PROFILE = "https://meta.fabricmc.net/v2/versions/loader/{minecraft_version}/{loader_version}/profile/json"


def get_fabric_loaders():
    r = requests.get(FABRIC_META, timeout=10)
    r.raise_for_status()
    return r.json()


def get_fabric_profile(minecraft_version: str, loader_version: str):
    url = FABRIC_PROFILE.format(
        minecraft_version=minecraft_version,
        loader_version=loader_version,
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def install_fabric(version_meta: dict, loader_version: str):
    mc_ver  = version_meta["id"]
    profile = get_fabric_profile(mc_ver, loader_version)
    for lib in profile.get("libraries", []):
        name = lib.get("name", "")
        url  = lib.get("url", "https://maven.fabricmc.net/")
        if not name:
            continue
        _download_maven_lib(url, name)
    return profile


def _download_maven_lib(repo_url: str, maven_name: str):
    """
    Convert a maven coordinate (group:artifact:version) to a path and download it.
    e.g. net.fabricmc:fabric-loader:0.15.0 ->
         net/fabricmc/fabric-loader/0.15.0/fabric-loader-0.15.0.jar
    """
    parts = maven_name.split(":")
    if len(parts) < 3:
        return
    group, artifact, version = parts[0], parts[1], parts[2]
    group_path = group.replace(".", "/")
    jar_name   = f"{artifact}-{version}.jar"
    rel_path   = f"{group_path}/{artifact}/{version}/{jar_name}"
    dest       = LIBRARIES_DIR / rel_path
    if dest.exists():
        return
    full_url = repo_url.rstrip("/") + "/" + rel_path
    from .downloader import download_file
    try:
        download_file(full_url, dest)
    except Exception:
        pass  # non-fatal; some libs may be absent from a given repo

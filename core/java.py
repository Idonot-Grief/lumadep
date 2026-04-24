import zipfile
import tarfile
import os
import platform
from pathlib import Path
from .config import JAVA_DIR

_OS  = platform.system().lower()   # 'windows', 'linux', 'darwin'
_ARCH = platform.machine().lower()  # 'amd64', 'x86_64', 'arm64', 'aarch64'

# Azul Zulu JDK download URLs per (major_version, os, arch)
# Format: (url, is_zip)  — True=zip, False=tar.gz
_JAVA_URLS = {
    # Java 8
    (8, "windows", "amd64"):   ("https://cdn.azul.com/zulu/bin/zulu8.94.0.17-ca-jdk8.0.492-win_x64.zip", True),
    (8, "linux",   "amd64"):   ("https://cdn.azul.com/zulu/bin/zulu8.94.0.17-ca-jdk8.0.492-linux_x64.tar.gz", False),
    (8, "darwin",  "amd64"):   ("https://cdn.azul.com/zulu/bin/zulu8.94.0.17-ca-jdk8.0.492-macosx_x64.tar.gz", False),
    # Java 17
    (17, "windows", "amd64"):  ("https://cdn.azul.com/zulu/bin/zulu17.66.19-ca-jdk17.0.19-win_x64.zip", True),
    (17, "linux",   "amd64"):  ("https://cdn.azul.com/zulu/bin/zulu17.66.19-ca-jdk17.0.19-linux_x64.tar.gz", False),
    (17, "darwin",  "amd64"):  ("https://cdn.azul.com/zulu/bin/zulu17.66.19-ca-jdk17.0.19-macosx_x64.tar.gz", False),
    (17, "darwin",  "arm64"):  ("https://cdn.azul.com/zulu/bin/zulu17.66.19-ca-jdk17.0.19-macosx_aarch64.tar.gz", False),
    # Java 21
    (21, "windows", "amd64"):  ("https://cdn.azul.com/zulu/bin/zulu21.50.19-ca-jdk21.0.11-win_x64.zip", True),
    (21, "linux",   "amd64"):  ("https://cdn.azul.com/zulu/bin/zulu21.50.19-ca-jdk21.0.11-linux_x64.tar.gz", False),
    (21, "darwin",  "amd64"):  ("https://cdn.azul.com/zulu/bin/zulu21.50.19-ca-jdk21.0.11-macosx_x64.tar.gz", False),
    (21, "darwin",  "arm64"):  ("https://cdn.azul.com/zulu/bin/zulu21.50.19-ca-jdk21.0.11-macosx_aarch64.tar.gz", False),
}

# Normalise arch names
_ARCH_MAP = {"x86_64": "amd64", "aarch64": "arm64"}
_NORM_ARCH = _ARCH_MAP.get(_ARCH, _ARCH)

# Map versions that don't have explicit entries to closest available
_VERSION_FALLBACK = {16: 17, 18: 21, 19: 21, 20: 21, 25: 21, 26: 21}


def get_java_version_required(version_meta: dict) -> int:
    java_ver = version_meta.get("javaVersion", {})
    return java_ver.get("majorVersion", 8)


def _resolve_version(version: int) -> int:
    """Map to the nearest version we have a download for."""
    supported = [8, 17, 21]
    if version in supported:
        return version
    if version in _VERSION_FALLBACK:
        return _VERSION_FALLBACK[version]
    # pick the smallest supported version that is >= requested
    for v in sorted(supported):
        if v >= version:
            return v
    return supported[-1]


def install_java(version: int, callback=None) -> Path:
    version = _resolve_version(version)
    java_path = JAVA_DIR / str(version)
    if java_path.exists() and find_java_executable(java_path):
        return java_path   # already installed

    key = (version, _OS, _NORM_ARCH)
    # fallback to amd64 if arm not found
    if key not in _JAVA_URLS:
        key = (version, _OS, "amd64")
    if key not in _JAVA_URLS:
        raise Exception(
            f"No Java {version} download available for {_OS}/{_NORM_ARCH}. "
            "Please install Java manually and set the path in Settings."
        )

    url, is_zip = _JAVA_URLS[key]
    ext = ".zip" if is_zip else ".tar.gz"
    archive_dest = JAVA_DIR / f"jdk{version}{ext}"

    from .downloader import download_file
    download_file(url, archive_dest, progress_callback=callback)

    java_path.mkdir(parents=True, exist_ok=True)

    if is_zip:
        with zipfile.ZipFile(archive_dest) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                parts = member.filename.split("/")
                new_parts = parts[1:] if len(parts) > 1 else parts
                if not new_parts or not new_parts[0]:
                    continue
                target = java_path / "/".join(new_parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target, "wb") as out:
                    out.write(src.read())
    else:
        with tarfile.open(archive_dest, "r:gz") as tf:
            for member in tf.getmembers():
                parts = member.name.split("/")
                new_parts = parts[1:] if len(parts) > 1 else parts
                if not new_parts or not new_parts[0]:
                    continue
                member.name = "/".join(new_parts)
                tf.extract(member, java_path)

    try:
        archive_dest.unlink()
    except Exception:
        pass

    # Make executables runnable on Unix
    if _OS in ("linux", "darwin"):
        bin_dir = java_path / "bin"
        if bin_dir.exists():
            for f in bin_dir.iterdir():
                try:
                    f.chmod(f.stat().st_mode | 0o111)
                except Exception:
                    pass

    return java_path


def find_java_executable(java_path: Path):
    """Find the java binary inside an extracted JDK directory."""
    if _OS == "windows":
        candidates = [
            java_path / "bin" / "java.exe",    # always prefer: console output visible
        ]
    elif _OS == "darwin":
        candidates = [
            java_path / "Contents" / "Home" / "bin" / "java",
            java_path / "bin" / "java",
        ]
    else:
        candidates = [java_path / "bin" / "java"]

    for c in candidates:
        if c.exists():
            return c
    return None

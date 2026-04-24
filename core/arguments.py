"""
Minecraft launch argument builder.

Handles all version formats:
  - Pre-1.13  : meta["minecraftArguments"] is a flat template string
  - 1.13+     : meta["arguments"]["jvm"] + meta["arguments"]["game"] are
                structured lists with per-rule conditional entries

Also resolves every ${variable} placeholder the Mojang launcher spec defines.
"""
import platform
import re
from pathlib import Path
from typing import Any, Dict, List, Union


# ── OS helpers ────────────────────────────────────────────────────────────────

def _os_name() -> str:
    s = platform.system()
    return "osx" if s == "Darwin" else ("windows" if s == "Windows" else "linux")

def _os_arch() -> str:
    m = platform.machine().lower()
    return "x86" if m in ("i386", "i686", "x86") else "x64"

def _os_version() -> str:
    return platform.version()


# ── Rule evaluator ────────────────────────────────────────────────────────────

def _eval_rules(rules: List[Dict], features: Dict[str, bool] = None) -> bool:
    """
    Evaluate a Mojang rules list.  Returns True if the argument should be included.
    Default (no rules) = always include.
    """
    if not rules:
        return True

    features = features or {}
    result = False  # default-deny when rules are present

    for rule in rules:
        action = rule.get("action", "allow") == "allow"

        # OS condition
        os_cond = rule.get("os")
        if os_cond:
            if "name" in os_cond and os_cond["name"] != _os_name():
                continue
            if "arch" in os_cond and os_cond["arch"] != _os_arch():
                continue
            if "version" in os_cond:
                try:
                    if not re.search(os_cond["version"], _os_version()):
                        continue
                except re.error:
                    pass

        # Feature condition  (e.g. is_demo_user, has_custom_resolution)
        feat_cond = rule.get("features")
        if feat_cond:
            match = all(features.get(k, False) == v for k, v in feat_cond.items())
            if not match:
                continue

        result = action

    return result


# ── Variable substitution ─────────────────────────────────────────────────────

def _substitute(text: str, variables: Dict[str, str]) -> str:
    for k, v in variables.items():
        text = text.replace(f"${{{k}}}", v)
    return text


# ── Single argument resolver ──────────────────────────────────────────────────

def _resolve_arg(arg: Union[str, dict], variables: Dict[str, str],
                 features: Dict[str, bool]) -> List[str]:
    if isinstance(arg, str):
        return [_substitute(arg, variables)]
    if isinstance(arg, dict):
        rules = arg.get("rules", [])
        if _eval_rules(rules, features):
            value = arg.get("value", [])
            if isinstance(value, str):
                return [_substitute(value, variables)]
            return [_substitute(v, variables) for v in value]
    return []


# ── Public API ────────────────────────────────────────────────────────────────

def build_launch_command(
    meta: dict,
    *,
    java_exe: Path,
    classpath: str,
    natives_dir: Path,
    game_dir: Path,
    assets_dir: Path,
    auth_player: str,
    auth_uuid: str,
    access_token: str,
    user_type: str,
    ram_min: int,
    ram_max: int,
    extra_jvm_args: str = "",
    resolution: tuple = None,       # (width, height) or None
    launcher_name: str = "mc-launcher",
    launcher_version: str = "2.0",
) -> List[str]:
    """
    Build the full Java launch command for any Minecraft version.

    Works with:
      • Very old versions (rd-*, a*, b*, 1.0–1.12.x) — minecraftArguments string
      • Modern versions (1.13+)                       — arguments.jvm / arguments.game
    """
    version_id   = meta["id"]
    main_class   = meta.get("mainClass", "net.minecraft.client.main.Main")
    asset_index  = meta.get("assetIndex", {}).get("id", "legacy") if meta.get("assetIndex") else "legacy"

    features = {
        "is_demo_user":          False,
        "has_custom_resolution": resolution is not None,
    }

    variables = {
        # paths
        "natives_directory":  str(natives_dir),
        "launcher_name":      launcher_name,
        "launcher_version":   launcher_version,
        "classpath":          classpath,
        "game_directory":     str(game_dir),
        "assets_root":        str(assets_dir),
        "assets_index_name":  asset_index,
        "game_assets":        str(assets_dir / "virtual" / "legacy"),  # pre-1.7
        # auth
        "auth_player_name":   auth_player,
        "auth_uuid":          auth_uuid,
        "auth_access_token":  access_token,
        "auth_session":       f"token:{access_token}:{auth_uuid}",  # very old
        "user_type":          user_type,
        "user_properties":    "{}",
        # version
        "version_name":       version_id,
        "version_type":       meta.get("type", "release"),
        # resolution (only used when has_custom_resolution=True)
        "resolution_width":   str(resolution[0]) if resolution else "854",
        "resolution_height":  str(resolution[1]) if resolution else "480",
    }

    cmd: List[str] = [str(java_exe)]

    # ── RAM ───────────────────────────────────────────────────────────────────
    cmd += [f"-Xms{ram_min}m", f"-Xmx{ram_max}m"]

    # ── JVM arguments ─────────────────────────────────────────────────────────
    if "arguments" in meta and "jvm" in meta["arguments"]:
        # Modern format (1.13+)
        for arg in meta["arguments"]["jvm"]:
            cmd.extend(_resolve_arg(arg, variables, features))
    else:
        # Legacy: synthesise the minimum required JVM args
        cmd += [
            f"-Djava.library.path={natives_dir}",
            "-Dfile.encoding=UTF-8",
            "-Dlog4j2.formatMsgNoLookups=true",
        ]

    # Modern format may omit -Djava.library.path if it relies on the manifest
    # rule to inject it — but always ensure it is present so natives load.
    lib_path_flag = f"-Djava.library.path={natives_dir}"
    if lib_path_flag not in cmd:
        # Insert right after the java executable (index 0)
        cmd.insert(1, lib_path_flag)

    # ── Extra user JVM args ───────────────────────────────────────────────────
    if extra_jvm_args:
        cmd.extend(extra_jvm_args.split())

    # ── Classpath + main class ────────────────────────────────────────────────
    cmd += ["-cp", classpath, main_class]

    # ── Game arguments ────────────────────────────────────────────────────────
    if "arguments" in meta and "game" in meta["arguments"]:
        # Modern format (1.13+)
        for arg in meta["arguments"]["game"]:
            cmd.extend(_resolve_arg(arg, variables, features))
    elif "minecraftArguments" in meta:
        # Legacy flat-string format (pre-1.13)
        legacy = _substitute(meta["minecraftArguments"], variables)
        cmd.extend(legacy.split())
    else:
        # Absolute fallback for very old / custom classic versions
        # (rd-*, c*, a* that have no argument list at all)
        cmd += [
            auth_player,
            access_token,
        ]

    return cmd

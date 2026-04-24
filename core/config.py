"""
Launcher configuration. All data is stored next to main.py (the launcher root).
Nothing is written to AppData or the user home directory.
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict
from dataclasses import dataclass, asdict, field


def _launcher_root():
    """Return the directory containing main.py, works for source and frozen builds."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


LAUNCHER_DIR  = _launcher_root()
CONFIG_FILE   = LAUNCHER_DIR / "config.json"
INSTANCES_DIR = LAUNCHER_DIR / "instances"
LIBRARIES_DIR = LAUNCHER_DIR / "libraries"
JAVA_DIR      = LAUNCHER_DIR / "java"
ASSETS_DIR    = LAUNCHER_DIR / "assets"
VERSIONS_DIR  = LAUNCHER_DIR / "versions"


@dataclass
class ThemeConfig:
    name: str = "Dark"
    primary_color: str = "#2196F3"
    accent_color: str = "#FF5722"
    text_color: str = "#FFFFFF"
    background_color: str = "#212121"
    custom_icon: str = ""


@dataclass
class JavaConfig:
    java_path: str = ""
    min_ram: int = 2048
    max_ram: int = 4096
    extra_jvm_args: str = ""
    use_system_java: bool = True


@dataclass
class AuthConfig:
    username: str = "Player"
    uuid: str = "00000000-0000-0000-0000-000000000000"
    offline_mode: bool = True
    default_offline_name: str = "Player"
    use_microsoft_account: bool = False
    access_token: str = ""
    refresh_token: str = ""


@dataclass
class LauncherConfig:
    version: str = "2.0.0"
    auth: AuthConfig = field(default_factory=AuthConfig)
    java: JavaConfig = field(default_factory=JavaConfig)
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    show_console: bool = True
    keep_launcher_open: bool = False
    window_geometry: Dict[str, int] = field(default_factory=lambda: {
        "x": 100, "y": 100, "width": 1000, "height": 660
    })
    api_type: str = "mojang"
    custom_api_url: str = "https://piston-meta.mojang.com"
    auto_check_updates: bool = True
    update_server: str = "http://127.0.0.1:4355"
    logging_level: str = "INFO"
    cache_libraries: bool = True
    use_system_java_only: bool = False

    def to_dict(self):
        return {
            "version":              self.version,
            "auth":                 asdict(self.auth),
            "java":                 asdict(self.java),
            "theme":                asdict(self.theme),
            "show_console":         self.show_console,
            "keep_launcher_open":   self.keep_launcher_open,
            "window_geometry":      self.window_geometry,
            "api_type":             self.api_type,
            "custom_api_url":       self.custom_api_url,
            "auto_check_updates":   self.auto_check_updates,
            "update_server":        self.update_server,
            "logging_level":        self.logging_level,
            "cache_libraries":      self.cache_libraries,
            "use_system_java_only": self.use_system_java_only,
        }

    @staticmethod
    def _safe_dc(cls, data: dict):
        import dataclasses
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "LauncherConfig":
        config = LauncherConfig()
        if "auth" in data and isinstance(data["auth"], dict):
            config.auth = LauncherConfig._safe_dc(AuthConfig, data["auth"])
        if "java" in data and isinstance(data["java"], dict):
            config.java = LauncherConfig._safe_dc(JavaConfig, data["java"])
        if "theme" in data and isinstance(data["theme"], dict):
            config.theme = LauncherConfig._safe_dc(ThemeConfig, data["theme"])
        for key in ["show_console", "keep_launcher_open", "auto_check_updates",
                    "cache_libraries", "use_system_java_only"]:
            if key in data:
                setattr(config, key, data[key])
        for key in ["window_geometry", "api_type", "custom_api_url",
                    "update_server", "logging_level", "version"]:
            if key in data:
                setattr(config, key, data[key])
        return config


def load_config() -> LauncherConfig:
    LAUNCHER_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return LauncherConfig.from_dict(json.load(f))
        except Exception as e:
            print("Failed to load config: {}, using defaults".format(e))
    return LauncherConfig()


def save_config(config: LauncherConfig):
    LAUNCHER_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2)
    except Exception as e:
        print("Failed to save config: {}".format(e))


def migrate_old_config():
    old_file = LAUNCHER_DIR / "launcher_config.json"
    if not old_file.exists():
        return
    try:
        with open(old_file, encoding="utf-8") as f:
            old_data = json.load(f)
        new_config = LauncherConfig()
        if "username" in old_data:
            new_config.auth.username = old_data["username"]
            new_config.auth.default_offline_name = old_data["username"]
        if "offline" in old_data:
            new_config.auth.offline_mode = old_data["offline"]
        if "ram_min" in old_data:
            new_config.java.min_ram = old_data["ram_min"]
        if "ram_max" in old_data:
            new_config.java.max_ram = old_data["ram_max"]
        save_config(new_config)
        old_file.unlink()
    except Exception as e:
        print("Failed to migrate old config: {}".format(e))

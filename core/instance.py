import json
from pathlib import Path
from .config import INSTANCES_DIR


class Instance:
    def __init__(self, name: str, path: Path = None):
        self.name = name
        self.path = path or INSTANCES_DIR / name
        self.path.mkdir(parents=True, exist_ok=True)
        self.config_file = self.path / "instance.json"
        self.data = self.load()

    def load(self):
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "name": self.name,
            "version": "",
            "java_path": "",
            "fabric_loader": "",
            "offline": True,
            "username": "",
            "ram_min": "2048",
            "ram_max": "4096",
            "jvm_args": "",
        }

    def _int(self, key: str, default: int) -> int:
        """Read an instance data value as int, tolerating string storage."""
        try:
            return int(self.data.get(key, default))
        except (ValueError, TypeError):
            return default

    @property
    def ram_min(self) -> int:
        return self._int("ram_min", 2048)

    @property
    def ram_max(self) -> int:
        return self._int("ram_max", 4096)

    def save(self):
        self.data["name"] = self.name
        # Normalise RAM to int before writing so the file is always consistent
        for key in ("ram_min", "ram_max"):
            if key in self.data:
                try:
                    self.data[key] = int(self.data[key])
                except (ValueError, TypeError):
                    pass
        self.config_file.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def set_version(self, version_id: str):
        self.data["version"] = version_id
        self.save()

    def set_fabric(self, loader_version: str):
        self.data["fabric_loader"] = loader_version
        self.save()

    def set_java(self, java_path: str):
        self.data["java_path"] = str(java_path)
        self.save()

    def __repr__(self):
        return f"<Instance name={self.name!r} version={self.data.get('version')!r}>"

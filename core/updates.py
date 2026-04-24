"""
Update and patch management system with .upt patch files.
"""
import json
import hashlib
import zipfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import requests
from core.logger import launcher_logger


@dataclass
class UpdateInfo:
    """Represents a single update."""
    id: str
    version: str
    description: str
    release_date: str
    url: str
    size: int
    hash: str
    required: bool = False


class UpdateManager:
    """Manages launcher updates and patches."""
    
    def __init__(self, launcher_root: Path, update_server: str):
        self.launcher_root = launcher_root
        self.update_server = update_server.rstrip('/')
        self.updates_dir = launcher_root / 'updates'
        self.applied_patches_file = launcher_root / 'applied_patches.json'
        self.updates_dir.mkdir(parents=True, exist_ok=True)
        
        self.applied_patches = self._load_applied_patches()
    
    def _load_applied_patches(self) -> Dict[str, List[str]]:
        """Load history of applied patches."""
        if self.applied_patches_file.exists():
            try:
                with open(self.applied_patches_file) as f:
                    return json.load(f)
            except Exception as e:
                launcher_logger.error(f"Failed to load patch history: {e}")
        return {"applied": [], "timestamp": None}
    
    def _save_applied_patches(self):
        """Save applied patches history."""
        try:
            with open(self.applied_patches_file, 'w') as f:
                json.dump(self.applied_patches, f, indent=2)
        except Exception as e:
            launcher_logger.error(f"Failed to save patch history: {e}")
    
    def fetch_updates_list(self) -> List[UpdateInfo]:
        """Fetch available updates from server."""
        try:
            url = f"{self.update_server}/updates/"
            launcher_logger.info(f"Checking for updates at {url}")
            
            response = requests.get(url, timeout=10, verify=False)
            response.raise_for_status()
            
            # Parse XML or JSON updates list
            updates = []
            try:
                # Try JSON first
                data = response.json()
                for item in data.get('updates', []):
                    updates.append(UpdateInfo(**item))
            except:
                # Parse XML if JSON fails
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                for update_elem in root.findall('update'):
                    updates.append(UpdateInfo(
                        id=update_elem.find('id').text,
                        version=update_elem.find('version').text,
                        description=update_elem.find('description').text,
                        release_date=update_elem.find('releaseDate').text,
                        url=update_elem.find('url').text,
                        size=int(update_elem.find('size').text),
                        hash=update_elem.find('hash').text,
                        required=update_elem.find('required').text.lower() == 'true'
                    ))
            
            return updates
        except Exception as e:
            launcher_logger.error(f"Failed to fetch updates: {e}")
            return []
    
    def get_missing_updates(self, available_updates: List[UpdateInfo]) -> List[UpdateInfo]:
        """Find updates that haven't been applied yet."""
        applied_ids = set(self.applied_patches.get('applied', []))
        missing = [u for u in available_updates if u.id not in applied_ids]
        return sorted(missing, key=lambda x: x.release_date)
    
    def download_patch(self, update: UpdateInfo) -> Optional[Path]:
        """Download a patch file (.upt)."""
        try:
            patch_path = self.updates_dir / f"{update.id}.upt"
            
            # Skip if already downloaded and hash matches
            if patch_path.exists():
                file_hash = self._compute_file_hash(patch_path)
                if file_hash == update.hash:
                    launcher_logger.info(f"Patch {update.id} already downloaded")
                    return patch_path
            
            launcher_logger.info(f"Downloading patch {update.id}...")
            url = update.url if update.url.startswith('http') else f"{self.update_server}/files/{update.url}"
            
            response = requests.get(url, timeout=30, verify=False, stream=True)
            response.raise_for_status()
            
            with open(patch_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Verify hash
            file_hash = self._compute_file_hash(patch_path)
            if file_hash != update.hash:
                launcher_logger.error(f"Hash mismatch for patch {update.id}")
                patch_path.unlink()
                return None
            
            launcher_logger.info(f"Successfully downloaded patch {update.id}")
            return patch_path
        except Exception as e:
            launcher_logger.error(f"Failed to download patch {update.id}: {e}")
            return None
    
    def apply_patch(self, patch_path: Path) -> bool:
        """Apply a patch file to the launcher."""
        try:
            launcher_logger.info(f"Applying patch {patch_path.name}...")
            
            with zipfile.ZipFile(patch_path, 'r') as zip_ref:
                # Read patch metadata
                metadata = {}
                if 'PATCH_INFO.json' in zip_ref.namelist():
                    with zip_ref.open('PATCH_INFO.json') as f:
                        metadata = json.load(f)
                
                # Extract files to launcher root
                for file_info in zip_ref.infolist():
                    if file_info.filename == 'PATCH_INFO.json':
                        continue
                    
                    target_path = self.launcher_root / file_info.filename
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with zip_ref.open(file_info) as source, open(target_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
            
            # Record as applied
            update_id = patch_path.stem
            if update_id not in self.applied_patches.get('applied', []):
                self.applied_patches['applied'].append(update_id)
                self.applied_patches['timestamp'] = datetime.now().isoformat()
                self._save_applied_patches()
            
            launcher_logger.info(f"Successfully applied patch {update_id}")
            return True
        except Exception as e:
            launcher_logger.error(f"Failed to apply patch: {e}")
            return False
    
    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def import_patch_file(self, file_path: Path) -> bool:
        """Import a patch file from outside the updates directory."""
        try:
            # Copy to updates directory
            dest_path = self.updates_dir / file_path.name
            shutil.copy2(file_path, dest_path)
            launcher_logger.info(f"Imported patch {file_path.name}")
            return True
        except Exception as e:
            launcher_logger.error(f"Failed to import patch: {e}")
            return False


class PatchCreator:
    """Create .upt patch files."""
    
    @staticmethod
    def create_patch(patch_id: str, version: str, description: str,
                    files_to_patch: Dict[str, Path], output_path: Path) -> bool:
        """
        Create a .upt patch file.
        
        Args:
            patch_id: Unique patch identifier
            version: Version string
            description: Patch description
            files_to_patch: Dict of {relative_path: source_file_path}
            output_path: Where to save the .upt file
        """
        try:
            metadata = {
                'id': patch_id,
                'version': version,
                'description': description,
                'created': datetime.now().isoformat(),
                'files': list(files_to_patch.keys())
            }
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add metadata
                zf.writestr('PATCH_INFO.json', json.dumps(metadata, indent=2))
                
                # Add files
                for rel_path, source_file in files_to_patch.items():
                    if source_file.exists():
                        zf.write(source_file, rel_path)
            
            return True
        except Exception as e:
            launcher_logger.error(f"Failed to create patch: {e}")
            return False

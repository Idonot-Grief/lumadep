"""
Patcher executable - applies launcher updates.
This runs separately from the main launcher during updates.
"""
import sys
import os
import json
import zipfile
import subprocess
from pathlib import Path
from datetime import datetime
import time


class Patcher:
    """Apply patches to the launcher."""
    
    def __init__(self, launcher_dir: Path, patches: list):
        self.launcher_dir = launcher_dir
        self.patches = patches  # List of patch file paths
        self.applied = []
        self.failed = []
    
    def apply_all(self) -> bool:
        """Apply all patches in order."""
        print(f"[Patcher] Starting patch process at {datetime.now().strftime('%H:%M:%S')}")
        print(f"[Patcher] Applying {len(self.patches)} patches...")
        
        for i, patch_path in enumerate(self.patches, 1):
            print(f"\n[Patcher] [{i}/{len(self.patches)}] Applying {Path(patch_path).name}...")
            
            if self._apply_patch(patch_path):
                self.applied.append(Path(patch_path).stem)
                print(f"[Patcher] ✓ Successfully applied")
            else:
                self.failed.append(Path(patch_path).stem)
                print(f"[Patcher] ✗ Failed to apply")
                # Continue with next patch even if one fails
        
        # Save results
        self._save_patch_log()
        
        if self.failed:
            print(f"\n[Patcher] ✗ {len(self.failed)} patches failed")
            return False
        else:
            print(f"\n[Patcher] ✓ All patches applied successfully!")
            return True
    
    def _apply_patch(self, patch_path: str) -> bool:
        """Apply a single patch."""
        try:
            patch_file = Path(patch_path)
            if not patch_file.exists():
                print(f"[Patcher] Patch file not found: {patch_path}")
                return False
            
            with zipfile.ZipFile(patch_file, 'r') as zip_ref:
                # Extract to launcher directory
                for file_info in zip_ref.infolist():
                    if file_info.filename == 'PATCH_INFO.json':
                        continue
                    
                    target_path = self.launcher_dir / file_info.filename
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with zip_ref.open(file_info) as source, open(target_path, 'wb') as target:
                        target.write(source.read())
                    
                    print(f"[Patcher]   → {file_info.filename}")
            
            return True
        except Exception as e:
            print(f"[Patcher] Error: {e}")
            return False
    
    def _save_patch_log(self):
        """Save patch application log."""
        log_file = self.launcher_dir / 'patch_log.json'
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'applied': self.applied,
            'failed': self.failed,
            'total': len(self.patches)
        }
        
        try:
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
        except Exception as e:
            print(f"[Patcher] Failed to save log: {e}")


def main():
    """Main patcher entry point."""
    if len(sys.argv) < 2:
        print("Usage: patcher.py <launcher_dir> [patch1.upt] [patch2.upt] ...")
        sys.exit(1)
    
    launcher_dir = Path(sys.argv[1])
    patches = sys.argv[2:]
    
    if not launcher_dir.exists():
        print(f"[Patcher] Launcher directory not found: {launcher_dir}")
        sys.exit(1)
    
    patcher = Patcher(launcher_dir, patches)
    success = patcher.apply_all()
    
    # Return exit code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

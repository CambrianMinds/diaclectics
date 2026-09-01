#!/usr/bin/env python3
"""
Diaclectics Clean Release Exporter
===================================
Exports a pristine, sterile open-source release directory or tarball,
excluding local cache files, personal transcripts, and development scratchpads.
"""

import os
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path

# Paths to include in a clean release
INCLUDE_PATTERNS = [
    "src",
    "tests",
    "integrations",
    "docs",
    "data/seeds",
    "data/benchmarks",
    "data/training",
    "scripts",
    "outputs/axes",
    ".github",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.full.yml",
    "pyproject.toml",
    "setup.py",
    "pytest.ini",
    "requirements.txt",
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "CITATION.cff",
    ".gitignore"
]

EXCLUDE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".cache",
    ".git",
    "data/parsed",
    "reports",
    "dist",
    "build",
    "*.egg-info"
}

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def export_clean_release(output_dir: str = "dist/diaclectics_release", make_archive: bool = True) -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    target_path = repo_root / output_dir

    if target_path.exists():
        shutil.rmtree(target_path)
    target_path.mkdir(parents=True, exist_ok=True)

    print(f"[*] Exporting clean Diaclectics release from: {repo_root}")
    print(f"[*] Destination directory: {target_path}")


    copied_files = 0

    for pattern in INCLUDE_PATTERNS:
        src_path = repo_root / pattern
        if not src_path.exists():
            continue

        if src_path.is_file():
            dest_file = target_path / pattern
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_file)
            copied_files += 1
        elif src_path.is_dir():
            for root, dirs, files in os.walk(src_path):
                rel_root = Path(root).relative_to(repo_root)
                
                # Skip excluded directories
                if any(ex in str(rel_root).replace("\\", "/") for ex in EXCLUDE_DIRS):
                    continue

                for f in files:
                    if f.endswith(".pyc") or f == ".DS_Store":
                        continue
                    src_file = Path(root) / f
                    rel_file = src_file.relative_to(repo_root)
                    dest_file = target_path / rel_file
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_file)
                    copied_files += 1

    print(f"[+] Clean release prepared: {copied_files} files copied.")

    if make_archive:
        zip_path = repo_root / "dist" / "diaclectics-v1.0.0-clean.zip"
        print(f"[*] Creating release zip archive: {zip_path}")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(target_path):
                for f in files:
                    file_path = Path(root) / f
                    arcname = file_path.relative_to(target_path)
                    zipf.write(file_path, arcname)
        print(f"[+] Release bundle ready: {zip_path}")

    return target_path

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "dist/diaclectics_release"
    export_clean_release(out)


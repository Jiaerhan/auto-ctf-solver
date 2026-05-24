"""Common utilities for auto-ctf-solver."""

from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path
from typing import Any


def detect_file_type(filepath: Path) -> str:
    """Run `file` command via python-magic or subprocess."""
    import subprocess
    try:
        result = subprocess.run(
            ["file", "-b", str(filepath)],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def get_file_hash(filepath: Path, algo: str = "sha256") -> str:
    """Get file hash."""
    h = hashlib.new(algo)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_strings(filepath: Path, min_length: int = 4) -> list[str]:
    """Extract printable strings from a file."""
    import subprocess
    try:
        result = subprocess.run(
            ["strings", "-n", str(min_length), str(filepath)],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout.splitlines()
    except Exception:
        return []


def search_flag_pattern(text: str) -> list[str]:
    """Search for flag patterns in text. Returns list of potential flags."""
    patterns = [
        r'flag\{[^}]+\}',
        r'FLAG\{[^}]+\}',
        r'ctf\{[^}]+\}',
        r'CTF\{[^}]+\}',
        r'[A-Za-z0-9_]{20,}={0,2}',  # Base64-like
        r'[0-9a-f]{32}',  # MD5
        r'[0-9a-f]{40}',  # SHA1
        r'[0-9a-f]{64}',  # SHA256
    ]
    matches = []
    for pat in patterns:
        matches.extend(re.findall(pat, text))
    return list(set(matches))


def save_json(data: Any, filepath: Path) -> None:
    """Save data as JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(filepath: Path) -> Any:
    """Load data from JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as filename."""
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()[:200]

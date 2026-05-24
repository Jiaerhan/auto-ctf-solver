"""Screenshot capture for writeup documentation."""

from __future__ import annotations

import subprocess
import time
from datetime import datetime
from pathlib import Path

from ..config.settings import settings


class ScreenshotManager:
    """Captures screenshots for writeup generation.

    Uses scrot+Xvfb for terminal screenshots, CutyCapt for web screenshots.
    """

    def __init__(self):
        self.screenshot_dir = settings.screenshot_dir
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def capture_terminal(self, name: str = "") -> Path:
        """Capture terminal screenshot using scrot inside Docker."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"term_{name or timestamp}_{timestamp}.png"
        filepath = self.screenshot_dir / filename

        from .docker import docker as dm

        code, _, err = dm.exec_cmd(
            f"DISPLAY=:99 scrot {filepath}",
            timeout=10,
        )
        if code != 0:
            # Fallback: try import display
            code2, _, _ = dm.exec_cmd(
                "DISPLAY=:99 import -window root /tmp/screenshot.png",
                timeout=10,
            )
            if code2 == 0:
                dm.copy_from("/tmp/screenshot.png", filepath)

        if filepath.exists():
            return filepath
        return None  # type: ignore[return-value]

    def capture_web(self, url: str, name: str = "") -> Path:
        """Capture web page screenshot using CutyCapt."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"web_{name or timestamp}_{timestamp}.png"
        filepath = self.screenshot_dir / filename

        from .docker import docker as dm

        code, _, err = dm.exec_cmd(
            f"cutycapt --url={url} --out=/tmp/web_cap.png --delay=2000",
            timeout=30,
        )
        if code == 0:
            dm.copy_from("/tmp/web_cap.png", filepath)
            if filepath.exists():
                return filepath

        return None  # type: ignore[return-value]

    def capture_all(self, label: str = "") -> list[Path]:
        """Capture both terminal and any web views. Returns list of screenshot paths."""
        screenshots = []
        term_shot = self.capture_terminal(f"{label}_term")
        if term_shot:
            screenshots.append(term_shot)
        return screenshots

    def list_screenshots(self) -> list[Path]:
        """List all screenshots taken in this session."""
        return sorted(self.screenshot_dir.glob("*.png"), key=lambda p: p.stat().st_mtime)


screenshots = ScreenshotManager()

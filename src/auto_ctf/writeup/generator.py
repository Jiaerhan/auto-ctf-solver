"""Writeup generator - produces .docx and Markdown CTF writeups with screenshots."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config.settings import settings
from ..knowledge.patterns import WRITEUP_SECTIONS
from ..tools.common import sanitize_filename
from ..tools.screenshot import screenshots


class WriteupGenerator:
    """Generates CTF writeup documents from solve results."""

    def __init__(self):
        self.output_dir = settings.output_dir / "writeups"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        challenge_name: str,
        category: str,
        result: dict[str, Any],
        formats: list[str] | None = None,
    ) -> Path:
        """Generate writeup in specified formats. Returns path to primary output."""
        formats = formats or settings.writeup_formats
        safe_name = sanitize_filename(f"{category}_{challenge_name}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Collect screenshots
        shots = screenshots.list_screenshots()

        # Build writeup data
        data = self._build_data(challenge_name, category, result, shots)

        output_path = None
        for fmt in formats:
            fmt = fmt.strip()
            if fmt == "docx":
                from .docx_writer import DocxWriter
                writer = DocxWriter()
                path = writer.write(data, self.output_dir / f"{safe_name}_{timestamp}.docx")
            elif fmt == "md":
                from .md_writer import MdWriter
                writer = MdWriter()
                path = writer.write(data, self.output_dir / f"{safe_name}_{timestamp}.md")
            else:
                continue
            if output_path is None:
                output_path = path

        return output_path or self.output_dir

    def generate_from_solve_log(
        self,
        solve_log: Path,
        challenge_name: str = "",
        category: str = "",
    ) -> Path:
        """Generate writeup from a saved solve log JSON file."""
        data = json.loads(solve_log.read_text(encoding="utf-8"))
        return self.generate(
            challenge_name=challenge_name or data.get("name", "challenge"),
            category=category or data.get("category", "unknown"),
            result=data,
        )

    def _build_data(
        self,
        name: str,
        category: str,
        result: dict[str, Any],
        shots: list[Path],
    ) -> dict:
        return {
            "name": name,
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "success": result.get("success", False),
            "flag": result.get("flag", ""),
            "approach": result.get("approach", ""),
            "steps": result.get("steps", []),
            "errors": result.get("errors", []),
            "duration": result.get("duration", 0),
            "screenshots": [str(s) for s in shots if s.exists()],
            "sections": WRITEUP_SECTIONS,
        }

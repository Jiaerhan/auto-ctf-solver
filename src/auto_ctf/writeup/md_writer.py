"""Markdown writeup writer."""

from __future__ import annotations

from pathlib import Path


class MdWriter:
    """Writes CTF writeups as Markdown files."""

    def write(self, data: dict, output_path: Path) -> Path:
        lines = []

        lines.append(f"# CTF Writeup: {data['name']}")
        lines.append("")
        lines.append(f"**Category:** {data['category']}  ")
        lines.append(f"**Date:** {data['timestamp'][:10]}  ")
        if data.get("duration"):
            lines.append(f"**Duration:** {data['duration']:.1f}s  ")
        lines.append("")

        # Challenge Info
        lines.append("## Challenge Information")
        lines.append(f"- **Category:** {data['category']}")
        if data.get("flag"):
            lines.append(f"- **Flag:** `{data['flag']}`")
        lines.append("")

        # Approach
        lines.append("## Solution Approach")
        lines.append(data.get("approach", "No approach recorded."))
        lines.append("")

        # Steps
        lines.append("## Solution Steps")
        for i, step in enumerate(data.get("steps", []), 1):
            lines.append(f"### Step {i}")
            lines.append("")
            lines.append(step[:3000])
            lines.append("")

        # Flag
        if data.get("flag"):
            lines.append("## Flag")
            lines.append("")
            lines.append(f"```\n{data['flag']}\n```")
            lines.append("")

        # Screenshots
        screenshots = data.get("screenshots", [])
        if screenshots:
            lines.append("## Screenshots")
            lines.append("")
            for shot in screenshots:
                shot_path = Path(shot)
                if shot_path.exists():
                    rel_path = shot_path.name
                    lines.append(f"![{rel_path}]({rel_path})")
                    lines.append(f"*{rel_path}*")
                    lines.append("")
                else:
                    lines.append(f"- [Screenshot: {shot}]")
                    lines.append("")

        # Errors
        if data.get("errors"):
            lines.append("## Errors / Notes")
            lines.append("")
            for err in data["errors"]:
                lines.append(f"- {err}")
            lines.append("")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

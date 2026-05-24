"""Base agent class for all CTF specialist agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config.settings import settings
from ..knowledge.patterns import SolvePattern, UNIVERSAL_TACTICS, SAFETY_RULES
from ..tools.docker import docker
from ..tools.screenshot import screenshots


@dataclass
class ChallengeInfo:
    """Information about a CTF challenge."""
    name: str
    category: str = "unknown"
    files: list[Path] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    description: str = ""
    points: int = 0
    host: str = ""
    port: int = 0


@dataclass
class SolveResult:
    """Result of a solving attempt."""
    success: bool
    flag: str = ""
    category: str = ""
    approach: str = ""
    steps: list[str] = field(default_factory=list)
    screenshots: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    raw_output: str = ""


class BaseAgent(ABC):
    """Base class for all CTF specialist agents."""

    category: str = "unknown"
    patterns: list[SolvePattern] = []

    def __init__(self):
        self.docker = docker
        self.screenshots = screenshots
        self._start_time: float = 0.0

    @abstractmethod
    def solve(self, challenge: ChallengeInfo) -> SolveResult:
        """Execute the solve plan for this challenge."""

    def build_system_prompt(self, challenge: ChallengeInfo) -> str:
        """Build a specialized system prompt for Claude with all learned patterns."""
        patterns_text = "\n".join(
            f"- [{p.priority.value}] {p.name}: {p.prompt_hint}"
            for p in sorted(self.patterns, key=lambda p: p.priority.value)
        )
        tactics_text = "\n".join(f"- {t}" for t in UNIVERSAL_TACTICS)
        safety_text = "\n".join(f"- {r}" for r in SAFETY_RULES)

        return f"""You are a {self.category.upper()} CTF specialist. Solve this challenge systematically.

## Challenge
Name: {challenge.name}
Category: {challenge.category}
Files: {[str(f) for f in challenge.files]}
URLs: {challenge.urls}
Description: {challenge.description}
Points: {challenge.points}

## Solve Patterns (ordered by priority)
{patterns_text}

## Universal Tactics
{tactics_text}

## Safety Rules
{safety_text}

## Output Format
When you find the flag, output: FLAG_FOUND: <flag>
If you're stuck after trying multiple approaches, output: STUCK: <reason>
Screenshot key findings as you go.
"""

    def create_work_dir(self, challenge: ChallengeInfo) -> Path:
        """Create a working directory for this challenge."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = settings.work_dir / f"{challenge.category}_{challenge.name}_{timestamp}"
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir

    def record_step(self, step: str) -> None:
        """Record a solve step with timestamp."""
        pass  # To be integrated with progress tracking

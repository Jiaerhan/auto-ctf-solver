"""Central configuration for auto-ctf-solver."""

import os
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application settings loaded from environment and defaults."""

    # Anthropic API
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    anthropic_model: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    )

    # Docker
    docker_container: str = field(
        default_factory=lambda: os.getenv("CTF_DOCKER_CONTAINER", "ctf-tools-agent2")
    )
    docker_timeout: int = field(
        default_factory=lambda: int(os.getenv("CTF_DOCKER_TIMEOUT", "300"))
    )

    # Paths
    work_dir: Path = field(
        default_factory=lambda: Path(os.getenv("CTF_WORK_DIR", "D:/CTF/exam/agent2"))
    )
    output_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("CTF_OUTPUT_DIR", "D:/CTF/exam/agent2/output")
        )
    )
    screenshot_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("CTF_SCREENSHOT_DIR", "D:/CTF/exam/agent2/screenshots")
        )
    )

    # Solver
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("CTF_MAX_RETRIES", "3"))
    )
    timeout_minutes: int = field(
        default_factory=lambda: int(os.getenv("CTF_TIMEOUT_MINUTES", "30"))
    )

    # Rate limiting (compliance)
    rate_limit_delay: float = field(
        default_factory=lambda: float(os.getenv("CTF_RATE_LIMIT_DELAY", "1.0"))
    )
    max_threads: int = field(
        default_factory=lambda: int(os.getenv("CTF_MAX_THREADS", "2"))
    )

    # Writeup
    writeup_formats: list[str] = field(
        default_factory=lambda: os.getenv("CTF_WRITEUP_FORMATS", "docx,md").split(",")
    )

    def __post_init__(self):
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()

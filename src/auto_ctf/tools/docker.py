"""Docker container management for isolated CTF solving."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional

from ..config.settings import settings


class DockerManager:
    """Manages the ctf-tools-agent2 Docker container for isolated execution."""

    def __init__(self, container_name: str | None = None):
        self.container = container_name or settings.docker_container
        self.timeout = settings.docker_timeout

    def is_running(self) -> bool:
        """Check if the container is running."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", self.container],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() == "true"
        except Exception:
            return False

    def start(self) -> bool:
        """Start the container if not running."""
        if self.is_running():
            return True
        try:
            subprocess.run(
                ["docker", "start", self.container],
                capture_output=True, text=True, timeout=30, check=True,
            )
            time.sleep(2)  # Wait for container to fully start
            return self.is_running()
        except subprocess.CalledProcessError:
            return False

    def stop(self) -> bool:
        """Stop the container."""
        try:
            subprocess.run(
                ["docker", "stop", self.container],
                capture_output=True, text=True, timeout=30, check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def exec_cmd(
        self,
        cmd: str | list[str],
        workdir: str = "/home/ctf/work",
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Execute a command inside the container.

        Returns (returncode, stdout, stderr).
        """
        if isinstance(cmd, str):
            cmd = ["/bin/bash", "-c", cmd]

        docker_cmd = [
            "docker", "exec",
            "-w", workdir,
            self.container,
            *cmd,
        ]

        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True, text=True,
                timeout=timeout or self.timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout or self.timeout}s"

    def copy_to(self, src: Path, dst: str = "/home/ctf/work/") -> bool:
        """Copy a file from host to container."""
        try:
            subprocess.run(
                ["docker", "cp", str(src), f"{self.container}:{dst}"],
                capture_output=True, text=True, timeout=30, check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def copy_from(self, src: str, dst: Path) -> bool:
        """Copy a file from container to host."""
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["docker", "cp", f"{self.container}:{src}", str(dst)],
                capture_output=True, text=True, timeout=30, check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def file_exists(self, path: str) -> bool:
        """Check if a file exists inside the container."""
        code, _, _ = self.exec_cmd(f"test -f {path}")
        return code == 0

    def run_python(self, script: str, timeout: int | None = None) -> tuple[int, str, str]:
        """Run a Python script inside the container using the known Python path."""
        cmd = "/home/ctf/.python-3.9/bin/python3.9 -c " + subprocess.list2cmdline([script])
        return self.exec_cmd(cmd, timeout=timeout)

    def cleanup_workdir(self) -> None:
        """Clean up the work directory in the container."""
        self.exec_cmd("rm -rf /home/ctf/work/*")


docker = DockerManager()

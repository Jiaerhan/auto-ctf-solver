"""Specialist CTF agents for each category.

Each specialist loads category-specific solve patterns and executes them
via Claude Code orchestration in Docker containers.
"""

from __future__ import annotations

import subprocess
import json
import time
from datetime import datetime
from pathlib import Path

from .base import BaseAgent, ChallengeInfo, SolveResult
from ..knowledge.patterns import CATEGORY_PATTERNS
from ..config.settings import settings
from ..tools.docker import docker
from ..tools.screenshot import screenshots
from ..tools.common import save_json, sanitize_filename


class PwnAgent(BaseAgent):
    category = "pwn"
    patterns = CATEGORY_PATTERNS["pwn"]

    def solve(self, challenge: ChallengeInfo) -> SolveResult:
        return self._execute_solve(challenge)

    def _execute_solve(self, challenge: ChallengeInfo) -> SolveResult:
        result = SolveResult(success=False, category="pwn")
        start = time.time()
        work_dir = self.create_work_dir(challenge)

        try:
            # Step 1: Copy files to Docker
            for f in challenge.files:
                docker.copy_to(f, f"/home/ctf/work/{f.name}")

            # Step 2: Initial reconnaissance
            for f in challenge.files:
                _, out, _ = docker.exec_cmd(f"file /home/ctf/work/{f.name}")
                result.steps.append(f"file: {out.strip()}")
                _, out, _ = docker.exec_cmd(f"strings /home/ctf/work/{f.name}")
                result.steps.append(f"strings done ({len(out.splitlines())} lines)")

            # Step 3: Security check
            if challenge.files:
                _, out, _ = docker.exec_cmd(f"checksec --file=/home/ctf/work/{challenge.files[0].name} 2>/dev/null || echo 'checksec not available'")
                result.steps.append(f"checksec: {out.strip()}")

            # Step 4: Build and invoke Claude prompt
            prompt = self.build_system_prompt(challenge)
            prompt += f"\n\nWorking directory: /home/ctf/work/\nFiles available: {[f.name for f in challenge.files]}"

            # Write prompt for Claude Code
            prompt_file = work_dir / "prompt.txt"
            prompt_file.write_text(prompt)

            result.raw_output = prompt
            result.approach = "PWN multi-pattern approach (strings → checksec → exploit dev)"

        except Exception as e:
            result.errors.append(str(e))
        finally:
            result.duration_seconds = time.time() - start

        return result


class WebAgent(BaseAgent):
    category = "web"
    patterns = CATEGORY_PATTERNS["web"]

    def solve(self, challenge: ChallengeInfo) -> SolveResult:
        result = SolveResult(success=False, category="web")
        start = time.time()
        work_dir = self.create_work_dir(challenge)

        try:
            result.steps.append(f"Target URLs: {challenge.urls}")
            if challenge.host:
                result.steps.append(f"Target host: {challenge.host}:{challenge.port}")

            # Initial HTTP recon
            for url in challenge.urls:
                code, out, _ = docker.exec_cmd(
                    f"curl -sI '{url}' 2>&1 | head -20",
                    timeout=15,
                )
                result.steps.append(f"HTTP headers {url}: {out.strip()[:500]}")

            prompt = self.build_system_prompt(challenge)
            prompt_file = work_dir / "prompt.txt"
            prompt_file.write_text(prompt)

            result.raw_output = prompt
            result.approach = "Web multi-pattern approach (source → SSTI → SQLi → SSRF → JWT → Deser)"

        except Exception as e:
            result.errors.append(str(e))
        finally:
            result.duration_seconds = time.time() - start

        return result


class ReverseAgent(BaseAgent):
    category = "reverse"
    patterns = CATEGORY_PATTERNS["reverse"]

    def solve(self, challenge: ChallengeInfo) -> SolveResult:
        result = SolveResult(success=False, category="reverse")
        start = time.time()
        work_dir = self.create_work_dir(challenge)

        try:
            for f in challenge.files:
                docker.copy_to(f, f"/home/ctf/work/{f.name}")

                # Run strings and grep for flag
                _, out, _ = docker.exec_cmd(
                    f"strings /home/ctf/work/{f.name} | grep -iE 'flag|ctf|{{' || echo 'no obvious flag strings'"
                )
                result.steps.append(f"Flag strings in {f.name}: {out.strip()[:300]}")

                # Check for UPX
                _, out, _ = docker.exec_cmd(
                    f"strings /home/ctf/work/{f.name} | grep -i upx || echo 'no UPX'"
                )
                if "UPX" in out:
                    result.steps.append("Detected UPX packer, attempting unpack...")
                    docker.exec_cmd(f"python3 -c \"import sys; data=open('/home/ctf/work/{f.name}','rb').read(); data=data.replace(b'UPX0',b'.upx0').replace(b'UPX1',b'.upx1'); open('/home/ctf/work/{f.name}','wb').write(data)\"")

                # Android APK handling
                if f.suffix == '.apk':
                    result.steps.append("Android APK detected, extracting...")
                    docker.exec_cmd(f"apktool d /home/ctf/work/{f.name} -o /home/ctf/work/apk_out 2>&1 || true")
                    _, out, _ = docker.exec_cmd("grep -ri 'flag' /home/ctf/work/apk_out/smali/ 2>/dev/null | head -10 || echo 'no flag in smali'")
                    result.steps.append(f"Smali flag search: {out.strip()[:500]}")

            prompt = self.build_system_prompt(challenge)
            prompt_file = work_dir / "prompt.txt"
            prompt_file.write_text(prompt)

            result.raw_output = prompt
            result.approach = "Reverse multi-pattern approach (strings → flag grep → deobfuscate → Python replicate)"

        except Exception as e:
            result.errors.append(str(e))
        finally:
            result.duration_seconds = time.time() - start

        return result


class CryptoAgent(BaseAgent):
    category = "crypto"
    patterns = CATEGORY_PATTERNS["crypto"]

    def solve(self, challenge: ChallengeInfo) -> SolveResult:
        result = SolveResult(success=False, category="crypto")
        start = time.time()
        work_dir = self.create_work_dir(challenge)

        try:
            for f in challenge.files:
                docker.copy_to(f, f"/home/ctf/work/{f.name}")

                # Check for common crypto file types and constants
                _, out, _ = docker.exec_cmd(f"strings /home/ctf/work/{f.name} | head -50")
                result.steps.append(f"File content preview: {out.strip()[:300]}")

            prompt = self.build_system_prompt(challenge)
            prompt_file = work_dir / "prompt.txt"
            prompt_file.write_text(prompt)

            result.raw_output = prompt
            result.approach = "Crypto multi-pattern approach (RSA → AES mode → PRNG → Lattice → Custom hash)"

        except Exception as e:
            result.errors.append(str(e))
        finally:
            result.duration_seconds = time.time() - start

        return result


class MiscAgent(BaseAgent):
    category = "misc"
    patterns = CATEGORY_PATTERNS["misc"]

    def solve(self, challenge: ChallengeInfo) -> SolveResult:
        result = SolveResult(success=False, category="misc")
        start = time.time()
        work_dir = self.create_work_dir(challenge)

        try:
            for f in challenge.files:
                docker.copy_to(f, f"/home/ctf/work/{f.name}")

                # Run file detection
                _, out, _ = docker.exec_cmd(f"file /home/ctf/work/{f.name}")
                result.steps.append(f"file type: {out.strip()}")

                # Quick check for zero-width characters
                _, out, _ = docker.exec_cmd(
                    f"cat /home/ctf/work/{f.name} | python3 -c "
                    f"\"import sys; d=sys.stdin.read(); "
                    f"print(f'zero-width chars found: {sum(1 for c in d if ord(c) in [0x200b,0x200c,0x200d,0x200e,0x200f,0xfeff,0x2060,0x2061,0x2062,0x2063,0x2064])}')\" "
                    f"2>&1 || echo 'check failed'"
                )
                if "zero-width chars found:" in out:
                    result.steps.append(f"Zero-width check: {out.strip()}")

                # Check for PK header after PNG IEND
                _, out, _ = docker.exec_cmd(
                    f"python3 -c \"data=open('/home/ctf/work/{f.name}','rb').read(); "
                    f"import re; "
                    f"pk_positions=[m.start() for m in re.finditer(b'PK\\\\x03\\\\x04',data)]; "
                    f"print(f'PK headers: {pk_positions}')\" 2>&1 || echo 'check failed'"
                )
                if "PK headers:" in out:
                    result.steps.append(f"PK header check: {out.strip()}")

            prompt = self.build_system_prompt(challenge)
            prompt_file = work_dir / "prompt.txt"
            prompt_file.write_text(prompt)

            result.raw_output = prompt
            result.approach = "MISC multi-pattern approach (unzip → file type → visual observe → stego)"

        except Exception as e:
            result.errors.append(str(e))
        finally:
            result.duration_seconds = time.time() - start

        return result


class MobileAgent(BaseAgent):
    category = "mobile"
    patterns = CATEGORY_PATTERNS["mobile"]

    def solve(self, challenge: ChallengeInfo) -> SolveResult:
        result = SolveResult(success=False, category="mobile")
        start = time.time()
        work_dir = self.create_work_dir(challenge)

        try:
            for f in challenge.files:
                docker.copy_to(f, f"/home/ctf/work/{f.name}")

                if f.suffix == '.apk':
                    # Decompile and search for flags in smali
                    result.steps.append("Decompiling APK...")
                    docker.exec_cmd(f"apktool d /home/ctf/work/{f.name} -o /home/ctf/work/apk_out 2>&1")

                    _, out, _ = docker.exec_cmd(
                        "grep -riE 'flag\\{|ctf\\{|FLAG\\{' /home/ctf/work/apk_out/ 2>/dev/null | head -10 || echo 'no flag in APK'"
                    )
                    result.steps.append(f"Flag search: {out.strip()[:300]}")

                if f.suffix in ['.so', '.dylib']:
                    # Native library analysis
                    _, out, _ = docker.exec_cmd(f"objdump -T /home/ctf/work/{f.name} 2>&1 | head -30 || echo 'objdump failed'")
                    result.steps.append(f"Native exports: {out.strip()[:300]}")

            prompt = self.build_system_prompt(challenge)
            prompt_file = work_dir / "prompt.txt"
            prompt_file.write_text(prompt)

            result.raw_output = prompt
            result.approach = "Mobile multi-pattern (apktool → smali flag search → .so analysis → Python replicate)"

        except Exception as e:
            result.errors.append(str(e))
        finally:
            result.duration_seconds = time.time() - start

        return result


# Agent registry
AGENTS: dict[str, type[BaseAgent]] = {
    "pwn": PwnAgent,
    "web": WebAgent,
    "reverse": ReverseAgent,
    "crypto": CryptoAgent,
    "misc": MiscAgent,
    "mobile": MobileAgent,
}

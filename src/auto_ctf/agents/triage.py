"""Triage agent - identifies challenge type and routes to specialist."""

from __future__ import annotations

import re
from pathlib import Path

from ..knowledge.patterns import TRIAGE_RULES, CATEGORY_PATTERNS
from ..tools.common import detect_file_type, extract_strings
from .base import ChallengeInfo


class TriageAgent:
    """Analyzes challenge files/description to determine the CTF category."""

    def identify(self, challenge: ChallengeInfo) -> ChallengeInfo:
        """Identify the challenge category and update the ChallengeInfo."""
        scores: dict[str, float] = {}

        # Score based on file extensions and types
        for f in challenge.files:
            if not f.exists():
                continue
            ext = f.suffix.lower()
            file_type = detect_file_type(f)

            for rule in TRIAGE_RULES:
                # Check file extension
                if any(ext == f".{ind}" or ext == ind for ind in rule.indicators):
                    scores[rule.category] = scores.get(rule.category, 0) + rule.weight * 2

                # Check file type (magic bytes detection)
                for ind in rule.indicators:
                    if ind.lower() in file_type.lower():
                        scores[rule.category] = scores.get(rule.category, 0) + rule.weight

        # Score based on description keywords
        desc_lower = challenge.description.lower()
        for rule in TRIAGE_RULES:
            for kw in rule.keywords:
                if kw.lower() in desc_lower:
                    scores[rule.category] = scores.get(rule.category, 0) + rule.weight

        # Score based on URL patterns
        for url in challenge.urls:
            url_lower = url.lower()
            for rule in TRIAGE_RULES:
                for kw in rule.keywords:
                    if kw.lower() in url_lower:
                        scores[rule.category] = scores.get(rule.category, 0) + rule.weight * 0.5

        # Check strings in binary files for category hints
        for f in challenge.files:
            if f.suffix in ['.exe', '.elf', '.bin', '.so', '.dll', '']:
                strings = extract_strings(f)
                text = ' '.join(strings).lower()

                # PWN indicators in binary
                if any(s in text for s in ['/bin/sh', 'system', 'execve', 'stack', 'buffer', 'rop', 'got', 'plt']):
                    scores['pwn'] = scores.get('pwn', 0) + 3

                # Reverse indicators
                if any(s in text for s in ['correct', 'wrong', 'password', 'flag is', 'congratulations', 'license']):
                    scores['reverse'] = scores.get('reverse', 0) + 2

                # Crypto constants
                if any(s in text for s in ['0x9e3779b9', 'aes', 'rsa', 'md5', 'sha256', '0x67452301']):
                    scores['crypto'] = scores.get('crypto', 0) + 2

        # Determine best category
        if not scores:
            challenge.category = "unknown"
            return challenge

        best = max(scores, key=lambda k: scores[k])
        challenge.category = best
        return challenge

    def get_confidence(self, challenge: ChallengeInfo) -> float:
        """Return confidence level for the identified category (0-1)."""
        scores: dict[str, float] = {}
        desc_lower = challenge.description.lower()

        for rule in TRIAGE_RULES:
            count = sum(1 for kw in rule.keywords if kw.lower() in desc_lower)
            if count > 0:
                scores[rule.category] = scores.get(rule.category, 0) + count

        if not scores or challenge.category not in scores:
            return 0.3  # Low confidence default

        total = sum(scores.values())
        return min(scores[challenge.category] / total, 1.0)

    def format_triage_for_prompt(self, challenge: ChallengeInfo) -> str:
        """Format triage results for consumption by specialist agent."""
        patterns = CATEGORY_PATTERNS.get(challenge.category, [])
        confidence = self.get_confidence(challenge)

        lines = [
            f"## Triage Result",
            f"Category: {challenge.category.upper()}",
            f"Confidence: {confidence:.0%}",
            "",
        ]

        if patterns:
            lines.append("### Suggested Approach Order")
            for i, p in enumerate(sorted(patterns, key=lambda p: p.priority.value), 1):
                lines.append(f"{i}. [{p.priority.value.upper()}] {p.name}: {p.description}")

        return "\n".join(lines)


triage = TriageAgent()

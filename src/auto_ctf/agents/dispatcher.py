"""Agent dispatcher - routes challenges to the appropriate specialist agent."""

from __future__ import annotations

from .base import ChallengeInfo, SolveResult
from .specialists import AGENTS
from .triage import triage


class Dispatcher:
    """Routes challenges to category-specific agents."""

    def __init__(self):
        self._agents: dict = {}

    def dispatch(self, challenge: ChallengeInfo) -> SolveResult:
        """Identify challenge type and dispatch to specialist."""
        # Triage
        if challenge.category == "unknown":
            challenge = triage.identify(challenge)

        confidence = triage.get_confidence(challenge)

        # Get or create specialist agent
        agent_cls = AGENTS.get(challenge.category)
        if not agent_cls:
            return SolveResult(
                success=False,
                category=challenge.category,
                errors=[f"No agent for category: {challenge.category}"],
            )

        agent = agent_cls()

        # Execute solve
        result = agent.solve(challenge)

        # Merge triage info
        result.category = challenge.category

        return result

    def solve_with_fallback(self, challenge: ChallengeInfo) -> SolveResult:
        """Try primary category, fall back to MISC if it fails."""
        result = self.dispatch(challenge)

        if not result.success and challenge.category != "misc":
            # Fallback: try as MISC
            challenge.category = "misc"
            fallback = self.dispatch(challenge)
            if fallback.success:
                return fallback
            # Merge errors
            result.errors.extend(f"Fallback MISC also failed: {'; '.join(fallback.errors)}")

        return result


dispatcher = Dispatcher()

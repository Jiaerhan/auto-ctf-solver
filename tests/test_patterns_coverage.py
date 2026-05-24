"""Test that all specialist agents load solve patterns and knowledge base has full coverage.

These tests verify the knowledge base integrity — every category has patterns,
every pattern has required fields, and every agent can be instantiated and queried.
"""

import pytest

from src.auto_ctf.knowledge.patterns import (
    CATEGORY_PATTERNS,
    TRIAGE_RULES,
    UNIVERSAL_TACTICS,
    SAFETY_RULES,
    WRITEUP_SECTIONS,
    SolvePattern,
    TriageRule,
    Priority,
)
from src.auto_ctf.agents.specialists import (
    PwnAgent,
    WebAgent,
    ReverseAgent,
    CryptoAgent,
    MiscAgent,
    MobileAgent,
    AGENTS,
)
from src.auto_ctf.agents.base import ChallengeInfo


class TestKnowledgeBaseIntegrity:
    """Verify the knowledge base data is complete and well-formed."""

    def test_all_categories_have_patterns(self):
        """Each of the 6 categories must have at least 1 solve pattern."""
        for category, patterns in CATEGORY_PATTERNS.items():
            assert len(patterns) > 0, f"Category '{category}' has no patterns"

    def test_category_count(self):
        """There must be exactly 6 categories."""
        assert len(CATEGORY_PATTERNS) == 6, f"Expected 6 categories, got {len(CATEGORY_PATTERNS)}"

    def test_total_pattern_count(self):
        """Total patterns across all categories should meet minimum threshold."""
        total = sum(len(p) for p in CATEGORY_PATTERNS.values())
        assert total >= 50, f"Expected >= 50 total patterns, got {total}"

    def test_every_pattern_has_required_fields(self):
        """Every SolvePattern must have non-empty name, description, priority, tools, prompt_hint."""
        for category, patterns in CATEGORY_PATTERNS.items():
            for p in patterns:
                assert p.name, f"Empty name in {category} pattern: {p}"
                assert p.description, f"Empty description in {category}/{p.name}"
                assert isinstance(p.priority, Priority), f"Invalid priority in {category}/{p.name}"
                assert len(p.tools) > 0, f"No tools listed in {category}/{p.name}"
                assert p.prompt_hint, f"Empty prompt_hint in {category}/{p.name}"

    def test_every_pattern_has_unique_name_within_category(self):
        """Pattern names must be unique within each category."""
        for category, patterns in CATEGORY_PATTERNS.items():
            names = [p.name for p in patterns]
            assert len(names) == len(set(names)), f"Duplicate names in {category}: {[n for n in names if names.count(n) > 1]}"

    def test_triage_rules_exist(self):
        """There must be triage rules for routing challenges."""
        assert len(TRIAGE_RULES) > 0, "No triage rules defined"

    def test_triage_rules_cover_all_categories(self):
        """Every category in CATEGORY_PATTERNS should have at least one TriageRule."""
        categories_with_rules = {r.category for r in TRIAGE_RULES}
        for category in CATEGORY_PATTERNS:
            assert category in categories_with_rules, f"No triage rule for category '{category}'"

    def test_universal_tactics_exist(self):
        """Universal tactics list must be non-empty."""
        assert len(UNIVERSAL_TACTICS) >= 5, f"Expected >= 5 universal tactics, got {len(UNIVERSAL_TACTICS)}"

    def test_safety_rules_exist(self):
        """Safety rules must cover common constraints."""
        safety_text = " ".join(SAFETY_RULES).lower()
        required_topics = ["rate", "docker", "authorized"]
        for topic in required_topics:
            assert topic in safety_text, f"Safety rules missing '{topic}'"

    def test_writeup_sections_exist(self):
        """Writeup template must have the 7 standard sections."""
        section_names = [s[0] for s in WRITEUP_SECTIONS]
        assert len(section_names) >= 6, f"Expected >= 6 writeup sections, got {len(section_names)}"
        assert "Challenge Info" in section_names
        assert "Flag" in section_names


class TestPatternCoverageByCategory:
    """Per-category pattern coverage and agent instantiation tests."""

    @pytest.mark.parametrize("category,expected_min", [
        ("pwn", 8),
        ("web", 9),
        ("reverse", 9),
        ("crypto", 6),
        ("misc", 10),
        ("mobile", 3),
    ])
    def test_category_minimum_patterns(self, category, expected_min):
        """Each category meets its minimum pattern threshold."""
        patterns = CATEGORY_PATTERNS.get(category, [])
        assert len(patterns) >= expected_min, \
            f"Category '{category}' has {len(patterns)} patterns, expected >= {expected_min}"

    @pytest.mark.parametrize("category", list(CATEGORY_PATTERNS.keys()))
    def test_category_has_first_priority_pattern(self, category):
        """Each category must have at least one FIRST-priority pattern (immediate action)."""
        patterns = CATEGORY_PATTERNS[category]
        first_patterns = [p for p in patterns if p.priority == Priority.FIRST]
        assert len(first_patterns) >= 1, f"Category '{category}' has no FIRST-priority pattern"

    @pytest.mark.parametrize("category", list(CATEGORY_PATTERNS.keys()))
    def test_category_has_high_priority_patterns(self, category):
        """Each category must have at least 2 HIGH-priority patterns (core approaches)."""
        patterns = CATEGORY_PATTERNS[category]
        high_patterns = [p for p in patterns if p.priority == Priority.HIGH]
        assert len(high_patterns) >= 2, f"Category '{category}' has only {len(high_patterns)} HIGH-priority patterns"


class TestAgentInstantiation:
    """Verify all agents can be instantiated and load their patterns."""

    AGENT_CLASSES = {
        "pwn": PwnAgent,
        "web": WebAgent,
        "reverse": ReverseAgent,
        "crypto": CryptoAgent,
        "misc": MiscAgent,
        "mobile": MobileAgent,
    }

    @pytest.mark.parametrize("category,agent_cls", list(AGENT_CLASSES.items()))
    def test_agent_instantiation(self, category, agent_cls):
        """Agent can be instantiated without error."""
        agent = agent_cls()
        assert agent is not None
        assert agent.category == category

    @pytest.mark.parametrize("category,agent_cls", list(AGENT_CLASSES.items()))
    def test_agent_loads_patterns(self, category, agent_cls):
        """Agent loads at least one solve pattern from knowledge base."""
        agent = agent_cls()
        assert len(agent.patterns) > 0, f"Agent '{category}' has no patterns loaded"
        # Verify patterns are SolvePattern instances
        for p in agent.patterns:
            assert isinstance(p, SolvePattern), f"Non-SolvePattern in {category}: {type(p)}"

    @pytest.mark.parametrize("category,agent_cls", list(AGENT_CLASSES.items()))
    def test_agent_builds_prompt(self, category, agent_cls):
        """Agent can build a system prompt for a challenge without crashing."""
        agent = agent_cls()
        challenge = ChallengeInfo(
            name=f"test_{category}",
            category=category,
            description=f"Test {category} challenge",
        )
        prompt = agent.build_system_prompt(challenge)
        assert isinstance(prompt, str)
        assert len(prompt) > 100, f"Prompt too short for {category}: {len(prompt)} chars"
        assert challenge.name in prompt
        assert category.upper() in prompt

    def test_agent_registry_complete(self):
        """AGENTS dict maps all 6 categories to their classes."""
        assert len(AGENTS) == 6, f"Expected 6 agents in registry, got {len(AGENTS)}"
        for category in CATEGORY_PATTERNS:
            assert category in AGENTS, f"Category '{category}' missing from AGENTS registry"

    def test_agent_registry_classes_match(self):
        """AGENTS dict values match the expected agent classes."""
        for category, cls in self.AGENT_CLASSES.items():
            assert AGENTS[category] is cls, f"Mismatch for {category}: expected {cls.__name__}"


class TestTriageCoverage:
    """Verify triage rules provide adequate coverage."""

    def test_triage_rule_weights_summary(self):
        """Check total weight distribution across categories."""
        from collections import Counter
        category_counts = Counter(r.category for r in TRIAGE_RULES)
        assert "pwn" in category_counts, "No PWN triage rules"
        assert "web" in category_counts, "No Web triage rules"
        assert "reverse" in category_counts, "No Reverse triage rules"
        assert "crypto" in category_counts, "No Crypto triage rules"
        assert "misc" in category_counts, "No MISC triage rules"
        assert "mobile" in category_counts, "No Mobile triage rules"

    def test_triage_keywords_not_empty(self):
        """Every triage rule must have at least one keyword."""
        for rule in TRIAGE_RULES:
            assert len(rule.keywords) > 0, f"TriageRule for {rule.category} has no keywords"

    def test_triage_indicators_not_empty(self):
        """Every triage rule must have at least one indicator."""
        for rule in TRIAGE_RULES:
            assert len(rule.indicators) > 0, f"TriageRule for {rule.category} has no indicators"

    def test_triage_weights_valid(self):
        """All triage rule weights must be between 0 and 1."""
        for rule in TRIAGE_RULES:
            assert 0 < rule.weight <= 1.0, f"Invalid weight {rule.weight} for {rule.category}/{rule.keywords[0]}"

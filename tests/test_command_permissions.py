#!/usr/bin/env python3
"""Unit tests for check_agent_rules.py command checking logic using pytest."""

import pytest

from src.check_rules import check_command


class TestDeniedCommands:
    """Test mechanism for denying commands. It should use search (partial match)."""

    def test_denied_partial_match(self):
        """Denied pattern by default matches anywhere in command."""
        rules = {"deny_commands": [{"pattern": "rm -rf", "reason": "Dangerous"}]}

        status, reason = check_command("echo 'test' && rm -rf /tmp", rules)

        assert status == "deny"
        assert reason == "Dangerous"

    def test_denied_exact_match(self):
        """Anchors can be used to check denied pattern for exact match."""
        rules = {
            "deny_commands": [{"pattern": "^rm -rf /$", "reason": "Root deletion"}]
        }

        status, reason = check_command("rm -rf /tmp", rules)

        assert status is None  # Not denied because pattern does not match exactly
        assert reason is None

    def test_denied_priority_over_allowed(self):
        """Denied commands have precedence before allowed."""
        rules = {
            "deny_commands": [{"pattern": "git push", "reason": "No pushing"}],
            "allow_commands": [{"pattern": "git push.*"}],
        }

        status, reason = check_command("git push origin main", rules)

        assert status == "deny"
        assert reason == "No pushing"


@pytest.fixture
def exact_rules():
    """Rules allowing exact command 'git push'."""
    return {"allow_commands": [{"pattern": "git push"}]}


@pytest.fixture
def wildcard_rules():
    """Rules allowing 'git commit' with any arguments."""
    return {"allow_commands": [{"pattern": "git commit.*"}]}


class TestAllowedCommands:
    """Test mechanism for allowing commands. It should check for full match."""

    def test_exact_match(self, exact_rules):
        status, _ = check_command("git push", exact_rules)
        assert status == "allow"

    def test_exact_no_match(self, exact_rules):
        status, _ = check_command("git push upstream feature", exact_rules)
        assert status is None

    def test_wildcard_match(self, wildcard_rules):
        status, _ = check_command("git commit -a", wildcard_rules)
        assert status == "allow"

    def test_wildcard_no_match(self, wildcard_rules):
        status, _ = check_command("GIT_AUTHOR=impostor git commit -a", wildcard_rules)
        assert status is None


class TestConfirmCommands:
    """Test mechanism for explicitly requesting permission from the user."""

    def test_confirm_exact_match(self):
        """Test that confirm command returns 'ask' decision."""
        rules = {
            "confirm_commands": [
                {
                    "pattern": "rm -rf.*",
                    "reason": "Destructive operation",
                }
            ]
        }

        status, reason = check_command("rm -rf /tmp/test", rules)

        assert status == "ask"
        assert reason == "Destructive operation"

    def test_confirm_priority_over_allowed(self):
        """Requiring confirmation has precedence over approval."""
        rules = {
            "allow_commands": [{"pattern": "git push.*"}],
            "confirm_commands": [{"pattern": "git push.*--force.*"}],
        }

        status, _ = check_command("git push --force", rules)

        assert status == "ask"

    def test_confirm_no_match(self):
        """Test that unmatched command returns None."""
        rules = {"confirm_commands": [{"pattern": "rm -rf.*"}]}

        status, reason = check_command("ls -la", rules)

        assert status is None
        assert reason is None


class TestPartialRules:
    """Test that check_command handles rules with missing sections."""

    def test_only_deny_commands(self):
        """Test rules with only deny_commands defined."""
        rules = {"deny_commands": [{"pattern": "rm -rf", "reason": "Dangerous"}]}

        # Should deny matching command
        status, reason = check_command("rm -rf /tmp", rules)
        assert status == "deny"
        assert reason == "Dangerous"

        # Should return None for non-matching command
        status, reason = check_command("ls -la", rules)
        assert status is None
        assert reason is None

    def test_empty_rules(self):
        """Test with completely empty rules - should return none for any command."""
        status, reason = check_command("any command", {})
        assert status is None
        assert reason is None

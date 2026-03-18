"""Tests for {cwd} variable substitution in command patterns."""

from src.check_rules import check_command


class TestCwdVariable:
    """Test {cwd} substitution in command patterns."""

    def test_cwd_substituted_in_deny_pattern(self):
        rules = {"deny_commands": [{"pattern": r"^cd {cwd} &&.*", "reason": "Redundant cd"}]}

        decision, reason = check_command("cd /my/project && pytest", rules, cwd="/my/project")

        assert decision == "deny"
        assert reason == "Redundant cd"

    def test_cwd_not_matched_when_different_path(self):
        rules = {"deny_commands": [{"pattern": r"^cd {cwd} &&.*"}]}

        decision, _ = check_command("cd /other/path && pytest", rules, cwd="/my/project")

        assert decision is None

    def test_cwd_substituted_in_allow_pattern(self):
        rules = {"allow_commands": [{"pattern": r"cd {cwd} && pytest.*"}]}

        decision, _ = check_command("cd /my/project && pytest -v", rules, cwd="/my/project")

        assert decision == "allow"

    def test_cwd_substituted_in_confirm_pattern(self):
        rules = {"confirm_commands": [{"pattern": r"cd {cwd} && git push.*"}]}

        decision, _ = check_command("cd /my/project && git push", rules, cwd="/my/project")

        assert decision == "ask"

    def test_cwd_with_special_regex_chars_in_path(self):
        """Dots and other special chars in cwd path are treated as literals."""
        rules = {"deny_commands": [{"pattern": r"^cd {cwd}.*"}]}

        # Should match the literal path (dot is not a wildcard)
        decision, _ = check_command("cd /my/proj.ect/foo && ls", rules, cwd="/my/proj.ect")
        assert decision == "deny"

        # Should NOT match a path where dot acts as a wildcard
        decision, _ = check_command("cd /my/projXect/foo && ls", rules, cwd="/my/proj.ect")
        assert decision is None

    def test_no_cwd_provided_leaves_pattern_unchanged(self):
        """Without cwd, {cwd} in pattern is left as-is and won't match normal commands."""
        rules = {"deny_commands": [{"pattern": r"^cd {cwd}.*"}]}

        decision, _ = check_command("cd /some/path && ls", rules, cwd=None)

        assert decision is None

    def test_pattern_without_cwd_variable_unaffected(self):
        rules = {"deny_commands": [{"pattern": "rm -rf"}]}

        decision, _ = check_command("rm -rf /tmp", rules, cwd="/my/project")

        assert decision == "deny"

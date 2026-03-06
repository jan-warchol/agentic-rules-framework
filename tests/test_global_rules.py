"""Tests for global rules loading and merging with project rules."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.rules import load_rules, _merge_rules


def write_rules(directory, rules):
    path = Path(directory) / "agent-rules.yaml"
    path.write_text(yaml.dump(rules))
    return path


class TestMergeRules:
    def test_both_none_returns_none(self):
        assert _merge_rules(None, None) is None

    def test_global_only(self):
        global_rules = {"deny_commands": [{"pattern": "rm -rf"}]}
        assert _merge_rules(global_rules, None) == global_rules

    def test_project_only(self):
        project_rules = {"deny_commands": [{"pattern": "git push"}]}
        assert _merge_rules(None, project_rules) == project_rules

    def test_merges_lists(self):
        global_rules = {"deny_commands": [{"pattern": "rm -rf"}]}
        project_rules = {"deny_commands": [{"pattern": "git push"}]}
        merged = _merge_rules(global_rules, project_rules)
        assert merged["deny_commands"] == [{"pattern": "rm -rf"}, {"pattern": "git push"}]

    def test_global_entries_come_first(self):
        global_rules = {"deny_commands": [{"pattern": "global"}]}
        project_rules = {"deny_commands": [{"pattern": "project"}]}
        merged = _merge_rules(global_rules, project_rules)
        assert merged["deny_commands"][0]["pattern"] == "global"
        assert merged["deny_commands"][1]["pattern"] == "project"

    def test_merges_disjoint_keys(self):
        global_rules = {"deny_commands": [{"pattern": "rm -rf"}]}
        project_rules = {"deny_edits": [{"path": "config.yaml"}]}
        merged = _merge_rules(global_rules, project_rules)
        assert "deny_commands" in merged
        assert "deny_edits" in merged

    def test_empty_project_rules(self):
        global_rules = {"deny_commands": [{"pattern": "rm -rf"}]}
        merged = _merge_rules(global_rules, {})
        assert merged["deny_commands"] == [{"pattern": "rm -rf"}]


class TestLoadRules:
    def test_project_rules_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_rules = {"deny_commands": [{"pattern": "git push"}]}
            write_rules(tmpdir, project_rules)

            with patch("platformdirs.user_config_dir", return_value="/nonexistent/path"):
                rules, base_dir = load_rules({"cwd": tmpdir})

            assert rules == project_rules
            assert base_dir == Path(tmpdir)

    def test_global_rules_only(self):
        with tempfile.TemporaryDirectory() as global_config_dir, \
             tempfile.TemporaryDirectory() as project_dir:
            global_rules = {"deny_commands": [{"pattern": "rm -rf"}]}
            write_rules(global_config_dir, global_rules)

            with patch("platformdirs.user_config_dir", return_value=global_config_dir):
                rules, base_dir = load_rules({"cwd": project_dir})

            assert rules == global_rules
            assert base_dir == Path(project_dir)

    def test_global_and_project_rules_merged(self):
        with (
            tempfile.TemporaryDirectory() as global_config_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            global_rules = {"deny_commands": [{"pattern": "rm -rf", "reason": "global"}]}
            project_rules = {"deny_commands": [{"pattern": "git push", "reason": "project"}]}
            write_rules(global_config_dir, global_rules)
            write_rules(project_dir, project_rules)

            with patch("platformdirs.user_config_dir", return_value=global_config_dir):
                rules, base_dir = load_rules({"cwd": project_dir})

            assert len(rules["deny_commands"]) == 2
            assert rules["deny_commands"][0]["reason"] == "global"
            assert rules["deny_commands"][1]["reason"] == "project"
            assert base_dir == Path(project_dir)

    def test_no_rules_anywhere_raises(self):
        with patch("platformdirs.user_config_dir", return_value="/nonexistent/global"):
            with pytest.raises(FileNotFoundError):
                load_rules({"cwd": "/nonexistent/project"})

    def test_explicit_rules_path_still_merged_with_global(self):
        with (
            tempfile.TemporaryDirectory() as global_config_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            global_rules = {"deny_commands": [{"pattern": "rm -rf"}]}
            project_rules = {"deny_commands": [{"pattern": "git push"}]}
            write_rules(global_config_dir, global_rules)
            explicit_path = write_rules(project_dir, project_rules)

            with patch("platformdirs.user_config_dir", return_value=global_config_dir):
                rules, base_dir = load_rules({}, rules_path_arg=str(explicit_path))

            assert len(rules["deny_commands"]) == 2

    def test_global_deny_edits_base_dir_is_project_cwd(self):
        """Relative deny_edits paths in global rules are resolved against the project
        CWD, so a rule like deny_edits: [agent-rules.yaml] protects the project's
        rules file, not the global config file."""
        with (
            tempfile.TemporaryDirectory() as global_config_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            global_rules = {"deny_edits": [{"path": "agent-rules.yaml"}]}
            project_rules = {"deny_commands": [{"pattern": "git push"}]}
            write_rules(global_config_dir, global_rules)
            write_rules(project_dir, project_rules)

            with patch("platformdirs.user_config_dir", return_value=global_config_dir):
                _, base_dir = load_rules({"cwd": project_dir})

            assert base_dir == Path(project_dir)

    def test_yml_extension_supported_globally(self):
        with tempfile.TemporaryDirectory() as global_config_dir:
            global_rules = {"deny_commands": [{"pattern": "rm -rf"}]}
            (Path(global_config_dir) / "agent-rules.yml").write_text(yaml.dump(global_rules))

            with patch("platformdirs.user_config_dir", return_value=global_config_dir):
                rules, _ = load_rules({"cwd": "/nonexistent/project"})

            assert rules == global_rules

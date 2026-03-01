#!/usr/bin/env python3
"""Tests for multi-tool format detection and output."""

import json
import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from convert import detect_tool_format, convert_tool_entry, VSCODE_COPILOT, COPILOT_CLI
from check_agent_rules import get_tool_format, output_decision


# --- Sample input data ---

VSCODE_ENTRY = {
    "timestamp": "2026-02-20T15:46:57.407Z",
    "hookEventName": "PreToolUse",
    "tool_name": "run_in_terminal",
    "tool_input": {"command": "echo hello"},
    "cwd": "/some/path",
}

COPILOT_CLI_ENTRY = {
    "timestamp": 1771452890214,
    "toolName": "bash",
    "toolArgs": '{"command": "echo hello", "description": "Print hello"}',
    "cwd": "/some/path",
}


class TestDetectToolFormat:
    def test_vscode_detected_by_hookEventName(self):
        assert detect_tool_format(VSCODE_ENTRY) == VSCODE_COPILOT

    def test_copilot_cli_detected_by_toolName(self):
        assert detect_tool_format(COPILOT_CLI_ENTRY) == COPILOT_CLI

    def test_unknown_format_returns_none(self):
        assert detect_tool_format({"foo": "bar"}) is None


class TestConvertToolEntry:
    def test_vscode_extracts_tool_name_and_command(self):
        result = convert_tool_entry(VSCODE_ENTRY)
        assert result["tool"] == "run_in_terminal"
        assert result["args"]["command"] == "echo hello"
        assert result["cwd"] == "/some/path"

    def test_copilot_cli_extracts_tool_name_and_command(self):
        result = convert_tool_entry(COPILOT_CLI_ENTRY)
        assert result["tool"] == "bash"
        assert result["args"]["command"] == "echo hello"
        assert result["cwd"] == "/some/path"

    def test_copilot_cli_explicit_format(self):
        result = convert_tool_entry(COPILOT_CLI_ENTRY, tool_format=COPILOT_CLI)
        assert result["tool"] == "bash"

    def test_vscode_explicit_format(self):
        result = convert_tool_entry(VSCODE_ENTRY, tool_format=VSCODE_COPILOT)
        assert result["tool"] == "run_in_terminal"

    def test_copilot_cli_edit_tool_path(self):
        entry = {
            "timestamp": 1771453219699,
            "toolName": "edit",
            "toolArgs": '{"path": "/some/file.py", "old_str": "x", "new_str": "y"}',
            "cwd": "/some/path",
        }
        result = convert_tool_entry(entry)
        assert result["tool"] == "edit"
        assert result["args"]["path"] == "/some/file.py"


class TestGetToolFormat:
    def test_env_var_takes_highest_priority(self, monkeypatch):
        monkeypatch.setenv("AGENT_RULES_TOOL", COPILOT_CLI)
        # Even though input is vscode format and --tool says vscode, env var wins
        result = get_tool_format(VSCODE_ENTRY, tool_arg=VSCODE_COPILOT)
        assert result == COPILOT_CLI

    def test_tool_arg_takes_priority_over_autodetect(self, monkeypatch):
        monkeypatch.delenv("AGENT_RULES_TOOL", raising=False)
        # Input is vscode format but --tool says copilot-cli
        result = get_tool_format(VSCODE_ENTRY, tool_arg=COPILOT_CLI)
        assert result == COPILOT_CLI

    def test_autodetect_used_when_no_env_or_arg(self, monkeypatch):
        monkeypatch.delenv("AGENT_RULES_TOOL", raising=False)
        assert get_tool_format(VSCODE_ENTRY, tool_arg=None) == VSCODE_COPILOT
        assert get_tool_format(COPILOT_CLI_ENTRY, tool_arg=None) == COPILOT_CLI

    def test_raises_when_format_cannot_be_detected(self, monkeypatch):
        monkeypatch.delenv("AGENT_RULES_TOOL", raising=False)
        with pytest.raises(ValueError, match="Cannot detect tool format"):
            get_tool_format({"foo": "bar"}, tool_arg=None)


class TestOutputDecision:
    def test_vscode_output_structure(self, capsys):
        output_decision("deny", VSCODE_COPILOT, reason="Not allowed", context="Ask first")
        data = json.loads(capsys.readouterr().out)
        inner = data["hookSpecificOutput"]
        assert inner["hookEventName"] == "PreToolUse"
        assert inner["permissionDecision"] == "deny"
        assert inner["permissionDecisionReason"] == "Not allowed"
        assert inner["additionalContext"] == "Ask first"

    def test_copilot_cli_output_structure(self, capsys):
        output_decision("deny", COPILOT_CLI, reason="Not allowed")
        data = json.loads(capsys.readouterr().out)
        assert "hookSpecificOutput" not in data
        assert data["permissionDecision"] == "deny"
        assert data["permissionDecisionReason"] == "Not allowed"

    def test_copilot_cli_no_context_field(self, capsys):
        """copilot-cli output has no additionalContext field."""
        output_decision("deny", COPILOT_CLI, reason="r", context="c")
        data = json.loads(capsys.readouterr().out)
        assert "additionalContext" not in data

    def test_vscode_allow_decision(self, capsys):
        output_decision("allow", VSCODE_COPILOT)
        data = json.loads(capsys.readouterr().out)
        assert data["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_copilot_cli_allow_decision(self, capsys):
        output_decision("allow", COPILOT_CLI)
        data = json.loads(capsys.readouterr().out)
        assert data["permissionDecision"] == "allow"
        assert "permissionDecisionReason" not in data

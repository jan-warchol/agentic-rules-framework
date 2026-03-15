#!/usr/bin/env python3
"""Tests for multi-tool format detection and output."""

from src.normalize import (
    normalize_input,
    simplify_tool_call,
    VSCODE_COPILOT,
    COPILOT_CLI,
)


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


class TestNormalizeToolCall:
    def test_vscode_extracts_tool_name_and_args(self):
        result = normalize_input(VSCODE_ENTRY, VSCODE_COPILOT)
        assert result["tool"] == "run_in_terminal"
        assert result["args"] == {"command": "echo hello"}
        assert result["cwd"] == "/some/path"

    def test_copilot_cli_parses_json_args(self):
        result = normalize_input(COPILOT_CLI_ENTRY, COPILOT_CLI)
        assert result["tool"] == "bash"
        assert result["args"]["command"] == "echo hello"
        assert result["cwd"] == "/some/path"

    def test_copilot_cli_explicit_format(self):
        result = normalize_input(COPILOT_CLI_ENTRY, tool_format=COPILOT_CLI)
        assert result["tool"] == "bash"

    def test_vscode_explicit_format(self):
        result = normalize_input(VSCODE_ENTRY, tool_format=VSCODE_COPILOT)
        assert result["tool"] == "run_in_terminal"


class TestSimplifyToolCall:
    def test_extracts_command(self):
        normalized = normalize_input(VSCODE_ENTRY, VSCODE_COPILOT)
        result = simplify_tool_call(normalized)
        assert result["tool"] == "run_in_terminal"
        assert result["command"] == "echo hello"
        assert result["cwd"] == "/some/path"

    def test_copilot_cli_extracts_command(self):
        normalized = normalize_input(COPILOT_CLI_ENTRY, COPILOT_CLI)
        result = simplify_tool_call(normalized)
        assert result["command"] == "echo hello"

    def test_extracts_path(self):
        entry = {
            "timestamp": 1771453219699,
            "toolName": "edit",
            "toolArgs": '{"path": "/some/file.py", "old_str": "x", "new_str": "y"}',
            "cwd": "/some/path",
        }
        result = simplify_tool_call(normalize_input(entry, COPILOT_CLI))
        assert result["tool"] == "edit"
        assert result["paths"] == ["/some/file.py"]

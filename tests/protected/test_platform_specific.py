#!/usr/bin/env python3
"""Tests for platform detection and decision output formatting."""

import json
import pytest
from pathlib import Path

from src.platform_specific import (
    detect_platform,
    format_decision_output,
    VSCODE_COPILOT,
    COPILOT_CLI,
    CLAUDE_CODE,
)


def load_sample_inputs(file_path):
    """Load sample inputs from a JSONL file.

    Raises:
        ValueError: If the file is missing or contains no entries.
    """
    entries = []
    if file_path.exists():
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

    if not entries:
        raise ValueError(f"No sample inputs found in {file_path}")

    return entries


SAMPLE_DIR = Path(__file__).parent.parent / "sample-inputs"
VSCODE_COPILOT_SAMPLES = load_sample_inputs(SAMPLE_DIR / "vscode-copilot.jsonl")
CLAUDE_CODE_SAMPLES = load_sample_inputs(SAMPLE_DIR / "claude-code.jsonl")
COPILOT_CLI_SAMPLES = load_sample_inputs(SAMPLE_DIR / "copilot-cli.jsonl")

# Environment variable sets for each platform
VSCODE_COPILOT_ENV_VARS = [
    {"VSCODE_CWD": "/home/user"},
    {"VSCODE_PID": "12345"},
    {"VSCODE_IPC_HOOK": "/run/vscode.sock"},
]

CLAUDE_CODE_ENV_VARS = [
    {"CLAUDE_PROJECT_DIR": "/some/project"},
    {"CLAUDE_CODE_ENTRYPOINT": "cli"},
    {"CLAUDE_ENV_FILE": "/path/to/env"},
]

# Decision parametrization for format output tests
DECISIONS = [
    ("allow", None),
    ("deny", "Security risk"),
]


class TestDetection:
    """Tests for platform detection with sample inputs."""

    @pytest.mark.parametrize("environment", VSCODE_COPILOT_ENV_VARS)
    def test_vscode_envs(self, environment):
        """VSCode Copilot detected with different environment variables."""
        assert detect_platform(VSCODE_COPILOT_SAMPLES[0], environment) == VSCODE_COPILOT

    @pytest.mark.parametrize("environment", CLAUDE_CODE_ENV_VARS)
    def test_claude_envs(self, environment):
        """Claude Code detected with different environment variables."""
        assert detect_platform(CLAUDE_CODE_SAMPLES[0], environment) == CLAUDE_CODE

    @pytest.mark.parametrize("entry", VSCODE_COPILOT_SAMPLES)
    def test_vscode_samples(self, entry):
        """All VSCode sample inputs detected correctly."""
        assert detect_platform(entry, VSCODE_COPILOT_ENV_VARS[0]) == VSCODE_COPILOT

    @pytest.mark.parametrize("entry", CLAUDE_CODE_SAMPLES)
    def test_claude_samples(self, entry):
        """All Claude Code sample inputs detected correctly."""
        assert detect_platform(entry, CLAUDE_CODE_ENV_VARS[0]) == CLAUDE_CODE

    @pytest.mark.parametrize("entry", COPILOT_CLI_SAMPLES)
    def test_copilot_samples(self, entry):
        """All Copilot CLI sample inputs detected correctly."""
        assert detect_platform(entry, {}) == COPILOT_CLI

    def test_vscode_requires_both_key_and_env(self):
        """VSCode detection fails if key is present but env vars are missing."""
        vscode_entry = {"hookEventName": "PreToolUse"}
        with pytest.raises(ValueError, match="Cannot detect tool format"):
            detect_platform(vscode_entry, {})

    def test_claude_requires_both_key_and_env(self):
        """Claude Code detection fails if key is present but env vars are missing."""
        claude_entry = {"hook_event_name": "PreToolUse"}
        with pytest.raises(ValueError, match="Cannot detect tool format"):
            detect_platform(claude_entry, {})

    def test_raises_when_format_cannot_be_detected(self):
        """Raises when input has no recognizable tool keys."""
        with pytest.raises(ValueError, match="Cannot detect tool format"):
            detect_platform({"foo": "bar"}, {})


class TestFormatting:
    """Tests for formatting decision output with parameterized decisions."""

    @pytest.mark.parametrize("decision,reason", DECISIONS)
    def test_vscode_output(self, decision, reason):
        """VSCode output structure with various decisions."""
        data = format_decision_output(VSCODE_COPILOT, decision, reason=reason)
        inner = data["hookSpecificOutput"]
        assert inner["hookEventName"] == "PreToolUse"
        assert inner["permissionDecision"] == decision
        if reason:
            assert inner["permissionDecisionReason"] == reason
        else:
            assert "permissionDecisionReason" not in inner

    @pytest.mark.parametrize("decision,reason", DECISIONS)
    def test_copilot_output(self, decision, reason):
        """Copilot CLI output structure with various decisions."""
        data = format_decision_output(COPILOT_CLI, decision, reason=reason)
        assert "hookSpecificOutput" not in data
        assert data["permissionDecision"] == decision
        if reason:
            assert data["permissionDecisionReason"] == reason
        else:
            assert "permissionDecisionReason" not in data

    @pytest.mark.parametrize("decision,reason", DECISIONS)
    def test_claude_output(self, decision, reason):
        """Claude Code output structure with various decisions."""
        data = format_decision_output(CLAUDE_CODE, decision, reason=reason)
        inner = data["hookSpecificOutput"]
        assert inner["hookEventName"] == "PermissionRequest"
        assert inner["permissionDecision"] == decision
        if reason:
            assert inner["permissionDecisionReason"] == reason
        else:
            assert "permissionDecisionReason" not in inner

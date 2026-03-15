"""Tool format detection and output formatting for permission decisions."""

import json
import os

VSCODE_COPILOT = "vscode-copilot"
COPILOT_CLI = "copilot-cli"
CLAUDE_CODE = "claude-code"


def get_tool_format(entry, tool_arg=None):
    """Determine tool format from env var, CLI arg, or entry fields.

    Priority: AGENT_RULES_TOOL env var > tool_arg > auto-detection from entry.

    Raises:
        ValueError: If format cannot be determined
    """
    env_tool = os.environ.get("AGENT_RULES_TOOL")
    if env_tool:
        return env_tool
    if tool_arg:
        return tool_arg
    if "hookEventName" in entry:
        return VSCODE_COPILOT
    if "hook_event_name" in entry:
        return CLAUDE_CODE
    if "toolName" in entry:
        return COPILOT_CLI
    raise ValueError("Cannot detect tool format from input; use --tool or AGENT_RULES_TOOL")


def output_decision(decision, tool_format, reason=None):
    """Output a permission decision with optional reason."""
    if tool_format in (VSCODE_COPILOT, CLAUDE_CODE):
        # Both VSCode Copilot and Claude Code use hookSpecificOutput format
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
            }
        }
        if reason:
            output["hookSpecificOutput"]["permissionDecisionReason"] = reason
    else:  # copilot-cli
        output = {"permissionDecision": decision}
        if reason:
            output["permissionDecisionReason"] = reason
    print(json.dumps(output))

"""Output formatting for permission decisions."""

import json
from .convert import VSCODE_COPILOT, COPILOT_CLI, CLAUDE_CODE


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

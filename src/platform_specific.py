"""Tool format detection and output formatting for permission decisions."""

VSCODE_COPILOT = "vscode-copilot"
COPILOT_CLI = "copilot-cli"
CLAUDE_CODE = "claude-code"


def detect_platform(entry, environment):
    """Auto-detect platform from entry fields and environment variables.

    Considers both the keys in the entry and environment variables to determine
    the platform:
    - VSCode Copilot: hookEventName key + VSCode env vars (VSCODE_PID, VSCODE_CWD, etc.)
    - Claude Code: hook_event_name key + Claude Code env vars (CLAUDE_PROJECT_DIR, etc.)
    - Copilot CLI: toolName + toolArgs keys (no VSCode/Claude Code env vars)

    Args:
        entry: Dictionary with tool-specific fields
        environment: Environment dictionary with variables to check

    Returns:
        Detected platform string

    Raises:
        ValueError: If platform cannot be detected
    """
    has_vscode_key = "hookEventName" in entry
    has_claude_key = "hook_event_name" in entry
    has_gh_cli_keys = "toolName" in entry and "toolArgs" in entry

    vscode_vars = ("VSCODE_PID", "VSCODE_CWD", "VSCODE_IPC_HOOK")
    vscode_env = any(var in environment for var in vscode_vars)

    claude_vars = ("CLAUDE_PROJECT_DIR", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_ENV_FILE")
    claude_env = any(var in environment for var in claude_vars)

    # VSCode Copilot: entry has hookEventName AND VSCode env vars present
    if has_vscode_key and vscode_env:
        return VSCODE_COPILOT

    # Claude Code: entry has hook_event_name AND Claude Code env vars present
    if has_claude_key and claude_env:
        return CLAUDE_CODE

    # Copilot CLI: entry has toolName and toolArgs, no VSCode/Claude Code env vars
    if has_gh_cli_keys and not vscode_env and not claude_env:
        return COPILOT_CLI

    raise ValueError(
        "Cannot detect tool format from input. "
        "Expected: (hookEventName + VSCODE_* env vars) or "
        "(hook_event_name + CLAUDE_* env vars) or "
        "(toolName + toolArgs without VSCode/Claude env vars)"
    )


def format_decision_output(platform, decision, reason=None):
    """Format a permission decision into the appropriate output structure."""
    if platform == CLAUDE_CODE:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "permissionDecision": decision,
            }
        }
        if reason:
            output["hookSpecificOutput"]["permissionDecisionReason"] = reason
        return output
    if platform == VSCODE_COPILOT:
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
    return output

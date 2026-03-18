"""Hook to check tool usage and deny certain operations."""

import re
from pathlib import Path
import yaml

config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

COMMAND_TOOLS = config.get("command_tools", [])
EDITING_TOOLS = config.get("editing_tools", [])


def _resolve_pattern(pattern, cwd):
    """Replace {cwd} in a pattern with the re-escaped CWD value."""
    if cwd and "{cwd}" in pattern:
        return pattern.replace("{cwd}", re.escape(cwd))
    return pattern


def check_command(command, rules, cwd=None):
    """Check command against deny, allow, and confirm lists.

    Args:
        command: The command string to check
        rules: Rules dictionary containing deny_commands, allow_commands, and confirm_commands
        cwd: Current working directory, used to resolve {cwd} in patterns

    Returns:
        Tuple of (decision, reason): decision is 'deny', 'allow', 'ask', or None; reason is str or None
    """
    if not command:
        return None, None

    deny_commands = rules.get("deny_commands", [])
    allow_commands = rules.get("allow_commands", [])
    confirm_commands = rules.get("confirm_commands", [])

    # Check denied commands first (partial match)
    for denied in deny_commands:
        pattern = _resolve_pattern(denied["pattern"], cwd)
        if re.search(pattern, command):
            return "deny", denied.get("reason")

    # Check confirm commands (exact match!)
    for confirm in confirm_commands:
        pattern = _resolve_pattern(confirm["pattern"], cwd)
        if re.fullmatch(pattern, command):
            return "ask", confirm.get("reason")

    # Check allowed commands (exact match!)
    for allowed in allow_commands:
        pattern = _resolve_pattern(allowed["pattern"], cwd)
        if re.fullmatch(pattern, command):
            return "allow", allowed.get("reason")

    return None, None


def check_path(file_path, deny_list, base_dir):
    """Check if file path is forbidden.

    Args:
        file_path: Path to check (absolute or relative)
        deny_list: List of forbidden path entries
        base_dir: Reference directory for resolving relative paths

    Returns:
        Tuple of (decision, reason): decision is 'deny' or None, reason is str or None
    """
    if not file_path:
        return None, None

    # Resolve file path to absolute
    file_path_abs = Path(file_path).resolve()

    for forbidden in deny_list:
        forbidden_path = Path(forbidden["path"])

        # If relative, resolve relative to rules directory
        if not forbidden_path.is_absolute():
            forbidden_path_abs = (base_dir / forbidden_path).resolve()
        else:
            forbidden_path_abs = forbidden_path.resolve()

        reason = forbidden.get("reason")

        # Check if file is within a forbidden directory (or matches exactly)
        try:
            # is_relative_to() is available in Python 3.9+
            if file_path_abs.is_relative_to(forbidden_path_abs):
                return "deny", reason
        except AttributeError:
            # Fallback for Python < 3.9
            try:
                file_path_abs.relative_to(forbidden_path_abs)
                return "deny", reason
            except ValueError:
                pass

    return None, None


def check_paths(paths, rules, base_dir):
    """Check a list of paths against deny_edits rules.

    Returns:
        Tuple of (decision, reason): decision is 'deny' or None
    """
    deny_list = rules.get("deny_edits", [])
    for path in paths:
        decision, reason = check_path(path, deny_list, base_dir)
        if decision == "deny":
            return decision, reason
    return None, None


def process_tool_call(tool_input, rules, base_dir):
    """Check a tool call against command and path rules.

    Returns:
        Tuple of (decision, reason): decision is 'deny', 'allow', 'ask', or None
    """
    tool_name = tool_input.get("tool")
    if tool_name in COMMAND_TOOLS:
        return check_command(
            tool_input.get("command") or "", rules, cwd=tool_input.get("cwd")
        )
    if tool_name in EDITING_TOOLS:
        return check_paths(tool_input.get("paths", []), rules, base_dir)
    return None, None

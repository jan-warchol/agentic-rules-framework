"""Hook to check tool usage and deny certain operations."""

import re
import shlex
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


def _join_reasons(reasons):
    """Join a list of reason strings into a single string, filtering out None values."""
    provided = [r for r in reasons if r is not None]
    return "\n\n".join(provided) if provided else None


def check_command(command, rules, cwd=None):
    """Check command against deny, allow, and confirm lists.

    All matching rules within the winning decision category are collected and
    their reasons are combined. Priority order: deny > confirm > allow.

    Args:
        command: The command string to check
        rules: Rules dictionary containing deny_commands, allow_commands, and confirm_commands
        cwd: Current working directory, used to resolve {cwd} in patterns

    Returns:
        Tuple of (decision, reason, matched_patterns): decision is 'deny', 'allow', 'ask', or None;
        reason combines all matching rules' reasons; matched_patterns lists the rule patterns that fired
    """
    if not command:
        return None, None, []

    deny_commands = rules.get("deny_commands", [])
    allow_commands = rules.get("allow_commands", [])
    confirm_commands = rules.get("confirm_commands", [])

    # Check denied commands (partial match) — collect all matches
    deny_matches = [r for r in deny_commands if re.search(_resolve_pattern(r["pattern"], cwd), command)]
    if deny_matches:
        return "deny", _join_reasons([r.get("reason") for r in deny_matches]), [r["pattern"] for r in deny_matches]

    # Check confirm commands (exact match) — collect all matches
    confirm_matches = [r for r in confirm_commands if re.fullmatch(_resolve_pattern(r["pattern"], cwd), command)]
    if confirm_matches:
        return "ask", _join_reasons([r.get("reason") for r in confirm_matches]), [r["pattern"] for r in confirm_matches]

    # Check allowed commands (exact match) — collect all matches
    allow_matches = [r for r in allow_commands if re.fullmatch(_resolve_pattern(r["pattern"], cwd), command)]
    if allow_matches:
        return "allow", _join_reasons([r.get("reason") for r in allow_matches]), [r["pattern"] for r in allow_matches]

    return None, None, []


def check_path(file_path, deny_list, base_dir):
    """Check if file path is forbidden.

    All matching deny rules are collected and their reasons combined.

    Args:
        file_path: Path to check (absolute or relative)
        deny_list: List of forbidden path entries
        base_dir: Reference directory for resolving relative paths

    Returns:
        Tuple of (decision, reason, matched_patterns): decision is 'deny' or None;
        reason combines all matching rules' reasons; matched_patterns lists the matched path strings
    """
    if not file_path:
        return None, None, []

    file_path_abs = Path(file_path).resolve()
    matches = []
    for forbidden in deny_list:
        forbidden_path = Path(forbidden["path"])

        # If relative, resolve relative to rules directory
        if not forbidden_path.is_absolute():
            forbidden_path_abs = (base_dir / forbidden_path).resolve()
        else:
            forbidden_path_abs = forbidden_path.resolve()

        # Check if file is within a forbidden directory (or matches exactly)
        try:
            # is_relative_to() is available in Python 3.9+
            matched = file_path_abs.is_relative_to(forbidden_path_abs)
        except AttributeError:
            # Fallback for Python < 3.9
            try:
                file_path_abs.relative_to(forbidden_path_abs)
                matched = True
            except ValueError:
                matched = False

        if matched:
            matches.append(forbidden)

    if matches:
        return "deny", _join_reasons([m.get("reason") for m in matches]), [m["path"] for m in matches]
    return None, None, []


def check_paths(paths, rules, base_dir):
    """Check a list of paths against deny_edits rules.

    All denied paths are checked and their reasons combined.

    Returns:
        Tuple of (decision, reason, matched_patterns): decision is 'deny' or None;
        reason combines all matching rules' reasons across all paths; matched_patterns lists matched path strings
    """
    deny_list = rules.get("deny_edits", [])
    all_reasons = []
    all_patterns = []
    has_deny = False
    for path in paths:
        decision, reason, patterns = check_path(path, deny_list, base_dir)
        if decision == "deny":
            has_deny = True
            if reason is not None:
                all_reasons.append(reason)
            all_patterns.extend(patterns)
    if has_deny:
        return "deny", "\n\n".join(all_reasons) if all_reasons else None, all_patterns
    return None, None, []


def extract_paths_from_command(command: str) -> list:
    """Return tokens from command that correspond to existing filesystem paths."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    def _exists(t):
        try:
            return Path(t).exists()
        except OSError:
            return False
    return [t for t in tokens if _exists(t)]


def process_tool_call(tool_input, rules, base_dir):
    """Check a tool call against command and path rules.

    For command tools, also extracts any existing filesystem paths from the
    command tokens and checks them against deny_edits rules.

    Returns:
        Tuple of (decision, reason, matched_patterns): decision is 'deny', 'allow', 'ask', or None;
        matched_patterns is a list of rule pattern strings that triggered the decision
    """
    tool_name = tool_input.get("tool")
    if tool_name in COMMAND_TOOLS:
        command = tool_input.get("command") or ""
        cmd_decision, cmd_reason, cmd_patterns = check_command(
            command, rules, cwd=tool_input.get("cwd")
        )

        paths_in_command = extract_paths_from_command(command)
        path_decision, path_reason, path_patterns = check_paths(
            paths_in_command, rules, base_dir
        )

        if cmd_decision == "deny" or path_decision == "deny":
            all_reasons = []
            all_patterns = []
            if cmd_decision == "deny":
                if cmd_reason:
                    all_reasons.append(cmd_reason)
                all_patterns.extend(cmd_patterns)
            if path_decision == "deny":
                if path_reason:
                    all_reasons.append(path_reason)
                all_patterns.extend(path_patterns)
            combined_reason = "\n\n".join(all_reasons) if all_reasons else None
            return "deny", combined_reason, all_patterns

        return cmd_decision, cmd_reason, cmd_patterns

    if tool_name in EDITING_TOOLS:
        return check_paths(tool_input.get("paths", []), rules, base_dir)
    return None, None, []

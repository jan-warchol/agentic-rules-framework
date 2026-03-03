#!/usr/bin/env python3
"""Hook to check tool usage and deny certain operations."""

import os
from pathlib import Path
import yaml
from .convert import convert_tool_entry, detect_tool_format, VSCODE_COPILOT, COPILOT_CLI, CLAUDE_CODE
from .rules import load_rules, check_command, check_path
from .output import output_decision

# Load config (tools lists)
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

COMMAND_TOOLS = config.get("command_tools", [])
EDITING_TOOLS = config.get("editing_tools", [])


def get_tool_format(input_data, tool_arg=None):
    """Determine which tool format to use.

    Priority order:
      1. AGENT_RULES_TOOL environment variable
      2. --tool CLI argument
      3. Auto-detection from input data fields

    Args:
        input_data: Raw input JSON data
        tool_arg: Value of the --tool CLI argument (or None)

    Returns:
        Tool format string: 'claude-code', 'vscode-copilot' or 'copilot-cli'

    Raises:
        ValueError: If format cannot be determined
    """
    env_tool = os.environ.get("AGENT_RULES_TOOL")
    if env_tool:
        return env_tool
    if tool_arg:
        return tool_arg
    detected = detect_tool_format(input_data)
    if detected is None:
        raise ValueError("Cannot detect tool format from input; use --tool or AGENT_RULES_TOOL")
    return detected


def process_command_tool(args, rules, tool_format):
    """Process command tools - check command restrictions."""
    command = args.get("command", "")
    status, details = check_command(command, rules)
    if status is not None:
        output_decision(status, tool_format, reason=details.get("reason"))
        return True
    return False


def process_editing_tool(args, rules, rules_path, tool_format):
    """Process editing tools - check forbidden edits.

    Args:
        args: Tool arguments containing path or paths
        rules: Rules dictionary containing deny_edits
        rules_path: Path to the rules file
        tool_format: Tool format string for output

    Returns:
        True if editing is forbidden, False otherwise
    """
    deny_list = rules.get("deny_edits", [])
    rules_dir = rules_path.parent

    # Normalize to list of paths
    paths_to_check = []
    if args.get("path"):
        paths_to_check.append(args["path"])
    if "paths" in args:
        paths_to_check.extend(args["paths"])

    # Check all paths
    for path in paths_to_check:
        is_denied, details = check_path(path, deny_list, rules_dir)
        if is_denied:
            output_decision("deny", tool_format, reason=details.get("reason"))
            return True

    return False

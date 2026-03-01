#!/usr/bin/env python3
"""Hook to check tool usage and deny certain operations."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
import yaml
from convert import convert_tool_entry, detect_tool_format, VSCODE_COPILOT, COPILOT_CLI

# Load config (tools lists)
config_path = Path(__file__).parent / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

COMMAND_TOOLS = config.get("command_tools", [])
EDITING_TOOLS = config.get("editing_tools", [])


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Hook to check tool usage and deny certain operations.")
    parser.add_argument("rules_path", nargs="?", help="Path to agent-rules.yaml (default: auto-detect from cwd)")
    parser.add_argument("--tool", help="Tool format to use: 'vscode-copilot' or 'copilot-cli' (default: auto-detect)")
    return parser.parse_args()


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
        Tool format string: 'vscode-copilot' or 'copilot-cli'

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


def load_rules(input_data, rules_path_arg=None):
    """Load rules from CLI argument or cwd directory.

    Args:
        input_data: The tool input JSON data
        rules_path_arg: Optional path from --rules CLI argument

    Returns:
        dict: Loaded rules configuration

    Raises:
        FileNotFoundError: If no rules file is found
    """
    rules_path = None

    # Check for CLI argument
    if rules_path_arg:
        rules_path = Path(rules_path_arg)
        if not rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
    else:
        # Get cwd from input data
        converted = convert_tool_entry(input_data)
        cwd = converted.get("cwd", "")
        if not cwd:
            raise ValueError("No cwd found in input data and no rules path provided")

        cwd_path = Path(cwd)

        # Try agent-rules.yaml first, then agent-rules.yml
        for filename in ["agent-rules.yaml", "agent-rules.yml"]:
            potential_path = cwd_path / filename
            if potential_path.exists():
                rules_path = potential_path
                break

        if not rules_path:
            raise FileNotFoundError(f"No agent-rules.yaml or agent-rules.yml found in {cwd_path}")

    # Load and return rules
    with open(rules_path) as f:
        return yaml.safe_load(f), rules_path


def check_path(file_path, deny_list, base_dir):
    """Check if file path is forbidden. Returns (is_denied, details).
    
    Args:
        file_path: Path to check (absolute or relative)
        deny_list: List of forbidden path entries
        base_dir: Reference directory for resolving relative paths
    
    Returns:
        Tuple of (is_denied: bool, details: dict)
    """
    if not file_path:
        return False, {}

    # Resolve file path to absolute
    file_path_abs = Path(file_path).resolve()
    
    for forbidden in deny_list:
        forbidden_path = Path(forbidden["path"])
        
        # If relative, resolve relative to rules directory
        if not forbidden_path.is_absolute():
            forbidden_path_abs = (base_dir / forbidden_path).resolve()
        else:
            forbidden_path_abs = forbidden_path.resolve()
        
        # Check if absolute paths match exactly
        if file_path_abs == forbidden_path_abs:
            details = {}
            if "reason" in forbidden:
                details["reason"] = forbidden["reason"]
            if "context" in forbidden:
                details["context"] = forbidden["context"]
            return True, details
        
        # Check if file is within a forbidden directory
        try:
            # is_relative_to() is available in Python 3.9+
            if file_path_abs.is_relative_to(forbidden_path_abs):
                details = {}
                if "reason" in forbidden:
                    details["reason"] = forbidden["reason"]
                if "context" in forbidden:
                    details["context"] = forbidden["context"]
                return True, details
        except AttributeError:
            # Fallback for Python < 3.9
            try:
                file_path_abs.relative_to(forbidden_path_abs)
                details = {}
                if "reason" in forbidden:
                    details["reason"] = forbidden["reason"]
                if "context" in forbidden:
                    details["context"] = forbidden["context"]
                return True, details
            except ValueError:
                # Not relative, continue checking
                pass

    return False, {}


def check_command(command, rules):
    """Check command against deny, allow, and confirm lists. Returns (status, details).

    Args:
        command: The command string to check
        rules: Rules dictionary containing deny_commands, allow_commands, and confirm_commands

    Returns:
        status: 'deny', 'allow', 'ask', or None
        details: dict with optional 'reason' and 'context' keys
    """
    if not command:
        return None, {}

    deny_commands = rules.get("deny_commands", [])
    allow_commands = rules.get("allow_commands", [])
    confirm_commands = rules.get("confirm_commands", [])

    # Check denied commands first (partial match)
    if deny_commands:
        for denied in deny_commands:
            if re.search(denied["pattern"], command):
                details = {}
                if "reason" in denied:
                    details["reason"] = denied["reason"]
                if "context" in denied:
                    details["context"] = denied["context"]
                return "deny", details

    # Check confirm commands (exact match!)
    if confirm_commands:
        for confirm in confirm_commands:
            if re.fullmatch(confirm["pattern"], command):
                details = {}
                if "reason" in confirm:
                    details["reason"] = confirm["reason"]
                if "context" in confirm:
                    details["context"] = confirm["context"]
                return "ask", details

    # Check allowed commands (exact match!)
    if allow_commands:
        for allowed in allow_commands:
            if re.fullmatch(allowed["pattern"], command):
                details = {}
                if "reason" in allowed:
                    details["reason"] = allowed["reason"]
                if "context" in allowed:
                    details["context"] = allowed["context"]
                return "allow", details

    return None, {}


def output_decision(decision, tool_format, reason=None, context=None):
    """Output a permission decision with optional reason and context."""
    if tool_format == VSCODE_COPILOT:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
            }
        }
        if reason:
            output["hookSpecificOutput"]["permissionDecisionReason"] = reason
        if context:
            output["hookSpecificOutput"]["additionalContext"] = context
    else:  # copilot-cli
        output = {"permissionDecision": decision}
        if reason:
            output["permissionDecisionReason"] = reason
    print(json.dumps(output))


def process_command_tool(args, rules, tool_format=VSCODE_COPILOT):
    """Process command tools - check command restrictions."""
    command = args.get("command", "")
    status, details = check_command(command, rules)
    if status is not None:
        output_decision(
            status,
            tool_format,
            reason=details.get("reason"),
            context=details.get("context")
        )
        return True
    return False


def process_editing_tool(args, rules, rules_path, tool_format=VSCODE_COPILOT):
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
            output_decision(
                "deny",
                tool_format,
                reason=details.get("reason"),
                context=details.get("context")
            )
            return True

    return False


def main():
    args = parse_args()

    # Read the tool input JSON from stdin
    input_data = json.load(sys.stdin)

    # Determine tool format (env var > --tool arg > auto-detect)
    tool_format = get_tool_format(input_data, args.tool)

    # Load rules
    rules, rules_path = load_rules(input_data, args.rules_path)

    # Convert to known format
    converted = convert_tool_entry(input_data, tool_format)

    # Extract tool name and args
    tool_name = converted.get("tool", "")
    tool_args = converted.get("args", {})

    # Process based on tool type
    if tool_name in COMMAND_TOOLS:
        process_command_tool(tool_args, rules, tool_format)
    elif tool_name in EDITING_TOOLS:
        process_editing_tool(tool_args, rules, rules_path, tool_format)


if __name__ == "__main__":
    main()

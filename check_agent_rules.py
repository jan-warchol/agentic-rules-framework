#!/usr/bin/env python3
"""Hook to check tool usage and deny certain operations."""

import json
import re
import sys
from pathlib import Path
import yaml
from convert import convert_tool_entry

# Load config (tools lists)
config_path = Path(__file__).parent / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

COMMAND_TOOLS = config.get("command_tools", [])
EDITING_TOOLS = config.get("editing_tools", [])


def load_rules(input_data):
    """Load rules from CLI argument or cwd directory.

    Args:
        input_data: The tool input JSON data

    Returns:
        dict: Loaded rules configuration

    Raises:
        FileNotFoundError: If no rules file is found
    """
    rules_path = None

    # Check for CLI argument
    if len(sys.argv) > 1:
        rules_path = Path(sys.argv[1])
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


def output_decision(decision, reason=None, context=None):
    """Output a permission decision with optional reason and context."""
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
    print(json.dumps(output))


def process_command_tool(args, rules):
    """Process command tools - check command restrictions."""
    command = args.get("command", "")
    status, details = check_command(command, rules)
    if status is not None:
        output_decision(
            status,
            reason=details.get("reason"),
            context=details.get("context")
        )
        return True
    return False


def process_editing_tool(args, rules, rules_path):
    """Process editing tools - check forbidden edits.
    
    Args:
        args: Tool arguments containing path or paths
        rules: Rules dictionary containing deny_edits
        rules_path: Path to the rules file
    
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
                reason=details.get("reason"),
                context=details.get("context")
            )
            return True

    return False


def main():
    # Read the tool input JSON from stdin
    input_data = json.load(sys.stdin)

    # Load rules
    rules, rules_path = load_rules(input_data)

    # Convert to known format
    converted = convert_tool_entry(input_data)

    # Extract tool name and args
    tool_name = converted.get("tool", "")
    args = converted.get("args", {})

    # Process based on tool type
    if tool_name in COMMAND_TOOLS:
        process_command_tool(args, rules)
    elif tool_name in EDITING_TOOLS:
        process_editing_tool(args, rules, rules_path)


if __name__ == "__main__":
    main()

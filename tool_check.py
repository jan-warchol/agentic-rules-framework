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

        # Try AGENT_RULES.yaml first, then AGENT_RULES.yml
        for filename in ["AGENT_RULES.yaml", "AGENT_RULES.yml"]:
            potential_path = cwd_path / filename
            if potential_path.exists():
                rules_path = potential_path
                break

        if not rules_path:
            raise FileNotFoundError(f"No AGENT_RULES.yaml or AGENT_RULES.yml found in {cwd_path}")

    # Load and return rules
    with open(rules_path) as f:
        return yaml.safe_load(f)


def check_forbidden_path(file_path, forbidden_list):
    """Check if file path is forbidden. Returns (is_forbidden, details)."""
    if not file_path:
        return False, {}

    path = Path(file_path)
    for forbidden in forbidden_list:
        forbidden_path = Path(forbidden["path"])
        # Match if the file path ends with the forbidden path
        if path.name == forbidden_path.name and (
            len(forbidden_path.parts) == 1 or str(path).endswith(str(forbidden_path))
        ):
            details = {}
            if "reason" in forbidden:
                details["reason"] = forbidden["reason"]
            if "context" in forbidden:
                details["context"] = forbidden["context"]
            return True, details

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


def main():
    # Read the tool input JSON from stdin
    input_data = json.load(sys.stdin)

    # Load rules
    rules = load_rules(input_data)

    # Convert to known format
    converted = convert_tool_entry(input_data)

    # Extract tool name and args
    args = converted.get("args", {})

    process_command_tool(args, rules)


if __name__ == "__main__":
    main()

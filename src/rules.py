"""Rules loading and evaluation."""

import re
from pathlib import Path
import yaml
from .convert import convert_tool_entry


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
            return True, details

        # Check if file is within a forbidden directory
        try:
            # is_relative_to() is available in Python 3.9+
            if file_path_abs.is_relative_to(forbidden_path_abs):
                details = {}
                if "reason" in forbidden:
                    details["reason"] = forbidden["reason"]
                return True, details
        except AttributeError:
            # Fallback for Python < 3.9
            try:
                file_path_abs.relative_to(forbidden_path_abs)
                details = {}
                if "reason" in forbidden:
                    details["reason"] = forbidden["reason"]
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
                return "deny", details

    # Check confirm commands (exact match!)
    if confirm_commands:
        for confirm in confirm_commands:
            if re.fullmatch(confirm["pattern"], command):
                details = {}
                if "reason" in confirm:
                    details["reason"] = confirm["reason"]
                return "ask", details

    # Check allowed commands (exact match!)
    if allow_commands:
        for allowed in allow_commands:
            if re.fullmatch(allowed["pattern"], command):
                details = {}
                if "reason" in allowed:
                    details["reason"] = allowed["reason"]
                return "allow", details

    return None, {}

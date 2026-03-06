"""Rules loading and evaluation."""

from pathlib import Path
import yaml


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
        cwd = input_data.get("cwd", "")
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
        return yaml.safe_load(f), rules_path.parent

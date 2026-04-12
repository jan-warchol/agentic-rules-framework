"""Rules loading and evaluation."""

from pathlib import Path
import platformdirs
import yaml


RULES_FILENAMES = ["agent-rules.yaml", "agent-rules.yml"]
APP_NAME = "agentic-rules-framework"


def _find_rules_file(directory):
    """Return path to first rules file found in directory, or None."""
    for filename in RULES_FILENAMES:
        path = directory / filename
        if path.exists():
            return path
    return None


def _load_yaml_file(path):
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _merge_rules(global_rules, project_rules):
    """Merge global and project rules by concatenating each list section.

    Global rules are prepended so they are evaluated first.
    """
    if global_rules is None:
        return project_rules
    if project_rules is None:
        return global_rules

    merged = {}
    all_keys = set(global_rules) | set(project_rules)
    for key in all_keys:
        g = global_rules.get(key, []) or []
        p = project_rules.get(key, []) or []
        merged[key] = g + p
    return merged


def global_rules_path():
    """Return the path to the global rules file (may not exist)."""
    config_dir = Path(platformdirs.user_config_dir(APP_NAME))
    return config_dir / RULES_FILENAMES[0]


def load_rules(input_data, rules_path_arg=None):
    """Load and merge global and project-level rules.

    Global rules are loaded from the user config directory
    (e.g. ~/.config/agentic-rules-framework/agent-rules.yaml).
    Project rules are loaded from the cwd or from rules_path_arg.

    Either file may be absent; at least one must exist.

    Args:
        input_data: The tool input JSON data
        rules_path_arg: Optional explicit path from --rules CLI argument

    Returns:
        Tuple of (merged_rules dict, base_dir Path)

    Raises:
        FileNotFoundError: If no rules file is found anywhere
    """
    # --- Global rules ---
    global_config_dir = Path(platformdirs.user_config_dir(APP_NAME))
    global_path = _find_rules_file(global_config_dir)
    global_rules = _load_yaml_file(global_path) if global_path else None

    # --- Project rules ---
    project_rules = None
    project_path = None
    base_dir = None

    if rules_path_arg:
        rules_path = Path(rules_path_arg)
        if not rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        project_rules = _load_yaml_file(rules_path)
        base_dir = rules_path.parent
    else:
        cwd = input_data.get("cwd", "")
        if cwd:
            cwd_path = Path(cwd)
            base_dir = cwd_path
            project_path = _find_rules_file(cwd_path)
            if project_path:
                project_rules = _load_yaml_file(project_path)

    if global_rules is None and project_rules is None:
        raise FileNotFoundError(
            f"No agent-rules.yaml found in {base_dir or '(no cwd)'} or {global_config_dir}"
        )

    merged = _merge_rules(global_rules, project_rules)
    # base_dir is used for resolving relative paths in deny_edits;
    # all relative paths (from both global and project rules) are resolved
    # against the project CWD, so global rules like deny_edits: [agent-rules.yaml]
    # apply to the current project.
    if base_dir is None:
        base_dir = global_config_dir

    # Determine the effective rules path for logging (project takes precedence)
    if rules_path_arg:
        effective_rules_path = Path(rules_path_arg)
    elif project_path:
        effective_rules_path = project_path
    else:
        effective_rules_path = global_path

    return merged, base_dir, effective_rules_path

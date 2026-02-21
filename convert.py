#!/usr/bin/env python3
"""Convert prompt-history.jsonl and tool-inputs/results.jsonl to simplified format."""

import json
import sys
from pathlib import Path
import yaml
from conversion_utils import parse_timestamp, run_converter

# Load configuration
config_path = Path(__file__).parent / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

FIELDS = config["fields"]
TOOL_ARG_FIELDS = set(config["tool_arg_fields"])


def filter_args(args):
    """Filter args to only include specified fields, renaming filePath to path."""
    if not isinstance(args, dict):
        return {}
    filtered = {k: v for k, v in args.items() if k in TOOL_ARG_FIELDS}
    # Rename filePath to path
    if "filePath" in filtered:
        filtered["path"] = filtered.pop("filePath")

    # Special handling for replacements (multi_replace_string_in_file)
    if "replacements" in args and isinstance(args["replacements"], list):
        paths = [
            r.get("filePath") or r.get("path")
            for r in args["replacements"]
            if isinstance(r, dict)
        ]
        paths = [p for p in paths if p]  # Filter out None values
        if paths:
            filtered["paths"] = paths

    return filtered


def convert_tool_entry(entry):
    """Convert a single tool entry to simplified format."""
    # Extract tool name
    tool_name = entry.get("tool_name")

    # Extract tool arguments (Format 1)
    args = entry.get("tool_input", {})

    # Build result from configured fields
    result = {}
    for field in FIELDS:
        if field == "timestamp":
            result[field] = parse_timestamp(entry["timestamp"])
        elif field == "tool":
            result[field] = tool_name
        elif field == "args":
            result[field] = filter_args(args)
        elif field in entry:
            result[field] = entry[field]

    return result


def convert_prompt_entry(entry):
    """Convert a single prompt history entry to simplified format."""
    result = {}
    for field in FIELDS:
        if field == "timestamp":
            result[field] = parse_timestamp(entry["timestamp"])
        elif field in entry:
            result[field] = entry[field]
    return result


def convert_entry(entry):
    """Convert a single entry (auto-detect type: prompt or tool)."""
    # Detect entry type
    if "tool_name" in entry:
        return convert_tool_entry(entry)
    else:
        # Assume it's a prompt entry
        return convert_prompt_entry(entry)


def main():
    run_converter(convert_entry, sys.argv[0])


if __name__ == "__main__":
    main()

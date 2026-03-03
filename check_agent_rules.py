#!/usr/bin/env python3
import argparse
import json
import sys

from src.check_rules import (
    get_tool_format,
    load_rules,
    convert_tool_entry,
    process_command_tool,
    process_editing_tool,
    COMMAND_TOOLS,
    EDITING_TOOLS,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Hook to check tool usage and deny certain operations."
    )
    parser.add_argument(
        "rules_path",
        nargs="?",
        help="Path to agent-rules.yaml (default: auto-detect from cwd)",
    )
    parser.add_argument(
        "--tool",
        help="Tool format to use: 'claude-code', 'vscode-copilot' or 'copilot-cli' (default: auto-detect)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    input_data = json.load(sys.stdin)
    tool_format = get_tool_format(input_data, args.tool)
    rules, rules_path = load_rules(input_data, args.rules_path)
    converted = convert_tool_entry(input_data, tool_format)
    tool_name = converted.get("tool", "")
    tool_args = converted.get("args", {})
    if tool_name in COMMAND_TOOLS:
        process_command_tool(tool_args, rules, tool_format)
    elif tool_name in EDITING_TOOLS:
        process_editing_tool(tool_args, rules, rules_path, tool_format)

#!/usr/bin/env python3
import argparse
import json
import sys

from src.normalize import normalize_input, simplify_tool_call
from src.rules import load_rules
from src.check_rules import process_tool_call
from src.io_format import get_tool_format, output_decision


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
    rules, base_dir = load_rules(input_data, args.rules_path)
    simplified = simplify_tool_call(normalize_input(input_data, tool_format))
    status, reason = process_tool_call(simplified, rules, base_dir)
    if status is not None:
        output_decision(status, tool_format, reason=reason)

#!/usr/bin/env python3
import argparse
import json
import os
import sys

from src.normalization import simplify_tool_input
from src.rules import load_rules
from src.check_rules import process_tool_call
from src.platform_specific import detect_platform, format_decision_output
from src.logging import write_log


def parse_args():
    parser = argparse.ArgumentParser(
        description="Hook to check tool usage and deny certain operations."
    )
    parser.add_argument(
        "rules_path",
        nargs="?",
        help="Path to agent-rules.yaml (default: auto-detect from cwd)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    input_data = json.load(sys.stdin)
    platform = detect_platform(input_data, os.environ)
    try:
        rules, base_dir, rules_path = load_rules(input_data, args.rules_path)
    except FileNotFoundError:
        sys.exit(0)
    simplified = simplify_tool_input(input_data)
    status, reason = process_tool_call(simplified, rules, base_dir)
    write_log(simplified, status, reason, rules_path)
    if status is not None:
        output = format_decision_output(platform, status, reason=reason)
        print(json.dumps(output))

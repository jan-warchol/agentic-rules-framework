#!/usr/bin/env python3
import json
import os
import sys

from src.normalization import simplify_tool_input
from src.rules import load_rules
from src.check_rules import process_tool_call
from src.platform_specific import detect_platform, format_decision_output
from src.logging import write_log


if __name__ == "__main__":
    input_data = json.load(sys.stdin)
    platform = detect_platform(input_data, os.environ)
    try:
        rules, base_dir, rules_path = load_rules(input_data)
    except FileNotFoundError:
        sys.exit(0)
    simplified = simplify_tool_input(input_data)
    decision, reason, matched_patterns = process_tool_call(simplified, rules, base_dir)
    write_log(simplified, decision, reason, matched_patterns, rules_path)
    if decision is not None:
        output = format_decision_output(platform, decision, reason=reason)
        print(json.dumps(output))

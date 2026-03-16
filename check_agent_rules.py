#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from pathlib import Path

from src.normalization import simplify_tool_input
from src.rules import load_rules
from src.check_rules import process_tool_call, config_path
from src.platform_specific import detect_platform, format_decision_output

LOG_FILENAME = ".agent-rules-log.jsonl"


def write_log(simplified_input, status, reason, rules_path):
    cwd = os.getcwd()
    log_entry = {
        "timestamp": int(time.time()),
        "script_path": str(Path(__file__).resolve()),
        "config_path": str(config_path.resolve()),
        "rules_path": str(rules_path.resolve()) if rules_path else None,
        "session": simplified_input.get("session"),
        "cwd": cwd,
        "input": {"tool": simplified_input.get("tool")},
        "output": {},
    }
    if "paths" in simplified_input:
        log_entry["input"]["paths"] = simplified_input["paths"]
    if "command" in simplified_input:
        log_entry["input"]["command"] = simplified_input["command"]
    if status:
        log_entry["output"]["decision"] = status
        log_entry["output"]["reason"] = reason

    log_path = Path(cwd) / LOG_FILENAME
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


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

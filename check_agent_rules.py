#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from pathlib import Path

from src.normalize import normalize_input, simplify_tool_call
from src.rules import load_rules
from src.check_rules import process_tool_call
from src.io_format import get_tool_format, output_decision

LOG_FILENAME = ".agent-rules-log.jsonl"


def write_log(simplified_input, status, reason, rules_path):
    cwd = os.getcwd()
    log_entry = {
        "timestamp": int(time.time()),
        "session_id": simplified_input.get("session_id"),
        "cwd": cwd,
        "rules_path": str(rules_path.resolve()) if rules_path else None,
        "input": {"tool": simplified_input.get("tool")},
        "output": {},
    }
    if simplified_input.get("paths"):
        log_entry["input"]["paths"] = simplified_input["paths"]
    if simplified_input.get("command"):
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
    parser.add_argument(
        "--tool",
        help="Tool format to use: 'claude-code', 'vscode-copilot' or 'copilot-cli' (default: auto-detect)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    input_data = json.load(sys.stdin)
    tool_format = get_tool_format(input_data, args.tool)
    try:
        rules, base_dir, rules_path = load_rules(input_data, args.rules_path)
    except FileNotFoundError:
        sys.exit(0)
    simplified = simplify_tool_call(normalize_input(input_data, tool_format))
    status, reason = process_tool_call(simplified, rules, base_dir)
    write_log(simplified, status, reason, rules_path)
    if status is not None:
        output_decision(status, tool_format, reason=reason)

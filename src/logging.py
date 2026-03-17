import json
import os
import time
from pathlib import Path

LOG_FILENAME = ".agent-rules-log.jsonl"


def write_log(simplified_input, status, reason, rules_path):
    cwd = simplified_input["cwd"] if "cwd" in simplified_input else os.getcwd()
    log_entry = {
        "timestamp": int(time.time()),
        "session": simplified_input.get("session"),
        "cwd": cwd,
        "rules_path": str(rules_path.resolve()) if rules_path else None,
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

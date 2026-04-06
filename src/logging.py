import json
import os
import time
from pathlib import Path

import platformdirs

APP_NAME = "agentic-rules-framework"
LOG_SUBDIR = ".claude-sessions"
LOG_FILENAME = "permission-logs.jsonl"


def _load_config() -> dict:
    config_dir = Path(platformdirs.user_config_dir(APP_NAME))
    try:
        with open(config_dir / "config.json") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_log_dir(cwd: str) -> Path:
    """Return directory where log files should be written.

    Defaults to .claude-sessions/ in cwd; overridden by logs_base_dir in
    ~/.config/agentic-rules-framework/config.json.
    """
    config = _load_config()
    base = config.get("logs_base_dir")
    if not base:
        log_dir = Path(cwd) / LOG_SUBDIR
        log_dir.mkdir(exist_ok=True)
        return log_dir

    base_dir = Path(base).expanduser()
    if not base_dir.is_absolute():
        raise ValueError(f"logs_base_dir must be an absolute path, got: {base!r}")
    cwd_path = Path(cwd)
    try:
        subdir = ".".join(cwd_path.relative_to(Path.home()).parts)
    except ValueError:
        subdir = ".".join(cwd_path.parts[1:])

    log_dir = base_dir / subdir
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def write_entry(path: Path, entry: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")


def write_log(simplified_input, decision, reason, matched_patterns, rules_path):
    cwd = simplified_input.get("cwd") or os.getcwd()
    log_entry = {
        "timestamp": int(time.time()),
        "session": simplified_input.get("session"),
        "cwd": cwd,
        "event": "AgenticRulesDecision",
        "rules_path": str(rules_path.resolve()) if rules_path else None,
        "input": {"tool": simplified_input.get("tool")},
        "output": {},
    }
    if "paths" in simplified_input:
        log_entry["input"]["paths"] = simplified_input["paths"]
    if "command" in simplified_input:
        log_entry["input"]["command"] = simplified_input["command"]
    if decision:
        log_entry["output"]["decision"] = decision
        log_entry["output"]["reason"] = reason
        log_entry["output"]["rules_matched"] = matched_patterns

    log_dir = get_log_dir(cwd)
    write_entry(log_dir / LOG_FILENAME, log_entry)

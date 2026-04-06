#!/usr/bin/env python3
"""Log events related to permission debugging to the configured location."""

import json
import os
import sys

from src.logging import LOG_FILENAME, get_log_dir, write_entry
from src.normalization import normalize_input


DROP_KEYS = {"transcript_path", "tool_use_id", "agent_id", "agent_type"}


def is_plan_mode_permission(event):
    """True for PermissionRequest events triggered solely by default mode needing acceptEdits."""
    if event.get("permission_mode") != "default":
        return False
    suggestions = event.get("permission_suggestions", [])
    return any(
        s.get("type") == "setMode" and s.get("mode") == "acceptEdits"
        for s in suggestions
    )


def process_event(event: dict) -> dict | None:
    if is_plan_mode_permission(event):
        return None

    event = normalize_input(event)

    if "args" in event:
        for key in ("content", "new_string", "old_string"):
            event["args"].pop(key, None)

    entry = {k: v for k, v in event.items() if k not in DROP_KEYS}
    first_keys = ["timestamp", "session", "cwd", "event", "tool", "args"]
    return {k: entry[k] for k in first_keys if k in entry} | {
        k: v for k, v in entry.items() if k not in first_keys
    }


if __name__ == "__main__":
    entry = process_event(json.load(sys.stdin))
    if entry is not None:
        cwd = entry.get("cwd") or os.getcwd()
        write_entry(get_log_dir(cwd) / LOG_FILENAME, entry)

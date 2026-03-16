"""Hook input normalization and simplification."""

import json
from datetime import datetime


def _normalize_field(result, canonical_name, alt_names):
    """Normalize a field to its canonical name, removing alternate forms.

    If canonical name doesn't exist, tries to use the first non-None alternate.
    Removes all alternate forms from the dict.

    Args:
        result: dict being normalized (modified in place)
        canonical_name: the canonical field name (e.g., "path")
        alt_names: list of alternate field names (e.g., ["filePath", "file_path"])
    """
    if canonical_name not in result:
        val = None
        for alt in alt_names:
            val = result.pop(alt, None)
            if val:
                break
        if val:
            result[canonical_name] = val
    else:
        # Remove all alternate names if canonical exists
        for alt in alt_names:
            result.pop(alt, None)


def normalize_input(hook_input):
    """Normalize a raw input entry, passing through all fields unchanged except:

    - toolName/tool_name → tool (raw field dropped)
    - toolArgs/tool_input → args, parsed if JSON string, with field names normalized (raw field dropped)
    - hookEventName/hook_event_name → event (raw field dropped)
    - sessionId/session_id → session (raw field dropped)
    - timestamp: string ISO 8601 → integer Unix timestamp (seconds)
    """
    result = dict(hook_input)

    # Normalize common fields
    _normalize_field(result, "session", ["sessionId", "session_id"])
    _normalize_field(result, "event", ["hookEventName", "hook_event_name"])
    _normalize_field(result, "tool", ["toolName", "tool_name"])
    _normalize_field(result, "args", ["toolArgs", "tool_input"])

    # Convert timestamp from string to integer if needed
    if "timestamp" in result and isinstance(result["timestamp"], str):
        dt = datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
        result["timestamp"] = int(dt.timestamp())

    # Parse JSON string args if needed and normalize field names
    if "args" in result:
        args_raw = result["args"]
        args_full = json.loads(args_raw) if isinstance(args_raw, str) else args_raw

        if isinstance(args_full, dict):
            _normalize_field(args_full, "path", ["filePath", "file_path"])
            _normalize_field(args_full, "paths", ["filePaths", "file_paths"])
            result["args"] = args_full
        else:
            result["args"] = {}

    return result


def simplify_tool_input(tool_input):
    """Simplify a tool call entry by extracting command and paths.

    Normalizes the input first, then:
    - Extracts command from args
    - Extracts paths from args or from replacements
    """
    normalized = normalize_input(tool_input)
    args = normalized["args"]

    paths = args.get("paths", [])
    if path := args.get("path"):
        paths.append(path)
    if "replacements" in args and isinstance(args["replacements"], list):
        for r in args["replacements"]:
            if isinstance(r, dict):
                path = r.get("filePath") or r.get("path")
                if path:
                    paths.append(path)

    result = {
        "cwd": normalized["cwd"],
        "session": normalized.get("session"),
        "tool": normalized["tool"],
    }
    if paths:
        result["paths"] = paths
    if "command" in args:
        result["command"] = args["command"]
    return result

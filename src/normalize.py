"""Hook input normalization and simplification."""

import json


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


def normalize_input(entry):
    """Normalize a raw input entry, passing through all fields unchanged except:

    - toolName/tool_name → tool (raw field dropped)
    - toolArgs/tool_input → args, parsed if JSON string, with field names normalized (raw field dropped)
    - hookEventName/hook_event_name → event (raw field dropped)
    - sessionId/session_id → session (raw field dropped)
    """
    result = dict(entry)

    # Normalize common fields
    _normalize_field(result, "session", ["sessionId", "session_id"])
    _normalize_field(result, "event", ["hookEventName", "hook_event_name"])
    _normalize_field(result, "tool", ["toolName", "tool_name"])
    _normalize_field(result, "args", ["toolArgs", "tool_input"])

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


def simplify_tool_call(normalized):
    """Simplify a normalized tool call by extracting command and path.

    - Extracts command from args
    - Extracts path from args or from replacements
    """
    args = normalized["args"]

    path = args.get("path")

    if not path and "replacements" in args and isinstance(args["replacements"], list):
        for r in args["replacements"]:
            if isinstance(r, dict):
                path = r.get("path") or r.get("filePath")
                if path:
                    break

    return {
        "tool": normalized["tool"],
        "cwd": normalized["cwd"],
        "command": args.get("command"),
        "path": path,
        "session": normalized.get("session"),
    }

"""Tool call normalization and simplification."""

import json

VSCODE_COPILOT = "vscode-copilot"
COPILOT_CLI = "copilot-cli"
CLAUDE_CODE = "claude-code"


def normalize_input(entry, tool_format=None):
    """Normalize a raw input entry, passing through all fields unchanged except:

    - toolName/tool_name → tool (raw field dropped)
    - toolArgs/tool_input → args, parsed if JSON string (raw field dropped)

    Non-tool entries (e.g. prompt history) are returned unchanged.

    tool_format must be determined with get_tool_format() before calling.
    """
    if "toolName" not in entry and "tool_name" not in entry:
        return entry

    if tool_format is None:
        raise ValueError("tool_format is required; use get_tool_format() to determine it")

    if tool_format == COPILOT_CLI:
        tool_name = entry.get("toolName")
        args_raw = entry.get("toolArgs") or "{}"
        args_full = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        raw_keys = ("toolName", "toolArgs")
    else:  # vscode-copilot and claude-code
        tool_name = entry.get("tool_name")
        args_full = entry.get("tool_input", {})
        raw_keys = ("tool_name", "tool_input")

    if not isinstance(args_full, dict):
        args_full = {}

    result = {k: v for k, v in entry.items() if k not in raw_keys}
    result["tool"] = tool_name
    result["args"] = args_full
    return result


def simplify_tool_call(normalized):
    """Simplify a normalized tool call by extracting command and paths.

    - Extracts command from args
    - Consolidates all path representations (path/filePath/file_path/paths/replacements)
      into a single list

    Args:
        normalized: Output of normalize_input

    Returns:
        dict with keys: tool, cwd, command, paths
    """
    args = normalized["args"]

    paths = []
    path = args.get("path") or args.get("filePath") or args.get("file_path")
    if path:
        paths.append(path)
    paths.extend(args.get("paths", []))
    if "replacements" in args and isinstance(args["replacements"], list):
        for r in args["replacements"]:
            if isinstance(r, dict):
                p = r.get("filePath") or r.get("path")
                if p:
                    paths.append(p)

    return {
        "tool": normalized["tool"],
        "cwd": normalized["cwd"],
        "command": args.get("command"),
        "paths": paths,
        "session_id": normalized.get("session_id"),
    }

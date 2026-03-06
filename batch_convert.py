#!/usr/bin/env python3
"""Convert prompt-history.jsonl and tool-inputs/results.jsonl to simplified format.

Usage:
  convert_batch.py <input>             # write to <input-stem>-normalized.<ext>
  convert_batch.py <input> <output>    # write to specified output file
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from src.normalize import normalize_input

# Note: filtering is applied after normalization.
FIELDS = [
    # "timestamp",
    # "cwd",
    # "session",
    "event",
    "prompt",
    "tool",
    "args",
]

# Note: filtering is applied after normalization.
TOOL_ARG_FIELDS = {
    "command",
    "intent",
    "includePattern",
    "glob",
    "path",
    "paths",
    "pattern",
    "prompt",
    "query",
    "questions",
    "url",
}


def parse_timestamp(timestamp):
    """Convert timestamp to Unix milliseconds."""
    if isinstance(timestamp, (int, float)):
        return int(timestamp)
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def filter_args(args):
    """Filter normalized args to configured fields."""
    return {k: v for k, v in args.items() if k in TOOL_ARG_FIELDS}


def filter_fields(entry):
    """Pick configured fields from entry, parsing timestamp."""
    result = {}
    for field in FIELDS:
        if field == "timestamp" and "timestamp" in entry:
            result[field] = parse_timestamp(entry["timestamp"])
        elif field in entry:
            result[field] = entry[field]
    return result


def convert_entry(entry):
    """Convert a single entry (auto-detect type: prompt or tool)."""
    normalized = normalize_input(entry)
    if "args" in normalized:
        normalized["args"] = filter_args(normalized["args"])
    return filter_fields(normalized)


def convert_stream(input_stream, output_stream):
    for line in input_stream:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        output_stream.write(json.dumps(convert_entry(entry)) + "\n")


def derived_output_path(input_path):
    p = Path(input_path)
    return p.with_name(p.stem + "-normalized" + p.suffix)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        input_file = sys.argv[1]
        output_file = derived_output_path(input_file)
    elif len(sys.argv) == 3:
        input_file, output_file = sys.argv[1], sys.argv[2]
    else:
        print("Usage: convert_batch.py <input_file> [<output_file>]", file=sys.stderr)
        print("  One arg:   write to <input-stem>-normalized.<ext>", file=sys.stderr)
        print("  Two args:  write to specified output file", file=sys.stderr)
        sys.exit(1)
    with open(input_file) as f_in, open(output_file, "w") as f_out:
        convert_stream(f_in, f_out)
    print(f"Converted {input_file} -> {output_file}", file=sys.stderr)

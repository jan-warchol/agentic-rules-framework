#!/usr/bin/env python3
"""Convert event log to simplified format. Writes to <input-stem>-normalized.<ext>."""

import json
import sys
from pathlib import Path
from src.normalization import normalize_input

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


def convert_entry(entry):
    norm = normalize_input(entry)
    if "args" in norm:
        filtered_args = {k: v for k, v in norm["args"].items() if k in TOOL_ARG_FIELDS}
        norm["args"] = filtered_args
    return {f: norm[f] for f in FIELDS if f in norm}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: batch_convert.py <input_file>", file=sys.stderr)
        sys.exit(1)
    in_path = Path(sys.argv[1])
    out_path = in_path.with_name(in_path.stem + "-normalized" + in_path.suffix)
    with open(in_path) as f_in, open(out_path, "w") as f_out:
        for line in f_in:
            if not line.strip():
                continue
            converted = convert_entry(json.loads(line))
            f_out.write(json.dumps(converted) + "\n")
    print(f"Converted {in_path} -> {out_path}", file=sys.stderr)

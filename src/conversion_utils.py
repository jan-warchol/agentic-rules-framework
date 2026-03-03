"""Shared utilities for JSONL conversion scripts."""

import json
import sys
from datetime import datetime


def parse_timestamp(timestamp):
    """Convert timestamp to Unix milliseconds."""
    if isinstance(timestamp, (int, float)):
        return int(timestamp)
    # ISO 8601 string
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def convert_stream(input_stream, output_stream, convert_entry_fn):
    """
    Generic stream converter that applies convert_entry_fn to each line.

    Args:
        input_stream: Input stream to read JSONL from
        output_stream: Output stream to write converted JSONL to
        convert_entry_fn: Function that takes a dict and returns a converted dict
    """
    for line in input_stream:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        converted = convert_entry_fn(entry)
        output_stream.write(json.dumps(converted) + "\n")


def run_converter(convert_entry_fn, script_name="converter"):
    """
    Main entry point for conversion scripts.

    Handles both stream mode (stdin/stdout) and file mode based on command-line args.

    Args:
        convert_entry_fn: Function that takes a dict and returns a converted dict
        script_name: Name of the script for usage message
    """
    if len(sys.argv) == 1:
        # Stream mode: read from stdin, write to stdout
        convert_stream(sys.stdin, sys.stdout, convert_entry_fn)
    elif len(sys.argv) == 3:
        # File mode: read from file, write to file
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        with open(input_file) as f_in, open(output_file, "w") as f_out:
            convert_stream(f_in, f_out, convert_entry_fn)
        print(f"Converted {input_file} -> {output_file}", file=sys.stderr)
    else:
        print(f"Usage: {script_name} [<input_file> <output_file>]", file=sys.stderr)
        print(f"  No args: read from stdin, write to stdout", file=sys.stderr)
        print(f"  Two args: convert input_file to output_file", file=sys.stderr)
        sys.exit(1)

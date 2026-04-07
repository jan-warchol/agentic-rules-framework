#!/usr/bin/env python3
"""Log manual notes alongside regular hook event data.

Reads multi-line input from the terminal. Each entry is submitted automatically
after a 100ms pause with no new input. Paste your text; it saves itself.

Without arguments: loops, prompting for input repeatedly until Ctrl-C.
With an argument: saves one entry (with the argument as user_comment) and exits.
"""

import json
import os
import select
import sys
import termios
import time
import tty
from pathlib import Path

from src.logging import LOG_FILENAME, get_log_dir, write_entry


def get_session_context(events_file: Path) -> dict:
    """Return session from the most recent PermissionRequest event."""
    result = {}
    try:
        with open(events_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("event") == "PermissionRequest" and "session" in entry:
                        result = {"session": entry["session"]}
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return result


TIMEOUT = 0.1  # seconds of silence before auto-submitting


def read_entry(fd: int) -> str | None:
    """Read bytes until TIMEOUT seconds pass with no new input.

    Returns the accumulated text (stripped), empty string if nothing arrived,
    or None on Ctrl-C.
    """
    chunks = []
    try:
        while True:
            ready, _, _ = select.select([fd], [], [], TIMEOUT)
            if not ready:
                break
            data = os.read(fd, 4096)
            if not data:
                break
            if b"\x03" in data:  # Ctrl-C byte (safety net if ISIG is off)
                return None
            chunks.append(data)
    except KeyboardInterrupt:
        return None
    text = b"".join(chunks).decode(errors="replace")
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def open_tty() -> tuple[int, object, list]:
    try:
        tty_file = open("/dev/tty", "rb", buffering=0)
    except OSError:
        print("Error: no controlling terminal found.", file=sys.stderr)
        sys.exit(1)
    fd = tty_file.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    return fd, tty_file, old_settings


def _save_entry(log_file: Path, why: str, user_comment: str | None = None) -> None:
    entry = {
        "timestamp": int(time.time()),
        **get_session_context(log_file),
        "cwd": str(Path.cwd()),
        "event": "AdditionalInfo",
        "why_permission_prompt_appeared": why,
    }
    if user_comment is not None:
        entry["user_comment"] = user_comment
    write_entry(log_file, entry)


def run_loop(fd: int, log_file: Path, user_comment: str | None = None) -> None:
    prompt = "Why the permission prompt appeared?"
    print(prompt, file=sys.stderr)
    while True:
        text = read_entry(fd)

        if text is None:  # Ctrl-C
            print("\nQuitting.", file=sys.stderr)
            break

        if not text:
            continue

        print(text, file=sys.stderr)
        _save_entry(log_file, text, user_comment)
        print("\nSaved.", file=sys.stderr)

        if user_comment is not None:
            break

        print(prompt, file=sys.stderr)


if __name__ == "__main__":
    log_dir = get_log_dir(os.getcwd())
    log_file = log_dir / LOG_FILENAME
    print(f"Logging to: {log_file}", file=sys.stderr)

    user_comment = sys.argv[1] if len(sys.argv) >= 2 else None
    fd, tty_file, old_settings = open_tty()
    try:
        run_loop(fd, log_file, user_comment)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        tty_file.close()

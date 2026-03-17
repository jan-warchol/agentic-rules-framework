#!/usr/bin/env python3
"""Tests for input normalization and tool call simplification using sample files."""

import json
from pathlib import Path

import pytest

from src.normalization import normalize_input, simplify_tool_input

TESTS_DIR = Path(__file__).parent.parent
PLATFORMS = ["claude-code", "copilot-cli", "vscode-copilot"]


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def make_normalize_cases():
    cases = []
    for platform in PLATFORMS:
        inputs = load_jsonl(TESTS_DIR / "sample-inputs" / f"{platform}.jsonl")
        expected = load_jsonl(TESTS_DIR / "samples-normalized" / f"{platform}-normalized.jsonl")
        for i, (inp, exp) in enumerate(zip(inputs, expected)):
            cases.append(pytest.param(inp, exp, id=f"{platform}-entry{i}"))
    return cases


def make_simplify_cases():
    cases = []
    for platform in PLATFORMS:
        inputs = load_jsonl(TESTS_DIR / "sample-inputs" / f"{platform}.jsonl")
        expected = load_jsonl(TESTS_DIR / "samples-simplified" / f"{platform}-simplified.jsonl")
        for i, (inp, exp) in enumerate(zip(inputs, expected)):
            cases.append(pytest.param(inp, exp, id=f"{platform}-entry{i}"))
    return cases


@pytest.mark.parametrize("entry,expected", make_normalize_cases())
def test_normalize(entry, expected):
    assert normalize_input(entry) == expected


@pytest.mark.parametrize("entry,expected", make_simplify_cases())
def test_simplify(entry, expected):
    assert simplify_tool_input(entry) == expected

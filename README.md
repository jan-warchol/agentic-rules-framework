# Agentic rules framework

Framework for defining tool use rules, file access rules, post-tool hooks etc.
Because what matters today are the guardrails and tools for steering the agent
in the right direction.

## Why create this?

1.  **Why not CLAUDE.md / AGENTS.md?** Instructions written there can be helpful,
    but they can also be ignored by the agent. Using hooks with deterministic code
    is better whenever possible.

2.  **Why not Claude Code / editor settings?** Deny rules in settings do not allow
    specifying reasons. Without them, agents will try to find workarounds, rather
    than follow the intent of the user.

3.  **Obvious** - `agent-rules.yaml` file is self-explanatory. Even without the
    hooks, agents can (and do!) read it to understand the intended behaviour.

4.  **Contextual** - trying to describe _all_ the rules in AGENTS.md / CLAUDE.md
    would pollute the context. Instead, provide the agent with feedback about the
    very thing it is doing at the moment.

## Installation

### Requirements

[`uv`](https://docs.astral.sh/uv/) package manager - install it with
`curl -LsSf https://astral.sh/uv/install.sh | sh` (or see
[other installation methods](https://docs.astral.sh/uv/getting-started/installation/)).

### Claude code

First, register the marketplace:

```
/plugin marketplace add jan-warchol/agentic-rules-framework
```

Then install the plugin itself:

```
/plugin install check-agent-rules@agentic-rules-framework
```

### Other platforms

TODO.

## Features

- deny list for paths, **with explanations** - useful e.g. when some files, like
  interface definitions, are considered "the source of truth" and shouldn't be
  modified without user awareness.
- deny list for commands, **with explanations** - useful e.g. if your agent has a
  tendency to run tests in multiple non-standard ways (which results in frequent
  permission prompts) - simply suggest alternative, approved command.
- allow list for commands (regular expresion patterns).

## `agent-rules.yaml`

This is where the rules should be defined. This file should be placed in the
directory from which you run your agent. All relative paths will be resolved
relative to the directory in which you run `claude`.

```yaml
# Path must be an exact match (regex patterns not supported yet).
deny_edits:
  - path: agent-rules.yaml
    reason: Only human can edit the agent rules configuration.
  - path: src/interfaces.ts
    reason: >
      Modifying or extending interfaces can only be done by a human operator.
      If you think changing an interface is necessary, report that to the user.

# Deny list uses partial matching ("rm -rf" will match "echo test && rm -rf /tmp")
deny_commands:
  - pattern: "rm -rf"
    reason: Destructive command. Instead, use "trash" to move files to system trash.

# Allow list uses full matching (anchors ^ and $ are implied)
allow_commands:
  - pattern: "trash .*"
```

## How it works

The tool defines hooks that run `check_agent_rules.py` script before tool usage
to check whether the tool should be allowed, denied or confirmed with the user.
`check_agent_rules.py` loads rules from `agent-rules.yaml` file located in the
directory where the agentic tool is running.

See [.claude-plugin/plugin.json](.claude-plugin/plugin.json) for Claude Code
configuration and [.github/hooks](.github/hooks) for GitHub Copilot configuration.

The script `check_agent_rules.py` has a simple sructure:

- load rules
- normalize agent-specific input format
- check normalized input against the rules
- wrap decision in format appropriate for the agent.

## Future roadmap

- defining post-tool hooks (run linter, tests and let the agent fix the code
  if needed)
- integrating tools for code quality metrics (code duplication level, cognitive
  complexity)
- documenting installation process for other platforms (GitHub copilot CLI,
  VScode copilot chat)

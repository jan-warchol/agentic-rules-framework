# Agentic rules framework

Framework for defining tool use rules, file access rules, post-tool hooks etc.
Because what matters today is the tooling around the agent, to guide it so that
it will work like you want.

## Why create this tool?

1.  **Why not CLAUDE.md / AGENTS.md?** - instructions written there can be helpful,
    but they can also be ignored by the agent. Using hooks with deterministic code
    is better whenever applicable.

2.  **Why not define hooks in VSCode settings?** - First, using `chat.tools.terminal.autoApprove`
    does not allow fine-grained behaviour (providing deny reason for the agent).
    Second, I want these rules to be defined in a visible place and in a plain,
    readable format, not hidden away in a json config somewhere.

## Features

* allowing tools (regular expresion patterns)
* denying tools **with explanation for the agent** - for example, if your agent
  has a tendency to create ad-hoc python scripts for testing (which results in frequent
  permission prompts), you can deny python usage with a comment "use pytest instead" -
  and it works!

## agent-rules.yaml

This is where the rules should be defined. See the example file in this repo.

## Hooks

The [.github/hooks/hooks.json](.github/hooks/hooks.json) file defines hooks that:

1. Log prompts and tool usage for further analysis
2. Runs `agent_rules.py` before tool usage to assess whether the tool should be
   allowed, denied or confirmed with the user.

## Future roadmap

- defining denied file paths (for files that the agent should leave alone)
- defining post-tool hooks (run linter, tests and let the agent fix the code
  if needed)
- integrating tools for code quality metrics (code duplication level, cognitive
  complexity)
- support for other platforms (first claude code, then probably GH copilot CLI)

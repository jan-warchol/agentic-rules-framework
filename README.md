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

Basically, the agents need to know _why_ they shouldn't do some things. If they are
simply forbidden something without an explanation, they will stubbornly try again
and again, or find workarounds. When provided with the reason, they will actually
be more compliant, as they will aim to follow the intent behind the rules. This could
theoretically be accomplished with instructions in CLAUDE.md / AGENTS.md, but:
- the rules must be deterministic, not subject to model's opinion
- describing _all_ the rules in AGENTS would pollute the context unnecessarily.

Also, rules defined in a visible place with clear purpose can be read and enacted
by the agent, even without the hooks themselves (it's very common that agent reads
`agent-rules.yaml` during a session and corrects its reasoning based on what is
written there) .

## Features

* allowing tools (regular expresion patterns)
* denying tools **with explanation for the agent** - for example, if your agent
  has a tendency to create ad-hoc python scripts for testing (which results in frequent
  permission prompts), you can deny python usage with a comment "use pytest instead" -
  and it works!
* denying editing specific paths **with explanation for the agent** - for example, if
  there are files that shouldn't be modified without deep consideration, because they
  are considered "source of truth" (e.g. interface definitions), you can mark them as
  such (with an explanation so that the agent will understand that it needs to adapt
  its strategy to these files).

## agent-rules.yaml

This is where the rules should be defined. See the example file in this repo.

## Hooks

Directory [.github/hooks](.github/hooks) contains hooks that:

1. Log prompts and tool usage for further analysis
2. Run `agent_rules.py` before tool usage to assess whether the tool should be
   allowed, denied or confirmed with the user.

## Future roadmap

- defining post-tool hooks (run linter, tests and let the agent fix the code
  if needed)
- integrating tools for code quality metrics (code duplication level, cognitive
  complexity)
- support for other platforms (first claude code, then probably GH copilot CLI)

To log additional information about permission requests for later debugging, use
`log_additional_info.py` script.

You can also setup a shell helper:

```bash
log_permission_note() {
    arf_plugin_path=$(
      jq -r \
      '.plugins["check-agent-rules@agentic-rules-framework"][0].installPath' \
      ~/.claude/plugins/installed_plugins.json
    )
    uv run --project "$arf_plugin_path" "$arf_plugin_path/log_additional_info.py" "$1"
}

alias lp='log_permission_note'
```

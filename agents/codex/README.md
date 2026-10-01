# Codex setup

Status: documentation-backed template; end-to-end Skylit authentication and tool discovery have not been certified in this kit.

1. Open this repository in Codex and run the offline sample first.
2. Provision a Skylit API key through your own account. Make `SKYLIT_API_KEY` available to the process running Codex; a desktop app may not inherit your terminal environment.
3. Merge [config.example.toml](config.example.toml) into your existing Codex configuration, following the [official MCP configuration guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli). Do not replace existing configuration.
4. Check the server with `codex mcp list` or the host's MCP controls. Ask for account usage only and confirm the discovered tool name matches `account_usage`.

The template allows only account lookup to start. Do not remove the allowlist wholesale. Add the exact read tools needed for an approved workflow after checking access and credit costs. If the gateway advertises a different name, verify it against the official catalogue before editing the allowlist.

Suggested first prompt:

> Read the Ticker Investigator workflow contract and run the offline sample. Explain which fields are fictional. If I explicitly ask to connect, inspect account usage only; do not query market data yet.

This configuration does not add a client-side credit ceiling. Tool timeouts and prompts do not enforce a workflow budget. The bounded live workflow is still planned. Keep sandbox and tool approvals enabled.

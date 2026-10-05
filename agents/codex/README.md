# Codex setup

**Start by copying the [README prompt](../../README.md#copy-paste-connect) into Codex.** Use a repository-scoped coding session that can run local commands. Access to this repository, Git and Python 3.11+ are needed; the agent can check prerequisites and explain anything missing. Do not attach a private vault.

## Local workflows first

Read [AGENTS.md](../../AGENTS.md) and follow [Start here](../../docs/start-here.md) connection-first: `doctor`, then the user stores their key once with `login` in their own terminal, then `account --welcome` and `first-chart --live` (a 1-credit chart) after an explicit yes. No MCP setup, Python packages or model API key is needed. Without API access yet, show the offline node-tracker chart instead. Codex account/subscription requirements are separate.

Use the [capability map](../../docs/capabilities.md) to route later questions to the four recipes, watchlist or all 77 endpoint previews. Local REST live paths are implemented with synthetic tests; authenticated verification is pending. They enforce documented request/credit caps and stop rules. Live commands use the key stored by `login` or a secure process environment, only for an authorized live plan; desktop processes may not inherit a terminal environment, which is why `login` is preferred. Never paste keys into chat.

## Optional direct MCP connection

This is a separate path; it is unnecessary for local examples. End-to-end Codex authentication and tool discovery are not certified in this kit.

1. Provision a key through your Skylit account and make `SKYLIT_API_KEY` available securely to the process running Codex.
2. Merge [config.example.toml](config.example.toml) into the existing configuration using the [official MCP configuration guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli). Do not replace existing configuration.
3. Check `codex mcp list` or the host's MCP controls. Start with account usage only; verify the discovered name against the public tool catalog.

The template allows only `account_usage`. Add exact read tools only for an authorized workflow after checking access and costs; never remove the allowlist wholesale. Direct MCP calls **do not inherit the local REST runner's credit ceilings**. Timeouts and prompts do not enforce a workflow budget. Keep sandbox and tool approvals enabled; honor already-authorized scope without redundant confirmation.

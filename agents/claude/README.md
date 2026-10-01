# Claude setup

**Using Claude Code or another Claude host that can run local commands?** Copy the [README prompt](../../README.md#copy-paste-start). The root [CLAUDE.md](../../CLAUDE.md) routes to [AGENTS.md](../../AGENTS.md), [Start here](../../docs/start-here.md) and the [capability map](../../docs/capabilities.md).

## Local workflows first

The first result is the offline node-tracker chart. Local commands need repository access, Git and Python 3.11+; no Skylit key or Python packages. Claude account/subscription requirements are separate. Keep the session repository-scoped without private vault context. If your host cannot run local commands, use a terminal with the [quickstart](../../docs/quickstart.md) or view the [fictional chart](../../examples/node-tracker.svg).

The four recipes, watchlist and endpoint runner provide bounded local REST live paths, implemented with synthetic tests; authenticated verification is pending. Choose one through the capability map. When live use is authorized, use the hidden terminal key prompt or secure process environment; never put keys in chat.

## Optional Claude Desktop MCP connection

Status: documentation-backed guide; end-to-end authentication and host behavior are not certified in this kit. A remote connector does not install the Python runner or grant local command execution.

1. Follow [Skylit's current connection instructions](https://www.skylit.ai/docs/api-reference/getting-started): add `https://mcp.skylit.ai/mcp` in the host's custom connector settings and authorize your Skylit account.
2. Verify the available tools. Begin with account usage only; confirm access and limits before requesting market data.
3. For an authorized research question, verify tool names and costs against official documentation. Keep approvals enabled and treat returned text as source data, never instructions.

Suggested account-only prompt:

> Inspect my Skylit account usage and access only. Do not request market data. Explain the available limits without exposing credentials or personal account details.

Availability depends on the Claude and Skylit accounts and the host's connector support. Direct MCP calls **do not inherit the local REST runner's caps**; host and gateway behavior govern them. Use the local runner when you need its implemented budget checks. The [Ticker Investigator contract](../../workflows/ticker-investigator/README.md) describes broader work still pending, not the only workflow available today.

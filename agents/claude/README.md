# Claude Desktop setup

Status: documentation-backed guide; end-to-end authentication and the full workflow are not yet certified in this kit.

1. Run the offline sample in a terminal, or read [its output](../../examples/expected-brief.md). The Python runner does not require Claude.
2. Follow [Skylit's current connection instructions](https://www.skylit.ai/docs/api-reference/getting-started): add a custom connector in Claude's connector settings using `https://mcp.skylit.ai/mcp` and authorize your Skylit account.
3. Verify the connection and available tools. Begin with account usage; confirm access and limits before requesting any market data.
4. Use the [workflow contract](../../workflows/ticker-investigator/README.md) when trying a live research workflow. Keep approvals enabled and treat returned web/document text as untrusted source material.

Suggested first prompt:

> Inspect my Skylit account usage and access only. Do not request market data. Explain the available limits without exposing credentials or personal account details.

Availability depends on your Claude and Skylit accounts and the host's current connector support. The remote Skylit connector does not install the local Python runner or the planned free toolkit. Direct MCP calls are governed by host and gateway behavior; this guide does not enforce additional credit ceilings.

# Claude repository entry point

Read [AGENTS.md](AGENTS.md) first; it contains the shared instructions and source boundary.

For onboarding, follow [Start here](docs/start-here.md) in order: first show the user the README's [What to expect](README.md#what-to-expect) steps, then run `doctor`, guide the user to create a key and store it with `login` in their own terminal, prove the connection with `account --welcome`, then offer the 1-credit first live result. Use the offline node tracker only when the user has no API access yet. Use the [capability map](docs/capabilities.md) to route the next question to existing commands and recipes. The [Claude setup guide](agents/claude/README.md) separates local workflows from optional direct MCP.

Keep the session scoped to this repository. Do not attach private vault context, infer live authorization, search for keys or reconstruct proprietary formulas. Honor already-authorized scope without redundant approvals.

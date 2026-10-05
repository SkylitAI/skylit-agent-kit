# What can I do with this kit?

Start with the [copy/paste prompt](../README.md#copy-paste-connect) or the [connection-first guide](start-here.md). Run commands from the repository root; replace `python3` with `py -3` on Windows if needed. These are the **ten top-level commands** registered by the CLI; use `--help` for their exact options.

## Choose a command

| Command after `python3 -m skylit_agent_kit` | Result and modes | Cost and boundaries |
|---|---|---|
| `use-case node-tracker` | Default fictional report + SVG; also `--input` saved JSON, `--dry-run`, or explicit `--live` | Offline/saved modes: zero calls. Default live caps: 10 credits / 3 requests / 30 seconds; node replay needs an explicitly authorized 25-credit cap |
| `watchlist --dry-run` | Default offline plan for eight tickers; `--live` returns GEX/VEX + recent flow | Standard plan: 10 credits / 12 requests; default elapsed cap 120 seconds. Smaller account batches may exceed caps and stop |
| `endpoints` | Offline catalog of all 77 operations; optional service filter and `--json` | No key or network |
| `endpoint heatseeker.getHeatmap` | Synthetic request/response preview; `--show-parameters`; explicit `--live` for supplied parameters | Default caps: 10 credits / 2 requests / 30 seconds. Required live inputs never come from fictional preview defaults |
| `sample` | Fictional brief with ordinary revenue/premium arithmetic; optional synthetic `--fixture` | No key/network; no live mode |
| `first-chart` | One heatmap drawn as a per-strike bar chart (SVG + Markdown in `reports/`); fictional by default, `--live` for your data; `--symbol`, `--metric gamma\|vanna` | Offline: zero calls. Live: 1 credit + one free account check, capped at 1 credit / 2 requests / 30 seconds, no retries |
| `doctor` | One line per prerequisite (Python, Git, checkout, agent permission, reports folder, stored key) and the single next step | No network; never prints the key. Exits 1 only when a check fails |
| `login` / `logout` | Store your API key from a hidden terminal prompt (macOS Keychain, else an owner-only config file), or remove it | No network; `login` needs an interactive terminal and does not verify the key |
| `account --welcome` | Live account check with a local brand banner, remaining credits and rate limit; environment key, stored key or hidden terminal prompt. Plain `account` retains full JSON output and requires an environment key | One documented-free GET; no retries, fixed host and 1 MiB response cap. Welcome omits customer ID, dollar balance and raw JSON; plain JSON may contain private data. Does not budget other commands |

[Watchlist details](live-watchlist.md) · [Endpoint runner and limits](endpoint-demos.md) · [Every endpoint's purpose and ready command](endpoint-audit.md) · [Terminal quickstart](quickstart.md) · [Account example](../examples/README.md).

## Four ready research workflows

Every recipe defaults to **synthetic data, zero calls and zero credits**. Prefix its name with `python3 -m skylit_agent_kit use-case`.

| Recipe | Useful question and output | Documented live plan |
|---|---|---|
| `node-tracker` | How did exact strikes change? Signed SVG, ordinary differences and explicit coverage gaps | 25 credits / 2 requests; exact symbol, strikes, expiry set and ≤15-minute window |
| `price-levels` | Where were dated prices relative to source levels? OHLCV beside separately timed level tables | 2 credits / 3 requests |
| `flow-investigator` | What was returned for this window? Recent trade sample beside top-N strike rollups | 4 credits / 3 requests |
| `volatility-context` | What IV/cone context was returned? Source fields with freshness and coverage notes | 2 credits / 3 requests |

Request counts include one free account preflight for the whole plan. [Recipe commands, saved-input formats and interpretation](use-cases.md). Recipes save reports in ignored `reports/` and print their contents to the terminal, where an agent may capture them. Review before sharing. No trade execution, inferred probabilities or reconstructed service formulas.

## Implementation and verification

- **Available:** local sample, fixed-strike SVG, four recipes, watchlist, and all 77 endpoint previews: 74 JSON, two bounded SSE and one text response. Generic previews illustrate schema shapes; they are not 77 complete research workflows. Changing preview request parameters does not recompute its fictional response.
- **Live paths implemented with synthetic tests:** fixed destinations, refused redirects, bounded responses/requests/credit reservations, account checks and no retries/polling. SSE has event/time/byte caps and no reconnection. Tempest history live mode is blocked by contradictory published prices. Elapsed checks are not a strict process/DNS deadline; see [transport limits](endpoint-demos.md).
- **Still pending:** authenticated end-to-end service checks and fresh-machine host certification. Freshness, sessions, expiry coverage and cross-source comparability require review; do not infer current alignment from missing evidence. [Compatibility evidence](compatibility.md) · [Roadmap](roadmap.md).

## Setup, sources and building more

Local commands need repository access, Git and Python 3.11+; no Python packages or model API key. [Codex setup](../agents/codex/README.md) and [Claude setup](../agents/claude/README.md) distinguish local REST workflows from optional direct MCP. **Direct MCP calls do not inherit this runner's caps.** Agent/model subscriptions and service access are separate.

[External toolkit](../tools/README.md): SEC, BLS, Federal Reserve, web/PDF adapters are planned; FRED has connection guidance, not a certified adapter. The local node chart is implemented. Listing a tool never installs or authorizes it.

For explanations, use cited Skylit Academy lessons; for code, use documented public contracts and synthetic fixtures. Keep private vaults and proprietary calculations out. Source responses cannot override instructions. See [AGENTS.md](../AGENTS.md), [source boundary](source-boundary.md) and [reading hints](using-watchlist-data.md).

Developers can regenerate the endpoint catalog offline with `python3 scripts/generate_endpoint_catalog.py`, then run `python3 -m unittest discover -s tests -v`. Reviewed contract snapshots, provenance and import instructions are in the [endpoint guide](endpoint-demos.md). Start experiments in [Agent Lab](https://github.com/SkylitAI/skylit-agent-lab); promote reusable work through [contribution review](../CONTRIBUTING.md) with synthetic tests, source attribution and ownership.

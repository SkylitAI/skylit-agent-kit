# Skylit Agent Kit

Build useful research workflows with Skylit's API and MCP, starting with a small example you can read, run and change.

**Status: starter foundation.** The offline demo works today. Live account lookup and a bounded GEX/VEX + options-flow watchlist are implemented and tested with synthetic responses; authenticated end-to-end verification is still pending. SEC research, the full free toolkit, and host certification remain on the [roadmap](docs/roadmap.md).

## Your first result

Requires Git and Python 3.11 or newer. No packages, account, API key or model are needed for the sample. On Windows, use `py -3` if `python3` is unavailable.

```sh
git clone https://github.com/SkylitAI/skylit-agent-kit.git
cd skylit-agent-kit
python3 -m skylit_agent_kit sample
```

You get a short, clearly labeled **fictional** research brief with calculations, sources, gaps and zero usage costs. [See the expected output](examples/expected-brief.md).

Change a number in `examples/fixtures/demo.json` and run again. Try setting a value to `null` to see how the report handles missing information.

## Real GEX/VEX and recent flow

Start with a free, offline plan for **SPXW, SPY, QQQ, TSLA, MSFT, AAPL, AMZN and META**:

```sh
python3 -m skylit_agent_kit watchlist --dry-run
```

When you want this run to use your Skylit account:

```sh
python3 -m skylit_agent_kit watchlist --live --output reports/watchlist.md
```

If needed, the terminal asks for your API key with typing hidden. Create it in your [Skylit Developer page](https://app.skylit.ai/developer); never paste it into an agent chat. No packages or model API key are required. The standard eight-symbol plan uses **12 requests / 10 documented credits** when your account allows a single heatmap batch. The program checks account access, balance, symbol support and the complete plan before paid calls, then runs once without retries. Unsupported or missing symbols stay visible; SPXW is never replaced with SPX.

The compact report shows source GEX/VEX nodes and recent flow, with separate board/trade times. This is implemented against the [public API contracts](docs/live-watchlist.md), with synthetic tests; a real account run has not yet been certified.

Suggested agent prompt:

> Run the watchlist dry-run for SPXW, SPY, QQQ, TSLA, MSFT, AAPL, AMZN and META. Explain the cost. When I ask for the live run, use the existing secure environment or guide me to the hidden terminal key prompt. Keep the default caps, report unavailable data explicitly, and show a compact report. Do not ask me to paste a key into chat.

## Choose your next step

| I want to… | Start here |
|---|---|
| Understand the data and build more | [Reading hints, guardrails and extensions](docs/using-watchlist-data.md) |
| Get GEX/VEX and recent flow | [Bounded watchlist guide](docs/live-watchlist.md) |
| Run and customize the sample | [Quickstart](docs/quickstart.md) |
| Connect Claude Desktop | [Claude guide](agents/claude/README.md) |
| Connect Codex | [Codex guide and config template](agents/codex/README.md) |
| Verify my Skylit account access | [Live account example](examples/README.md) |
| Explore free sources and tools | [Toolkit catalogue](tools/README.md) |
| Build the live Ticker Investigator | [Workflow contract](workflows/ticker-investigator/README.md) |
| Contribute a fix or experiment | [Contribution guide](CONTRIBUTING.md) |

```mermaid
flowchart LR
  A[Try offline] --> B[Connect Skylit]
  B --> C[Build a workflow]
  C --> D[Experiment in Agent Lab]
  D --> E[Review for Agent Kit]
```

## What belongs here

This kit holds maintained examples, shared helpers, agent setup guides and tested workflows. [Skylit Agent Lab](https://github.com/SkylitAI/skylit-agent-lab) is the home for community experiments. A useful experiment can graduate through a reviewed kit pull request.

The code license does not include Skylit service access or third-party data rights. Free sources can have usage limits, and your agent or model may have its own costs. Check current access in the [Skylit Developer page](https://app.skylit.ai/developer) and [official docs](https://www.skylit.ai/docs/api-reference/getting-started).

## Develop

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q skylit_agent_kit tests
```

The runtime and tests use only Python's standard library. Run from the repository root; installation into site-packages is not required. See the [support matrix](docs/compatibility.md), [security guidance](SECURITY.md) and [roadmap](docs/roadmap.md).

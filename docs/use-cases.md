# Build one useful workflow

Run these from the repository root. All four commands default to **fictional fixtures, no key, no network and zero credits**. Each creates a private Markdown report in ignored `reports/`; the node tracker also creates a standalone SVG. Source contracts were checked on 2026-10-01; live behavior remains unverified until an authorized account run.

| Your question | Run it offline | What you get | Live plan cost |
|---|---|---|---:|
| How did these exact strikes change? | `python3 -m skylit_agent_kit use-case node-tracker` | Signed chart, magnitude and adjacent changes, visible gaps | 25 credits; 2 requests |
| Where were prices relative to source levels? | `python3 -m skylit_agent_kit use-case price-levels` | OHLCV table and separately dated level table | 2 credits; 3 requests |
| Which strikes appear in this flow window? | `python3 -m skylit_agent_kit use-case flow-investigator` | Trade sample, source scores and top-N strike rollup | 4 credits; 3 requests |
| What volatility context was returned? | `python3 -m skylit_agent_kit use-case volatility-context` | IV tenor values, source fields and freshness/coverage flags | 2 credits; 3 requests |

Request counts include **one free account preflight for the whole plan**. Reports print the exact validated URLs, parameters and documented costs. No recipe polls, retries or raises its own budget. `--dry-run` prints only the plan.

Use `--output "reports/my research/nodes.md"` to choose a report name or subfolder.
Missing folders are created; existing files are never overwritten. Reports use
UTF-8, and chart/tutorial links are relative to the saved report. Quote paths
containing spaces when entering commands.

The bundled examples contain fictional SPY data (gamma for exposure recipes).
Changing `--symbol` or `--metric` does not generate another dataset. Use
`--dry-run` to inspect a different plan, or `--input` with matching saved data to
render it without network access.

## 1. Watch fixed strikes over time

![Synthetic fixed-strike replay](../examples/node-tracker.svg)

```bash
python3 -m skylit_agent_kit use-case node-tracker \
  --strikes 100,105 --output reports/my-nodes.md
```

The fictional example shows strike 100 changing from −100 to −120: signed change −20, magnitude change +20. Later the strike axis shifts, strike 105 disappears, and an expiry set changes. The tracker keeps the same strike identity and leaves incomparable observations blank. Source `currentKing` is never an identity key.

The response is the actual public `/v1/historical/range` structure:

```text
meta.metric
  data.symbols[].symbol
    axes[]: id → strikes + expirations
    frames[]: asOf + axis + spot + values
                 ↓ resolve the frame's axis ID
       exact symbol + metric + expiration set + strike
                 ↓
       signed value → absolute magnitude → ordinary differences
```

There is no inferred observation between frames. The chart uses actual UTC time spacing and breaks on missing strikes, duplicate timestamps and changed expiry sets. It rejects malformed timestamps, non-finite values, duplicate strikes/axes, unknown axes and mismatched vector lengths. Changes compare adjacent comparable observations; a zero prior magnitude has no percentage change. Tables show the first 200 timestamps per strike, while the SVG uses all returned observations.

To render your saved API response, supply its exact identity and window:

```bash
python3 -m skylit_agent_kit use-case node-tracker \
  --input /absolute/path/to/saved-range.json --symbol SPY --metric gamma \
  --strikes 100,105 --expirations 2026-10-02 \
  --from 2026-09-30T14:00:00Z --to 2026-09-30T14:06:00Z
```

Choose strikes actually relevant to your saved data; 100/105 are fictional demonstration prices. Saved files are size-limited to 8 MiB and checked before rendering. User-supplied files are labeled **source data**, not synthetic; the kit cannot certify their provenance. The window must match the saved response. No key is read. Delay and attribution metadata are preserved when returned; missing attribution does not establish redistribution rights.

For one live replay, replace the input argument with `--live` and explicitly allow its 25-credit cost:

```bash
python3 -m skylit_agent_kit use-case node-tracker --live \
  --symbol SPY --metric gamma --strikes 100,105 --expirations 2026-10-02 \
  --from 2026-09-30T14:00:00Z --to 2026-09-30T14:06:00Z \
  --max-credits 25 --max-requests 2 --max-seconds 30
```

Use an available historical window and relevant strikes/expirations. The live recipe accepts one exact symbol and a timezone-qualified window of at most 15 minutes. The default 10-credit cap is unchanged and stops this request before reading a key. If `SKYLIT_API_KEY` is absent, a terminal asks for it with hidden input. Never put a key in chat or command arguments. Account balance/rate limits are checked before the paid call. Elapsed checks are not a hard process deadline.

**Build with an agent:**

> Use only this repository and my supplied replay JSON. Plot the gamma values for these fixed strikes and this exact expiry set. Preserve source asOf timestamps, signs and coverage gaps. Explain signed change versus magnitude change in three sentences. Make no new API calls and infer no positioning cause, lifecycle stage or trading action.

Educational adaptation: [Node Lifecycle: Fresh, Tested, Delivered, and Decaying Levels](https://www.skylit.ai/learn/node-lifecycle) motivates checking a level over time. This demo does not infer tap counts, lifecycle classes or probabilities. Exposure changes alone cannot establish their cause.

## 2. Put dated prices beside exposure levels

```bash
python3 -m skylit_agent_kit use-case price-levels --dry-run
python3 -m skylit_agent_kit use-case price-levels --live --symbol SPY \
  --metric gamma --expirations 2026-10-02 \
  --from 2026-09-30T14:00:00Z --to 2026-09-30T14:06:00Z \
  --max-credits 2 --max-requests 3
```

`atlas.getHistory` supplies OHLCV; `heatseeker.getLevels` supplies source classifications and signed exposure. The report shows dated bars, close range/change and the separate levels `asOf`. Historical bars plus current levels do **not** become a simultaneous historical replay. The levels response does not expose actual expirations, so actual expiry coverage remains unverified. Atlas does not echo its symbol: saved-file symbol identity requires your provenance.

> Use the saved price-levels report to describe the dated price range, then list the source-classified levels. Separate observations from hypotheses. Check the timestamps and report missing comparability. Do not turn a node label into a buy/sell instruction or make new calls.

Educational adaptations: [Charts First: Market Structure Before Exposure](https://www.skylit.ai/learn/charts-first) starts with a price question before exposure context; [Reading Heatseeker Maps: King Nodes, Gatekeepers, Floors, and Ceilings](https://www.skylit.ai/learn/reading-heatseeker) gives context for node labels. [Trinity Mode: Cross-Index Alignment with SPX, SPY, and QQQ](https://www.skylit.ai/learn/trinity-mode) discusses cross-instrument views; this one-symbol recipe makes no Trinity alignment claim.

## 3. Investigate a flow window

```bash
python3 -m skylit_agent_kit use-case flow-investigator --live --symbol SPY \
  --from 2026-09-30T14:00:00Z --to 2026-09-30T14:06:00Z \
  --max-credits 4 --max-requests 3
```

`flowseeker.getFlow` returns at most 10 trades; `flowseeker.getFlowStrikes` returns at most 10 strike rollups for the same explicit window. The report shows trade timestamps/expirations and source Flow Scores, then total/net premium by returned strike. These are different scopes: the sample is not the whole-window total. Source scores are neither recalculated nor treated as probabilities.

> Explain the saved flow report. Identify overlapping strikes between the trade sample and the rollup, keep their distinct coverage visible, and list the evidence missing to infer intent. Preserve service scores as source data; do not reconstruct their formulas or make new calls.

## 4. Inspect volatility context

```bash
python3 -m skylit_agent_kit use-case volatility-context --live --symbol SPY \
  --max-credits 2 --max-requests 3
```

`heatseeker.getVolIv` plus `heatseeker.getVolCones` preserve source fields, `asOf`, session, stale/frozen status and missing coverage. The public IV description defines `svx1d`, `svx9`, `svx30`, `svx3m`, `svx6m` in annualized volatility points, plus `iv_rank` and `iv_pct`. The fictional fixture uses those names. The current public description documents `horizons[]` values priced from current spot and `levels[]` values anchored at a past close. The fixture supplies fictional values for both, with null/missing optional skew and event fields. Reports preserve `anchor`, `priced_at`, `until`, `em1_pct` and the source bands rather than reconstructing them. The two collections answer different timing questions; do not treat a moving horizon as a fixed intraday budget.

> Explain the returned IV tenor values and freshness flags. Preserve the field names and documented units. List missing cone horizons, and state whether source timing still needs review. Do not infer probabilities, prices, or trade actions from undocumented fields.

## Reuse the tools in your own code

```python
from skylit_agent_kit.endpoint_demo import plan_request, execute_plans
from skylit_agent_kit.recipe_reports import render_recipe

plans = [
    plan_request('heatseeker.getVolIv', {'symbols': 'SPY'}),
    plan_request('heatseeker.getVolCones', {'symbols': 'SPY'}),
]
# Run only after explicit live authorization. Get the key securely, never in chat.
responses = execute_plans(plans, api_key, max_credits=2,
                         max_requests=3, max_seconds=30)
data = {plan['id']: response for plan, response in zip(plans, responses)}
markdown = render_recipe('volatility-context', data, 'SPY', 'gamma', None, None)
```

For recipe `--input`, save an object keyed by the exact endpoint IDs shown above, with each value the unmodified endpoint response. The node tracker takes the range response directly. Time-window saved recipes require `--symbol`, `--from`, `--to`; price-levels/node-tracker also require `--expirations`. They use local data only. Do not commit private inputs or reports.

Technical sources: [Heatseeker public API contract](https://api.skylit.ai/v1/openapi.json), [Flowseeker public API contract](https://www.skylit.ai/docs/flowseeker-openapi.yaml), [Atlas public API contract](https://www.skylit.ai/docs/atlas-openapi.yaml). Maintained owners: Agent Kit maintainers; changes require synthetic regression tests and source-boundary review. See [compatibility evidence](compatibility.md) and [source boundary](source-boundary.md).

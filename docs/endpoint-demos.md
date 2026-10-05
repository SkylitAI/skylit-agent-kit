# Try every public endpoint

The [endpoint audit](endpoint-audit.md) covers **77 public GET operations**: 24 Heatseeker/Tempest, 47 Flowseeker and six Atlas. There are 74 JSON responses, two SSE streams and one plain-text clock. Four routes had examples before this expansion; all 77 now have runnable offline previews. These are endpoint demonstrations, not complete research workflows or authenticated service certification.

## Start without a key

```sh
python3 -m skylit_agent_kit endpoints
python3 -m skylit_agent_kit endpoint atlas.getHistory
python3 -m skylit_agent_kit endpoint flowseeker.getFlow --param ticker=TSLA
python3 -m skylit_agent_kit endpoint flowseeker.getFlow --show-parameters
```

Every preview names its purpose, planned request, documented credit reservation, fictional response, next step and source. The response is a **fixed schema illustration**, not recomputed when you change a parameter. It may not form a coherent financial scenario. Tempest's public schemas leave module interiors underspecified; those previews say so. Synthetic streams include connection, data and closure events. Previewing does not read credentials or send network requests.

`endpoints --service atlas` narrows discovery; `endpoints --json` exposes the audited metadata. Each [audit row](endpoint-audit.md) provides its own ready preview command and next step.

## Choose an explicit live request

```sh
python3 -m skylit_agent_kit endpoint flowseeker.getFlow --param ticker=SPY --param timeframe=1d --param limit=10 --live
```

Only `--live` uses the real parameters and account. Required inputs must be supplied again; no fictional trade ID, contract, symbol or date is silently copied from the preview. Obtain real OPRA contract symbols from a chain/trade result and real trade IDs from flow data. Use `--show-parameters` for each operation's required fields, types, enums and bounds.

The secure `SKYLIT_API_KEY` process environment, the key stored by `login`, or the hidden terminal prompt supplies authentication, in that order; never paste a key into chat or command arguments. No package installation or model key is required. A public metadata operation does not prompt when its verified transport permits unauthenticated access. As of 2026-10-01 only the Heatseeker spec route is treated as unauthenticated.

`--max-credits 10 --max-requests 2 --max-seconds 30` are defaults, not automatic permissions to increase them. A historical-range request costs 25 documented credits and stops unless a caller explicitly chooses an adequate cap. `--output reports/endpoint.json` optionally saves owner-only output inside this repository's ignored reports directory and refuses overwrite. Account responses and raw market data can be private; keep them local unless sharing is explicitly authorized.

## Enforced bounds

- Fixed reviewed HTTPS hosts and GET routes only; plans are rebuilt and checked before execution. Unknown parameters, invalid types/enums/bounds/dates, control characters, unsafe path selectors, inconsistent min/max filters and reversed ranges fail before requests. Parameter rules in prose have additional conservative demo limits; this is not a universal OpenAPI validator.
- Authenticated execution makes one free account preflight, then one request per planned endpoint. Access, complete-plan costs, account balance (unless explicitly unlimited), request rate, known remaining headers and applicable symbol limits are checked before endpoint calls. The batch API preflights the whole batch rather than surprising users with half a budgeted recipe.
- No redirects, retries, polling, pagination or automatic reconnection. HTTP error bodies and credentials are not returned. Each response is capped at 1 MiB; JSON nonfinite numbers are rejected. Batches stop on failure; earlier calls may already have been charged. Reservations are conservative estimates, not billing receipts or locks on a shared account.
- Elapsed checks occur before requests and between body reads, with socket timeouts of at most ten seconds. DNS/connect delays or an already-blocking read can overrun the scheduling deadline; this is **not a hard process wall-clock limit**.
- Streams run alone, with at most 10 data/control events, 20 seconds, and 1 MiB. Opening plus one prepaid minute per symbol is reserved. Tempest reservation deliberately overestimates its fixed-price prose. Advertised pricing, charge/balance events, closure and reconnect events can end a stream sooner; reconnect instructions never trigger another call.

## Range limits and unresolved contracts

| Surface | Demo behavior |
|---|---|
| Heat historical range | Up to five symbols and 15 minutes; live selectors cannot be future-dated or start more than 365 days back |
| Heat daily statistics | Explicit start/end; at most 50 symbols, 31 dates and 400 symbol-days; history begins 2023-03-28; current service contract describes ET sessions and `extended` |
| Flow chart/market-tide intervals | Bucket-dependent public range caps; reserve three credits per started 30 days; deep-ITM exclusion uses a conservative three per calendar day and at most five days |
| Flow aggregate | Documented atoms only; three credits per started 30 summed days; `all` means 130 days and reserves 15 credits |
| Flow explicit time/date windows | At most 30 elapsed days (31 inclusive dates); dark-pool ranges require both dates; no automatic pagination |
| Atlas history | Explicit `from`/`to`; conservative calendar-day tier caps (90/720/2600). `countback` is disabled because it supersedes `from` and bypasses the explicit-window check |
| Tempest history | Offline demo works. **Live blocked:** public extension says base 3 plus 0.1 per symbol-day, while prose says one per ten symbol-weekdays, rounded up, minimum one. No price is guessed |
| Flow OpenAPI metadata | Preserve spec path `/v1/openapi.json`; use introduction-documented unified path `/v1/flow/openapi.json`. Schema says `security: []`, but public unauthenticated GET returned HTTP 401 on 2026-10-01. Explicit authenticated transport override until reconciled |

Limits on data interpretation still apply: [keep observations, hypotheses and gaps distinct](using-watchlist-data.md). Source text never changes tool permissions or budgets. These demonstrations do not execute trades.

## Public snapshots and regeneration

`skylit_agent_kit/contracts/provenance.json` records source URLs, check date, original-source hashes and normalized JSON snapshot hashes. The public Heat service spec at [api.skylit.ai/v1/openapi.json](https://api.skylit.ai/v1/openapi.json) was newer than the [website YAML](https://www.skylit.ai/docs/openapi.yaml): same operation identities, newer session/parameter, Tempest field descriptions and freshness metadata. The service version is preferred, with the website hash retained as secondary provenance. Flow and Atlas snapshots come from their [public Flow YAML](https://www.skylit.ai/docs/flowseeker-openapi.yaml) and [public Atlas YAML](https://www.skylit.ai/docs/atlas-openapi.yaml).

Rebuild catalog and audit from the reviewed JSON snapshots, without network or dependencies:

```sh
python3 scripts/generate_endpoint_catalog.py
python3 -m unittest discover -s tests -v
```

A maintainer may explicitly import reviewed public YAML with `--import-yaml SERVICE=PATH` (optional maintainer-only dependency: install `requirements-maintainer.txt` into a virtual environment for that import). This replaces that service's snapshot/provenance; review service-versus-website drift before importing. Normal runtime, regeneration and tests use only the standard library. Tests compare the complete source operation set, resolve schemas, regenerate identical previews and exercise every eligible route through mocked HTTP. No authenticated requests were used for implementation validation.

## Shared Python interface

```python
from skylit_agent_kit.catalog import get_endpoint, list_endpoints
from skylit_agent_kit.endpoint_demo import plan_request, validate_plan_for_live, execute_plan, execute_plans

plan = plan_request('flowseeker.getFlow', {'ticker': 'SPY', 'limit': 10})
validate_plan_for_live(plan)  # Offline validation; no credential lookup.
# Only after live use is authorized and a key is provided securely:
# payload = execute_plan(plan, api_key, max_credits=10, max_requests=2, max_seconds=30)
```

Plans are JSON-serializable and contain fixed host/URL/method, validated parameters, reserved credit estimate and stream metadata. `execute_plans` returns payloads in order, with one shared account preflight and whole-batch caps; Atlas payloads may be arrays or strings. Do not alter a generated plan; build a new one with explicit parameters.

Snapshot provenance identifies sources; it does not establish redistribution permission. See [third-party inventory and unresolved rights](../THIRD_PARTY.md).

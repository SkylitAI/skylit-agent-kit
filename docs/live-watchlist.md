# Bounded GEX/VEX and flow watchlist

Implementation status: tested with independently authored synthetic responses, not certified against an authenticated account. This workflow copies documented service values; it does not reconstruct Skylit formulas, use private vault content, fetch SEC filings or recommend trades.

## First use

From the cloned repository, with Python 3.11+:

```sh
python3 -m skylit_agent_kit watchlist --dry-run
python3 -m skylit_agent_kit watchlist --live --output reports/watchlist.md
```

The first command is offline: it does not read a key, contact a service or write reports. The second explicitly opts into one live run. If no `SKYLIT_API_KEY` is already provided securely to this process, an interactive terminal prompts for it with typing hidden. Create your own key at the [Developer page](https://app.skylit.ai/developer). Never paste it into chat, put it in command arguments or commit it. The program does not load `.env` files. A noninteractive agent without a key stops with instructions for the hidden prompt.

No model, extra Python packages, agent installation or global configuration changes are needed. The only personal step is provisioning access through your own Skylit account. Repository access is separate; an internal GitHub repository requires authorization.

Default symbols: **SPXW, SPY, QQQ, TSLA, MSFT, AAPL, AMZN, META**. Duplicates are removed in order. Customize them with `--symbols NVDA,SPY`; SPXW is never silently replaced with SPX. The free heatmap catalog controls heatmap availability only; flow is attempted independently for every requested symbol.

## What the report means

The overview selects the source-classified `king` node, or explicitly labels the largest returned magnitude if no king exists. Expanded tables show at most three largest returned nodes per metric and the latest three valid returned flow trades. Display values use six significant digits. These are source values and simple selections, not locally derived GEX/VEX, signals or scores.

- Gamma and vanna boards request `maxStrikes=92` and `maxExpirations=5`: up to 92 strikes around spot and the nearest five expirations. They do not represent the whole chain. Actual returned expirations and board `asOf` are shown for each metric. The underlying `spot` can be newer than the board.
- Flow requests a `1d` window and at most 10 trades. Source totals and aggregates are shown separately from the truncated trade display. Response `meta.timestamp` is generation time; the most recent returned trade has its own timestamp.
- `--date YYYY-MM-DD` chooses an explicit **flow** trading date. Without it the service chooses the trading date, which can be a previous session. It does not change the live heatmap date. Separate endpoints are not an atomic snapshot, and the report does not assert that all observations are fresh.
- Missing, unsupported, invalid, empty and not-requested results stay visible. A 404 marks that component unavailable and permits remaining planned calls; other request failures stop the entire run. There are no retries, streams, polling or automatic follow-up calls.

## Limits and costs

Each run first makes free `GET /v1/account` and `GET /v1/symbols` requests. The account must be active/API-eligible and have readable limits. The complete paid plan must fit the configured caps, documented account request rate, current server rate allowance when supplied, and account credit balance (unless the account explicitly reports unlimited usage). Failure stops before paid requests. Missing catalog metrics may reduce the heatmap plan; smaller account batches may increase it.

The default eight-symbol plan is two heatmaps (gamma, vanna) plus eight flow calls: **10 documented credits, 12 total requests** if one batch can contain the supported symbols. Defaults are `--max-credits 10 --max-requests 12 --max-seconds 120`. Budgets are explicit options; the program never increases them automatically. Attempts reserve their documented cost even when a response fails, so reported reservation is conservative, not verified billing. Account changes or use by other clients can still interrupt a run; these local limits are not a transactional spending ceiling on a shared account.

Only HTTPS requests to fixed `api.skylit.ai` routes are allowed. Redirects are refused, response bodies are capped at 1 MiB, errors exclude raw bodies, and credentials are redacted if echoed in a response. The transport uses a socket timeout of at most ten seconds and checks the elapsed deadline before starting requests and between body reads. **This is not a hard wall-clock process deadline:** platform DNS/connect delays or a current blocking read can overrun it. After a deadline is observed, no further request starts. Server rate headers can stop the run early; the command never sleeps and retries.

## Saving private results

`--output reports/watchlist.md` writes the Markdown report with owner-only permissions and refuses to overwrite an existing file. Choose a new name for another run. Paths must stay within this repository's ignored `reports/` directory; symlinked roots are rejected. Without `--output`, the report is printed locally.

`--save-raw` optionally writes full returned **market** responses to a timestamped JSON file in `reports/`, also with owner-only permissions. It does not persist account responses or credentials. Review reports before sharing; ignore rules are not a permission to publish account data. Raw persistence is off by default.

## Public contracts and evidence

Technical contracts checked 2026-10-01:

- [Heatmap OpenAPI](https://www.skylit.ai/docs/openapi.yaml): `/v1/account`, `/v1/symbols`, `/v1/heatmap`, `SymbolHeatmap`, `StrikeNode`. Heatmap calls cost one documented credit each; account and symbol discovery are free.
- [Flow OpenAPI](https://www.skylit.ai/docs/flowseeker-openapi.yaml): `/v1/flow/{ticker}`, `FlowSuccess`, `FlowResponse`, `FlowTradeItem`, `AggregateScores`. Each flow call costs one documented credit.

Tests cover all eight symbols, deduplication and batching, exact query parameters, smaller account limits, insufficient budgets/balance/rate allowance, malformed/partial responses, per-component 404s, global failures, response-size/deadline controls, credential redaction and an offline CLI path. No authenticated API call was used to produce the implementation or test fixtures. A successful dry-run or synthetic test is not evidence that your current account entitlements or live service responses have been verified.

# Examples

New here? [Copy the agent prompt](../README.md#copy-paste-start) or use [Start here](../docs/start-here.md). The [capability map](../docs/capabilities.md) covers all commands and their modes.

| Example | Run or open | What it demonstrates |
|---|---|---|
| Fixed-strike chart | `python3 -m skylit_agent_kit use-case node-tracker` · [SVG preview](node-tracker.svg) | Exact strikes across changing axes and explicit gaps |
| Prices, flow or volatility | [Four use cases](../docs/use-cases.md) · [synthetic fixtures](fixtures/use-cases/) | Default offline reports; optional saved JSON or authorized live plans |
| Every public endpoint | `python3 -m skylit_agent_kit endpoints` · [77-entry audit](../docs/endpoint-audit.md) | Synthetic request/response shapes; bounded opt-in live runner |
| Simple arithmetic brief | `python3 -m skylit_agent_kit sample` · [expected output](expected-brief.md) | Fictional [teaching fixture](fixtures/demo.json), not an API response |
| Multi-symbol GEX/VEX + flow | `python3 -m skylit_agent_kit watchlist --dry-run` | Offline plan; [live watchlist guide](../docs/live-watchlist.md) |
| Account access only | `python3 -m skylit_agent_kit account` | Explicit live GET; details below |

Offline examples use no credentials or service calls. Reports are ignored local files; do not commit private inputs or outputs. Authenticated live behavior remains unverified.

## Live account lookup

Create your own API key through the [Skylit Developer page](https://app.skylit.ai/developer). Inject `SKYLIT_API_KEY` through your secret manager or process environment. `.env.example` documents the variable; the runner does **not** load `.env` files automatically. Never paste a real key into a prompt, committed file or shell command saved in history.

Once the variable is available to your terminal:

```sh
python3 -m skylit_agent_kit account
```

The example sends one HTTPS GET to `https://api.skylit.ai/v1/account`, which [Skylit documents as free](https://www.skylit.ai/docs/api-reference/getting-started). It prints the returned JSON for local inspection. The response can contain private account information: do not commit or attach it to issues.

Behavior: fixed destination, redirects rejected, 10-second socket timeout, response capped at 1 MiB, no retry on any failure. A socket timeout is not a total elapsed-time budget. It does not call market-data endpoints or establish a budget for other clients. No live account was used to certify this starter; HTTP behavior is fixture-tested.

Stop on 401/402/403 and resolve access or credits. For 429 or 503, follow the [official retry guidance](https://www.skylit.ai/docs/api-reference/rate-limits-and-retries) before making a later manual attempt. Never disable TLS verification.

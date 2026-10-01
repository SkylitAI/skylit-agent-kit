# Examples

- `fixtures/demo.json`: fictional input for the offline workflow.
- `expected-brief.md`: output produced from that fixture.
- `python3 -m skylit_agent_kit account`: explicit live REST access example.

## Live account lookup

Create your own API key through the [Skylit Developer page](https://app.skylit.ai/developer). Inject `SKYLIT_API_KEY` through your secret manager or process environment. `.env.example` documents the variable; the runner does **not** load `.env` files automatically. Never paste a real key into a prompt, committed file or shell command saved in history.

Once the variable is available to your terminal:

```sh
python3 -m skylit_agent_kit account
```

The example sends one HTTPS GET to `https://api.skylit.ai/v1/account`, which [Skylit documents as free](https://www.skylit.ai/docs/api-reference/getting-started). It prints the returned JSON for local inspection. The response can contain private account information: do not commit or attach it to issues.

Behavior: fixed destination, redirects rejected, 10-second socket timeout, response capped at 1 MiB, no retry on any failure. A socket timeout is not a total elapsed-time budget. It does not call market-data endpoints or establish a budget for other clients. No live account was used to certify this starter; HTTP behavior is fixture-tested.

Stop on 401/402/403 and resolve access or credits. For 429 or 503, follow the [official retry guidance](https://www.skylit.ai/docs/api-reference/rate-limits-and-retries) before making a later manual attempt. Never disable TLS verification.

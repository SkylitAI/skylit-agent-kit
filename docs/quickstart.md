# Quickstart

## 1. Run the sample

From the repository root, run `python3 -m skylit_agent_kit sample`.
The bundled DEMO ticker, figures and timestamp are fictional. Nothing is fetched, and no model is called.

To save a local report:

```sh
mkdir -p reports
python3 -m skylit_agent_kit sample > reports/demo.md
```

`reports/` is ignored by Git. Review any report before sharing it.

## 2. Make it yours

Copy `examples/fixtures/demo.json` to `reports/my-demo.json`. Keep `synthetic` set to `true`, edit the revenue or premium values, and run:

```sh
python3 -m skylit_agent_kit sample --fixture reports/my-demo.json
```

Changing the ticker changes its label only; it does not fetch that company's data.
Numbers must be nonnegative and finite; `null` means unavailable. The timestamp needs a timezone and periods use `YYYY-Q1` through `YYYY-Q4`. This teaching fixture is not Skylit's API schema.

## 3. Connect when ready

Use the [account example](../examples/README.md) to check access, or follow the [Claude](../agents/claude/README.md) or [Codex](../agents/codex/README.md) guide. Live research is a separate milestone; there is no `sample --live` switch.

## Troubleshooting

| Symptom | Action |
|---|---|
| `No module named skylit_agent_kit` | Run from the cloned repository root |
| Python command missing | Install Python 3.11+; on Windows try `py -3` |
| Invalid fixture | Compare your file with the bundled JSON; check timestamps, numeric values and `synthetic` |
| Authentication/access error | Check the official Developer page; do not repeatedly retry |
| No MCP tools | Check the host's connection state and permissions; record the host version in an issue |

Never include keys, account responses or private research in an issue.

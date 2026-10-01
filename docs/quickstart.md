# Quickstart

**Prefer copy/paste into an agent?** Use the [single README prompt](../README.md#copy-paste-start), then follow [Start here](start-here.md). This page is the manual terminal path. Requires repository access, Git and Python 3.11+; no API key for the offline examples.

## First, see a chart

After cloning the repository and opening its root directory:

```sh
python3 -m skylit_agent_kit use-case node-tracker
```

Open the printed SVG and Markdown paths in `reports/`. Data is fictional; there are zero service calls or credits. See [all four recipes](use-cases.md) and the [capability map](capabilities.md) for the next question. On Windows, try `py -3` instead of `python3`.

## Also try the small calculation sample

From the repository root, run `python3 -m skylit_agent_kit sample`.
The bundled DEMO ticker, figures and timestamp are fictional. Nothing is fetched, and no model is called.

To save a local report:

```sh
mkdir -p reports
python3 -m skylit_agent_kit sample > reports/demo.md
```

`reports/` is ignored by Git. Review any report before sharing it.

## Customize the sample

Copy `examples/fixtures/demo.json` to `reports/my-demo.json`. Keep `synthetic` set to `true`, edit the revenue or premium values, and run:

```sh
python3 -m skylit_agent_kit sample --fixture reports/my-demo.json
```

Changing the ticker changes its label only; it does not fetch that company's data.
Numbers must be nonnegative and finite; `null` means unavailable. The timestamp needs a timezone and periods use `YYYY-Q1` through `YYYY-Q4`. This teaching fixture is not Skylit's API schema.

## Connect when ready

Use the [account example](../examples/README.md) to check access, or follow the [Claude](../agents/claude/README.md) or [Codex](../agents/codex/README.md) guide. For real GEX/VEX and recent flow, use the separate [watchlist command](live-watchlist.md): run `python3 -m skylit_agent_kit watchlist --dry-run`, then add `--live` when ready to use your account. There is no `sample --live` switch; the sample remains fictional. The watchlist is synthetic-tested; authenticated verification is pending.

## Troubleshooting

| Symptom | Action |
|---|---|
| `No module named skylit_agent_kit` | Run from the cloned repository root |
| Python command missing | Install Python 3.11+; on Windows try `py -3` |
| Invalid fixture | Compare your file with the bundled JSON; check timestamps, numeric values and `synthetic` |
| Authentication/access error | Check the official Developer page; do not repeatedly retry |
| No MCP tools | Check the host's connection state and permissions; record the host version in an issue |

Never include keys, account responses or private research in an issue.

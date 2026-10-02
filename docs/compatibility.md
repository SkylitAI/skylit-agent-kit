# Compatibility and evidence

Never equate a setup guide with an end-to-end certification.

| Surface | Current evidence | Remaining check |
|---|---|---|
| Offline Python sample | Local tests on Python 3.11.14 and 3.14.5; CI configured for 3.11 and 3.14 on Linux | Confirm CI result for the exact review commit |
| REST account example | Mocked success, auth/rate/service failures, bad JSON, response size and redirect tests; welcome confirms active/API-eligible state and omits private account fields | Authorized account smoke test and inline-image display in each host |
| REST GEX/VEX + flow watchlist | Synthetic contract-shaped responses; batching, budgets, rate limits, gaps, sanitized failures and CLI dry-run tested | Authorized eight-symbol run; actual account entitlements, billing and freshness |
| All 77 endpoint demos | Public contract inventory, synthetic schema previews, serialized request and mocked transport tests; 74 JSON, two bounded SSE, one text response | Authenticated verification; Tempest history live mode blocked by contradictory public prices |
| Four research recipes | Offline reports and fixed-strike SVG; saved-input validation and mocked whole-plan account preflight | Authorized live node, price, flow and volatility runs; service timing and account billing |
| Claude Desktop | Guide based on Skylit documentation | Fresh-machine sign-in, tool discovery, complete workflow and optional tools |
| Codex | TOML template based on official configuration docs | Environment propagation, sign-in, account tool and workflow |
| OpenClaw, Hermes | Planned community compatibility probes | Versioned setup and failure-path evidence |
| ChatGPT, Meta Muse | Planned feasibility probes | Verify public integration surface and authentication before claiming support |
| Cursor, Gemini CLI, other hosts | Future candidates | A real workflow need and a maintainer |

For each verified integration, record date, host/version, OS, auth method, exact tools, sample/live result, failure cases and known limits. Do not attach credentials or raw private responses. Native host capabilities are not assumed interchangeable.

## Combined offline review — 2026-10-01

Runtime revision `f0fcf93eafe0c31cf9c2ee7b3f1af7fd976571db` combines the release
hardening and usability changes. On macOS arm64, all 109 tests passed with both
Python versions above. A fresh clone reproduced the sample, customized its
calculation and missing-data case, rendered all four recipes, and ran all 77
endpoint previews with Python network operations and credential prompts blocked.
All 133 repository-relative Markdown file links resolved.

The offline node chart was also inspected in the Codex in-app browser through a
loopback-only preview serving the selected synthetic SVG. Its complete chart,
legend, gaps, fictional label and attribution link were visible. The preview was
closed afterward. This verifies local rendering, not a host's Skylit connection.

Native Windows execution, authenticated host/service behavior and hosted CI for
the review branch remain unverified. Passing local checks does not close the
[release gates](release-readiness.md).

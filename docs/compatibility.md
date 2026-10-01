# Compatibility and evidence

Never equate a setup guide with an end-to-end certification.

| Surface | Current evidence | Remaining check |
|---|---|---|
| Offline Python sample | Local tests on Python 3.14; CI configured for 3.11 and 3.14 on Linux | Confirm CI result for the exact commit |
| REST account example | Mocked success, auth/rate/service failures, bad JSON, response size and redirect tests | Authorized account smoke test |
| Claude Desktop | Guide based on Skylit documentation | Fresh-machine sign-in, tool discovery, complete workflow and optional tools |
| Codex | TOML template based on official configuration docs | Environment propagation, sign-in, account tool and workflow |
| OpenClaw, Hermes | Planned community compatibility probes | Versioned setup and failure-path evidence |
| ChatGPT, Meta Muse | Planned feasibility probes | Verify public integration surface and authentication before claiming support |
| Cursor, Gemini CLI, other hosts | Future candidates | A real workflow need and a maintainer |

For each verified integration, record date, host/version, OS, auth method, exact tools, sample/live result, failure cases and known limits. Do not attach credentials or raw private responses. Native host capabilities are not assumed interchangeable.

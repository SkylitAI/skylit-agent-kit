# Security

Do not publish credentials, private data or exploitable security details in an issue, pull request or Actions log.

## Reporting a vulnerability

A working GitHub private-report route has **not yet been verified** for this internal repository (checked 2026-10-01). Until a private channel is confirmed, [open an issue requesting a private security contact](https://github.com/SkylitAI/skylit-agent-kit/issues/new?title=Private%20security%20contact%20request) containing only that request, with no vulnerability details. Existing internal contributors may contact repository owners through an established private channel. No dedicated monitored inbox or response deadline is claimed here.

A maintainer must enable and verify GitHub private vulnerability reporting during the approved public-release process, then replace this interim text with the tested report link before announcing the release. See [release readiness](docs/release-readiness.md). Once a private channel is available, include the affected revision, impact and a minimal sanitized reproduction; omit keys and private account data.

## Scope and safe use

This kit is pre-release. Live integrations still have the pending checks listed in [compatibility.md](docs/compatibility.md); no maintenance window or response SLA is promised.

Use your own account and least-privilege access. Revoke or rotate exposed keys. Keep TLS verification, host sandboxing and tool approvals enabled. Treat retrieved documents and tool outputs as untrusted data, never as instructions that authorize new actions.

The sample is offline and synthetic. The account example has one fixed HTTPS destination, rejects redirects, bounds response size and does not retry. It does not implement paid market-data workflows. Direct MCP clients use the host and service controls; this kit's prompt guidance cannot enforce their budgets.

Pull-request checks must not receive production credentials or execute untrusted code in a privileged workflow. Do not add `pull_request_target` execution of contribution code. Review dependency changes and action pins. Generated reports stay local and are ignored by Git.

## Proprietary knowledge boundary

Private formulas, scoring logic, calibration values and strategies must stay outside this kit and community experiments. Consume documented service outputs; do not recreate private internals. The [source boundary](docs/source-boundary.md) applies to code, prompts, tests, datasets, screenshots and Git history. Automated tests and secret scanners do not establish that intellectual property is safe to publish.

## Automated checks

Offline CI uses synthetic fixtures and read-only repository access. A separate security workflow scans fetched history with Gitleaks, redacts findings, and uploads no scan artifacts. Dependency review and Python CodeQL run for public repositories; internal/private repositories require the corresponding GitHub features and explicit repository variables before those jobs run. CodeQL alone receives `security-events: write` for its results. See the release checklist for activation and required-check verification.

The optional YAML importer uses pinned PyYAML with `safe_load`; runtime and tests remain standard-library-only. Review scan findings and dependency updates before release. Secret scans do not prove ownership, licensing clearance or absence of private intellectual property.

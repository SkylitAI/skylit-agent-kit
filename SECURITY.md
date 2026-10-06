# Security

Do not publish credentials, private data or exploitable security details in an issue, pull request or Actions log.

## Reporting a vulnerability

Report vulnerabilities privately through GitHub: [open a private security advisory](https://github.com/SkylitAI/skylit-agent-kit/security/advisories/new) (Security → Report a vulnerability). Do not open a public issue for a vulnerability. The repository owners receive the report. No response deadline is promised.

Include the affected revision, impact and a minimal sanitized reproduction; omit keys and private account data.

## Scope and safe use

This kit is an early public release (no version tag yet). Live integrations still have the pending checks listed in [compatibility.md](docs/compatibility.md); no maintenance window or response SLA is promised.

Use your own account and least-privilege access. Revoke or rotate exposed keys. Keep TLS verification, host sandboxing and tool approvals enabled. Treat retrieved documents and tool outputs as untrusted data, never as instructions that authorize new actions.

The sample is offline and synthetic. The account example has one fixed HTTPS destination, rejects redirects, bounds response size and does not retry. It does not implement paid market-data workflows. Direct MCP clients use the host and service controls; this kit's prompt guidance cannot enforce their budgets.

Pull-request checks must not receive production credentials or execute untrusted code in a privileged workflow. Do not add `pull_request_target` execution of contribution code. Review dependency changes and action pins. Generated reports stay local and are ignored by Git.

## Proprietary knowledge boundary

Private formulas, scoring logic, calibration values and strategies must stay outside this kit and community experiments. Consume documented service outputs; do not recreate private internals. The [source boundary](docs/source-boundary.md) applies to code, prompts, tests, datasets, screenshots and Git history. Automated tests and secret scanners do not establish that intellectual property is safe to publish.

## Automated checks

Offline CI uses synthetic fixtures and read-only repository access. A separate security workflow scans fetched history with Gitleaks, redacts findings, and uploads no scan artifacts. Dependency review and Python CodeQL run automatically because the repository is public. CodeQL alone receives `security-events: write` for its results. See the release checklist for activation and required-check verification.

The optional YAML importer uses pinned PyYAML with `safe_load`; runtime and tests remain standard-library-only. Review scan findings and dependency updates before each release. Secret scans do not prove ownership, licensing clearance or absence of private intellectual property.

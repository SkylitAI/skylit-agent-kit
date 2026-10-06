# Public release status

**The repository is public** (GitHub visibility `public` since 2026-10-01). The repository owner approved the public release on 2026-10-06, including redistribution of the bundled contracts. This page records what that rests on and what is still open. It is not a live compatibility certification or a complete security audit.

## Release gates

| Gate | Status — 2026-10-06 |
|---|---|
| Copyright and contribution rights | **Resolved.** The repository owner, who has authority for SkylitAI, confirmed the MIT license and its `2026 SkylitAI contributors` notice. |
| Contract redistribution | **Resolved.** The rights owner (Skylit) approved redistributing the three bundled snapshots and their generated derivatives under the existing notices. See [THIRD_PARTY.md](../THIRD_PARTY.md). |
| Responsible reviewer | **Resolved.** [.github/CODEOWNERS](../.github/CODEOWNERS) assigns `@prodij` (repository admin) to every path. Code-owner review is not yet a required merge rule. |
| Private reporting | **Resolved.** GitHub private vulnerability reporting is enabled (API read-back 2026-10-06), and [SECURITY.md](../SECURITY.md) links the report form. |
| Host security controls | **Mostly applied.** Secret scanning, non-provider patterns, validity checks and push protection are enabled; main protection is applied (below). Dependabot security updates are still disabled. The ruleset proposals below remain optional. |
| Source and exposure review | **Done for the current history.** On 2026-10-06, Gitleaks scanned all 14 remote branches (39 commits) with zero findings. A keyword review of history and all PR/review text found no private vault material, internal hosts, account identifiers or keys. Commit author metadata includes contributors' email addresses, as Git always does. |
| Exact revision checks | **Open.** `CodeQL Python` failed on main (2026-10-05) because Code Scanning could not process the uploaded SARIF. The cause is unconfirmed; a GitHub default CodeQL setup running alongside the advanced workflow would produce this. Live evidence remains as stated in [compatibility.md](compatibility.md): authenticated service checks are still pending. |

## Historical snapshot — 2026-10-01 (before publication)

Inspected `main`: `a9439b9c2412300e08d409c8e8e1caf05fd4c2dc`. Repository visibility: **internal**. Main protection was false; repository/inherited ruleset listing was empty. Dependabot vulnerability alerts and security updates, Code Security, secret scanning, non-provider patterns, validity checks and push protection were disabled. Private reporting was unverified (404). Actions allowed all actions, did not require SHA pins, defaulted to read permissions, and could not approve pull requests. These settings were read only and may change independently of this branch.

## Applied main protection — 2026-10-01

The approved solo-maintainer policy is applied through classic branch protection
and was read back from GitHub: PRs required; zero required approvals; an up-to-date
branch; passing `test (3.11)` and `test (3.14)` checks bound to GitHub Actions app
`15368`; resolved conversations; administrator enforcement; no force pushes,
deletion or configured review bypass allowances. Code-owner and last-pusher
approvals are not required. No visibility, access, tag or other security settings
were changed. The ruleset proposals below remain separate and unapplied.

## Optional administrator proposals — approval required

1. **Merge rules:** [main-ruleset.json](release/main-ruleset.json) targets `main`, requires a PR, one independent approval including code-owner review, dismissal of stale approvals, approval after the latest push, resolved review threads, an up-to-date branch and passing checks. It blocks force pushes and deletion and has no bypass actors. It also requires CodeQL results with no high/critical security alerts or error-level alerts. Confirm a real code owner and working analyses before activation.
2. **Required checks:** `test (3.11)`, `test (3.14)`, `Secret scan`, `Dependency review`, `CodeQL Python`, bound to GitHub Actions app ID `15368`. The two test names/app ID were verified on the base revision; the three new job names are proposals until an authorized branch run confirms them. Enable dependency graph/review and CodeQL first; make sure their jobs execute successfully, rather than skip, before these rules become the release gate.
3. **Tags:** [tag-ruleset.json](release/tag-ruleset.json) blocks updates, deletion and force moves of existing `v*` tags with no bypass. Creation still follows existing repository write permissions; create release tags only from the reviewed, checked main commit. Restricting tag creation to a release team/app needs that actor's confirmed numeric identity and separate approval; do not add an all-admin bypass to immutable tags.
4. **Dependencies and code:** enable dependency graph, Dependabot alerts and security updates. Use the committed advanced CodeQL workflow; avoid simultaneous default and advanced setups. For internal/private analysis, confirm GitHub Code Security entitlement, then set repository variables `ENABLE_CODEQL=true` and `ENABLE_DEPENDENCY_REVIEW=true`. These flags do not grant the GitHub entitlement. For a public repo the workflow enables these jobs automatically. Review all alerts, including lower-severity findings not blocked by the threshold.
5. **Secrets:** enable secret scanning and push protection, including supported non-provider patterns and validity checks. Review existing-history alerts. Use the smallest approved bypass scope; do not create blanket exemptions. The Gitleaks job complements these settings and is not provider-aware revocation or credential validation.
6. **Reporting:** enable private vulnerability reporting when supported and verify the external researcher's report button at the repository Security → Advisories page. Only then add the tested `security/advisories/new` route to SECURITY.md. Confirm an owner handles incoming reports; no response SLA is invented.
7. **Actions:** retain read-only default workflow permissions and disallow PR approval. Require full commit SHA pins and restrict allowed actions to the workflows' reviewed set: `actions/checkout`, `actions/setup-python`, `actions/dependency-review-action`, and `github/codeql-action/{init,analyze}`. Review the exact allowlist syntax and resolved pins in Settings before applying. Keep all production secrets out of these workflows and require approval for workflows from outside collaborators. Only CodeQL's job needs `security-events: write`.

The JSON files are reviewable REST request bodies, **not applied configuration**. They use the [GitHub ruleset API](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset). An admin should re-read existing/inherited rules immediately before an approved application, avoid duplicates, and verify the effective branch/tag rules afterward. No organization-wide 2FA or access changes are proposed.

## Implemented repository controls

- Watchlist reports retain response attribution/disclaimers even when observations are missing; standalone SVGs include visible credit and a fixed Skylit link. Recipe reports preserve notices too. Source strings render as inert text. Synthetic examples keep their fictional labels.
- MIT is unchanged. README and the third-party inventory separate kit licensing from API Data and upstream rights, and record the owner-approved redistribution of the bundled contracts.
- Offline CI is read-only, has full-SHA action pins, avoids persisted Git credentials and uses synthetic data. Gitleaks scans full fetched history with redaction; no report artifacts are uploaded. CodeQL's elevated permission is isolated to its job. No `pull_request_target` workflow executes contribution code.
- Optional maintainer PyYAML is version-pinned, documented and included in weekly Dependabot checks. Runtime, normal generation and tests remain standard-library-only. The Gitleaks release/checksum needs manual update review.

## Local evidence and limits

At initial audit: 27 reachable commits across fetched remote branches, six PR heads and preserved local branches; no tags. Gitleaks 8.30.1 reported zero findings for reachable history, the isolated worktree and the original checkout including ignored local reports. A separate raw-object scan covered all 134 available blobs and 28 commit objects, including one unreachable commit; zero findings. All 24 retained Actions run-log archives downloaded and scanned; zero findings. GitHub reported zero Actions artifacts and zero releases/assets. Scan outputs and downloaded logs are private local audit material outside this checkout and are not committed.

Scanners are heuristic. They do not clear proprietary methods, prove data rights, detect every secret or establish that revoked/removed remote objects cannot be recovered. Deleted/unavailable remote history, forks, external caches, unlisted artifacts and issue/PR discussion bodies are not exhaustively covered. Recheck after any new commits or publication steps. Keep any sensitive finding private; do not rotate keys, delete evidence or rewrite history without a scoped remediation decision.

The optional PyYAML 6.0.3 import was tested in a disposable copy using a hash-verified wheel: it preserved the Atlas contract and regenerated all 77 endpoints. An OSV query for that exact version returned no advisories on 2026-10-01; this is a point-in-time advisory check, not a guarantee.

Current technical evidence is offline and synthetic. In [draft PR #7](https://github.com/SkylitAI/skylit-agent-kit/pull/7), both Python matrix jobs and the Gitleaks secret scan passed at `e22eb4612c0bb4c3d03c662a96a29418f02e4e81`. CodeQL and dependency review were explicitly skipped because their repository feature gates were not enabled; those skips are not analysis results. Check the PR's latest head and runs before review or merge.

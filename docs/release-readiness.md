# Public release readiness

**Not approved for public release.** This checklist separates implemented repository controls from owner and administrator decisions. It is not a legal clearance, live compatibility certification or complete security audit. Do not change visibility, publish a release, push this review branch or merge it without the corresponding authorization.

## Open release gates

| Gate | Required evidence / next action |
|---|---|
| Copyright and contribution rights | Confirm the actual copyright-owning legal entity and authority to license the contributed material. Keep the current MIT license unchanged pending confirmation. |
| Contract redistribution | Obtain explicit terms/permission for all three bundled snapshots and their generated derivatives listed in [THIRD_PARTY.md](../THIRD_PARTY.md), or replace/remove the material with an approved plan. Public URLs alone are not permission. |
| Responsible reviewer | Obtain an exact GitHub user or `@SkylitAI/team` with write access. Then create `.github/CODEOWNERS` covering `*`, so source, workflows, licensing and security policy all require that owner. Verify GitHub accepts the file. No identity or team has been invented. |
| Private reporting | Verify an actual confidential reporting route. GitHub's private-reporting endpoint returned 404 while the repo was internal; that does not confirm that it is enabled. During the approved publication process, enable/test private reporting and update [SECURITY.md](../SECURITY.md) before announcing release. |
| Host security controls | Approve and apply the proposed repository settings below. Verify resulting settings and failing/successful PR behavior; workflow files alone do not enforce merging rules. |
| Source and exposure review | Review all intended public history, branches, tags, logs, artifacts, issues/PRs and assets; privately resolve any finding. Human IP/provenance review is still required. No private vault comparison was performed. |
| Exact revision checks | Run the complete offline matrix and security jobs against the final reviewed commit. A skipped CodeQL/dependency job is not evidence of analysis. Live evidence remains as stated in [compatibility.md](compatibility.md). |

## Read-only GitHub snapshot — 2026-10-01

Inspected `main`: `a9439b9c2412300e08d409c8e8e1caf05fd4c2dc`. Repository visibility: **internal**. Main protection was false; repository/inherited ruleset listing was empty. Dependabot vulnerability alerts and security updates, Code Security, secret scanning, non-provider patterns, validity checks and push protection were disabled. Private reporting was unverified (404). Actions allowed all actions, did not require SHA pins, defaulted to read permissions, and could not approve pull requests. These settings were read only and may change independently of this branch.

## Proposed administrator settings — approval required

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
- MIT is unchanged. README and the third-party inventory separate kit licensing from API Data and upstream rights, with an explicit unresolved redistribution gate.
- Offline CI is read-only, has full-SHA action pins, avoids persisted Git credentials and uses synthetic data. Gitleaks scans full fetched history with redaction; no report artifacts are uploaded. CodeQL's elevated permission is isolated to its job. No `pull_request_target` workflow executes contribution code.
- Optional maintainer PyYAML is version-pinned, documented and included in weekly Dependabot checks. Runtime, normal generation and tests remain standard-library-only. The Gitleaks release/checksum needs manual update review.

## Local evidence and limits

At initial audit: 27 reachable commits across fetched remote branches, six PR heads and preserved local branches; no tags. Gitleaks 8.30.1 reported zero findings for reachable history, the isolated worktree and the original checkout including ignored local reports. A separate raw-object scan covered all 134 available blobs and 28 commit objects, including one unreachable commit; zero findings. All 24 retained Actions run-log archives downloaded and scanned; zero findings. GitHub reported zero Actions artifacts and zero releases/assets. Scan outputs and downloaded logs are private local audit material outside this checkout and are not committed.

Scanners are heuristic. They do not clear proprietary methods, prove data rights, detect every secret or establish that revoked/removed remote objects cannot be recovered. Deleted/unavailable remote history, forks, external caches, unlisted artifacts and issue/PR discussion bodies are not exhaustively covered. Recheck after any new commits or publication steps. Keep any sensitive finding private; do not rotate keys, delete evidence or rewrite history without a scoped remediation decision.

The optional PyYAML 6.0.3 import was tested in a disposable copy using a hash-verified wheel: it preserved the Atlas contract and regenerated all 77 endpoints. An OSV query for that exact version returned no advisories on 2026-10-01; this is a point-in-time advisory check, not a guarantee.

Current technical evidence is offline and synthetic. The exact test results and revision should accompany the review handoff; hosted security checks remain pending until this branch is authorized to be pushed and run.

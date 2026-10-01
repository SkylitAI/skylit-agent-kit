# Road to v0.1

The initial commit is a foundation, not a certified live agent release. Milestones are gates, not delivery dates.

| Milestone | Deliverable | Current state |
|---|---|---|
| 1. Foundation | Repository, license, offline checks, concrete report, owners and live contracts | Code/docs foundation present; assign maintainers and verify live contracts |
| 2. Useful result | Offline sample plus bounded Skylit/SEC live brief | Offline sample, watchlist, four research recipes and all 77 endpoint previews implemented with synthetic tests; authenticated verification and SEC brief pending |
| 3. Free toolkit | Seven curated capabilities with examples and failure handling | Catalogue and FRED guide present; local fixed-strike SVG and Atlas price-context recipe implemented; broader free-source adapters pending |
| 4. Agent setups | Fresh-machine Claude and Codex runs; other host probes | Guides/templates present; host certification pending |
| 5. Member pilot | Five members, onboarding fixes and a rehearsed contribution | Pending |
| 6. Public release | Tested tag, demo, access, support ownership and triage | Pending |

## Next implementation tasks

1. **Platform owner:** verify account entitlements, selected read schemas, tool costs and retry headers using an authorized test account. Sanitize evidence.
2. **Engineering:** verify the watchlist, endpoint and recipe request/credit caps, elapsed scheduling deadline and stop rules against an authorized account. Synthetic failure tests cover 401/402/403/429/503 and timeouts. Caching and a broader SEC brief remain future work.
3. **Engineering:** add SEC ticker resolution and a cited filing; handle unsupported symbols and throttling.
4. **Engineering + product:** complete a useful live brief, comparing claims to actual responses. Keep calculations deterministic and source text untrusted.
5. **Community + engineering:** certify two host setups, rehearse a lab contribution, then run the pilot.

## Five small contribution candidates

- Improve the Windows quickstart after following it on a clean machine.
- Add a synthetic declining-revenue example with the expected result.
- Add an example showing missing premium observations and the resulting gap.
- Reproduce and document one supported host's account-only connection.
- Improve an error explanation after observing a real onboarding failure, using sanitized evidence.

## Proposed pilot gate

Four of five members reach the offline sample unassisted within ten minutes; all five reach a live result after access is provisioned; at least two return or customize within seven days; one exercises the contribution path; no credential or budget failure. These are learning gates, not proof of market demand.

Before public release, assign code/review ownership, record supported host versions, measure cost per completed brief, finish dependency/data attribution checks and confirm repository visibility. Track useful completed workflows, repeat use, support effort and accepted contributions.

# Source boundary

The agent kit distributes client examples and workflows. Proprietary Skylit calculations remain in Skylit services. This boundary also applies to experiments proposed for Agent Lab and to promotions from the lab.

## Allowed inputs

- Skylit Academy educational material for concepts, terminology, explanations, workflows and worked examples, with lesson attribution.
- Documented public API/MCP contracts and permitted service outputs.
- Approved public references, with citations and relevant usage terms.
- Independently authored synthetic fixtures, clearly labeled fictional.
- Ordinary arithmetic such as the sample's percentage change and share-of-total calculations; these do not implement Skylit scoring models.

## Academy as the educational source

Use Skylit Academy as the educational source of record for public repository tutorials, agent guidance and teaching examples. Record the lesson title and source link so a reviewer can trace each explanation. Label adaptations and fictional datasets clearly. Use official API/MCP documentation for technical contracts.

This source policy applies to both Agent Kit and Agent Lab. Academy material can explain how to interpret service outputs; it does not authorize filling in private implementation details from the vault or reconstructing proprietary service formulas. Keep the private-material boundary below intact.

## Material that must remain private

Do not copy, paraphrase, reconstruct, translate or embed private vault formulas, scoring models, weights, thresholds, calibration values, strategies or internal implementation details. This applies to code, prompts, examples, tests, snapshots, notebooks, generated reports, documentation, images, comments and commit messages. Renaming variables or using fictional inputs does not make a private algorithm publishable.

Do not attach private vault folders, symlinks, retrieval indexes, private agent memory or repository histories to the starter. Work in a repository-scoped session using only approved sources. Local agent isolation depends on actual host permissions; these instructions are not a filesystem sandbox.

## Contribution review

For any domain calculation or dataset change, reviewers must establish approved Academy, public-reference or synthetic provenance. If its origin is uncertain, do not merge or publish it until the owner explicitly clears the specific material. A general request to build an agent or implement a feature is not approval to disclose private knowledge.

Check staged content and reachable Git history before release. Keep private comparison scans local: do not upload vault contents, extracted terms, hashes, examples or scan evidence to public CI, issues or pull requests. CI must not receive vault access. Passing tests or finding no exact text matches does not detect every paraphrase or reconstructed formula; human source review is still required.

If a possible leak is found, stop further distribution, notify the repository owner privately and assess the affected commits/artifacts. Deleting the current file alone does not remove prior history. Coordinate remediation; do not silently rewrite shared history.

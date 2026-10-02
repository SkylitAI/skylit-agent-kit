# Sources, dependencies and redistribution review

The [MIT license](LICENSE) covers this kit's original code and original documentation. It does not grant rights in upstream specifications, API responses, exchange data, third-party material, Skylit service access or trademarks. Public availability and a recorded hash establish provenance, not permission to redistribute.

## Bundled contracts: release gate

| Material | Recorded upstream source | Recorded check | Redistribution evidence |
|---|---|---|---|
| `skylit_agent_kit/contracts/heatseeker.json` | [Service JSON](https://api.skylit.ai/v1/openapi.json); [secondary website YAML](https://www.skylit.ai/docs/openapi.yaml) | 2026-10-01 | No `info.license` or `info.termsOfService` in snapshot; permission unresolved |
| `skylit_agent_kit/contracts/flowseeker.json` | [Flowseeker YAML](https://www.skylit.ai/docs/flowseeker-openapi.yaml) | 2026-10-01 | No `info.license` or `info.termsOfService` in snapshot; permission unresolved |
| `skylit_agent_kit/contracts/atlas.json` | [Atlas YAML](https://www.skylit.ai/docs/atlas-openapi.yaml) | 2026-10-01 | No `info.license` or `info.termsOfService` in snapshot; permission unresolved |

Exact upstream and normalized snapshot SHA-256 hashes are in [provenance.json](skylit_agent_kit/contracts/provenance.json). The Heat snapshot records drift from the website YAML. This inventory does not re-fetch or certify the current live contract.

`contracts/endpoints.json` and `docs/endpoint-audit.md` are generated from these snapshots and contain upstream descriptions and schema material. The same permission review applies to them. Schema-derived endpoint previews are fictional; fictional values do not clear rights in copied schema/prose. The separately authored sample and recipe fixtures in `examples/fixtures/`, and the chart in `examples/node-tracker.svg`, are labeled synthetic; preserve those labels.

**Before public release:** the actual rights owner must approve redistribution of each snapshot and its derived catalog/documentation under specified terms, including any required notices. Record the approved terms and evidence without committing confidential correspondence. If approval is unavailable, remove or replace the affected material and regenerate/retest the dependent features before release. Changing only the current tree does not remove earlier Git objects. Do not rewrite shared history without a separately approved plan.

The copyright-owning legal entity and contribution chain of title also require owner confirmation. The existing MIT file and its `2026 SkylitAI contributors` notice remain unchanged; this inventory does not assert legal ownership or relicense upstream material.

## Dependencies and tooling

| Component | Use / distribution | License or source |
|---|---|---|
| Python 3.11+ standard library | Runtime, tests and ordinary JSON catalog generation; no third-party runtime packages | [Python license](https://docs.python.org/3/license.html) |
| PyYAML 6.0.3 | Optional maintainer YAML import only; pinned in `requirements-maintainer.txt`; not vendored | [MIT; PyPI metadata](https://pypi.org/project/PyYAML/6.0.3/), [upstream license](https://github.com/yaml/pyyaml/blob/6.0.3/LICENSE) |
| `actions/checkout`, `actions/setup-python`, `actions/dependency-review-action` | GitHub-hosted CI tools, pinned by full commit SHA; not vendored | Upstream MIT licenses: [checkout](https://github.com/actions/checkout/blob/main/LICENSE), [setup-python](https://github.com/actions/setup-python/blob/main/LICENSE), [dependency review](https://github.com/actions/dependency-review-action/blob/main/LICENSE) |
| `github/codeql-action` | Optional/public CI analysis, pinned by full commit SHA; not vendored | [Action MIT license](https://github.com/github/codeql-action/blob/main/LICENSE); CodeQL engine has [separate terms](https://codeql.github.com/license-terms/) |
| Gitleaks 8.30.1 | CI secret scan, downloaded at a pinned version and checked against a committed SHA-256; not vendored | [MIT license](https://github.com/gitleaks/gitleaks/blob/v8.30.1/LICENSE) |

Dependabot checks action pins and the optional pip requirement weekly. It does not update the manually pinned Gitleaks binary: review upstream releases and update the version and checksum together, then run the scan. No dependency/security scan grants redistribution rights or proves absence of secrets or proprietary material.

## Data and educational references

Shared live-data reports need visible attribution and must preserve source notices. The renderers include a fixed Skylit link and preserve returned attribution/disclaimer fields as inert text; source URLs cannot inject report markup. Synthetic charts credit the demo and remain labeled fictional.

The [API Terms](https://www.skylit.ai/api-terms) govern API Data separately from code. Attribution alone does not authorize bulk, scheduled, real-time or commercial publication; check the applicable license, exchange/provider restrictions and returned sharing fields before sharing. Keep account responses and saved reports private. No terms are accepted by this repository change.

Academy lesson citations and approved public references are documented in [source-boundary.md](docs/source-boundary.md) and the relevant tutorials. Educational references are not permission to copy private formulas or reconstruct service internals. A human source review is required before release.

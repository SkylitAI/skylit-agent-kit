# Contributing

Fixes, documentation and tested improvements belong in this kit. New experiments belong in [Skylit Agent Lab](https://github.com/SkylitAI/skylit-agent-lab); see [the promotion path](docs/community.md).

1. Open an issue describing the user problem, or pick a small item from the [roadmap](docs/roadmap.md).
2. Create a branch and keep the change focused. Use synthetic fixtures for tests.
3. For behavior changes, add a test that fails first, implement the fix, then run:

   ```sh
   python3 -m unittest discover -s tests -v
   python3 -m compileall -q skylit_agent_kit tests
   ```

4. Include the behavior change, verification and limitations in a pull request. Declare the source of new domain calculations and fixtures under the [source boundary](docs/source-boundary.md). Update compatibility evidence only for hosts you tested.

Do not commit secrets, account responses, private strategies or data you cannot redistribute. New dependencies need a reason, a pinned version and license notes. Tools need bounded requests, explicit permissions/costs, provenance, missing-data behavior and a maintainer. CI runs on synthetic fixtures without live credentials.

Submitting a contribution means you have the right to contribute it under this repository's [MIT license](LICENSE). Third-party software and data retain their own terms; include attribution where required. Be respectful and make feedback specific to the work.

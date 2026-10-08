# Contributing

This is a customer-facing public repository. Contributions must be safe to publish in full, including generated files, CI logs, screenshots, fixtures, commit messages, and pull-request discussion. Read [AGENTS.md](AGENTS.md) before making changes.

Each cookbook recipe must remain complete in Python, Node.js JavaScript, TypeScript, PHP, C#/.NET, Java, and Go.

## Public-information boundary

Use only public Gridics APIs, public documentation, public dependencies, and intentionally public assets.

Do not introduce confidential/internal Gridics material, including non-public repository or issue links, private dependencies or registries, staging/internal infrastructure, deployment/source identifiers, employee-only procedures, customer data, credentials, unpublished implementation details, or internal provider/backend diagnostics.

If a change would require private Gridics access to build, install, test, or understand the example, redesign the example around the public interface instead.

Use synthetic fixtures unless a real public example has been explicitly approved for publication.

## Change workflow

1. Update `recipes/manifest.json` first. Use only documented public V2 routes and canonical public fields.
2. Update the task README and every native entry point. Regenerate mechanical wrappers with `python3 tools/scaffold_cookbook.py`; never hand-edit a generated wrapper without updating the generator.
3. Add or update synthetic fixture behavior.
4. Run `python3 tests/validate_public_distribution.py`, `python3 tests/validate_repository.py`, and `python3 tests/validate_contract.py`.
5. Run fixture/parity tests for every affected runtime.
6. Report fixture and live production verification separately. A mocked or fixture success is not live evidence.

All examples need finite timeouts, page/result/request limits, credential redaction, and actionable public-safe error handling. Preserve APNs and identifiers as strings. Keep missing/unavailable values distinct from zero and false.

## Pull-request requirement

Every PR must confirm that it introduces no confidential Gridics material, requires no private Gridics dependency/access, uses synthetic or explicitly approved fixtures, passes the public-distribution checks, and does not overstate fixture results as live verification.

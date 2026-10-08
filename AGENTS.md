# Public Repository Agent Instructions

This repository is intended for public distribution. Treat every committed byte, generated file, pull-request message, CI log, artifact, screenshot, and test output as information that may be visible on the public internet.

## Source-of-truth boundary

Use only intentionally public Gridics interfaces and materials when changing this repository:

- the production Gridics Public API;
- public Gridics developer documentation and website content;
- public standards and public third-party documentation;
- dependencies that can be installed without Gridics employee credentials.

Do not copy, quote, summarize, link to, depend on, or expose confidential Gridics implementation information from another repository, service, environment, discussion, issue, pull request, package registry, deployment system, or internal tool.

If you can access private Gridics context while working here, that access does not make the information suitable for this repository.

## Never introduce

Do not add:

- links or references to non-public Gridics repositories, issues, pull requests, discussions, or releases;
- private package names, private registries, repository authentication, employee tokens, or employee-only installation steps;
- staging/internal hostnames, VPN instructions, infrastructure topology, environment-specific operational procedures, or employee-only tooling;
- internal branch names, implementation source revisions, deployment SHAs, image digests, unpublished release evidence, or non-public roadmap/status;
- customer data, organization data, employee data, production credentials, API keys, tokens, private keys, or secrets;
- non-public backend field names, query syntax, provider responses, implementation aliases, or diagnostic details;
- real-world fixtures when a synthetic example can demonstrate the behavior safely.

This applies equally to handwritten files, generated files, examples, fixtures, screenshots, tests, commit messages, PR/issue text, CI logs, and uploaded artifacts.

## Implementation rules

1. Prefer standalone public implementations over internal shared dependencies.
2. Never fix a build or test by granting this repository access to a private repository, package, registry, VPN, staging environment, or employee credential.
3. Use synthetic fixtures by default. A real public example must be deliberately approved for publication.
4. Keep secrets server-side and redact credentials from output.
5. Keep mocked/fixture verification distinct from live production verification.
6. Generated content must satisfy the same public-safety rules as source content.
7. If a requested change appears to require confidential information, stop that approach and redesign around the public contract.
8. If you are unsure whether information is public, omit or generalize it and rely on public Gridics documentation/API behavior.

## Before committing

Run:

```bash
python3 tests/validate_public_distribution.py
python3 tests/validate_repository.py
python3 tests/validate_contract.py
```

Also run the relevant fixture/parity suites for every affected language/example. Do not describe an example as live-verified unless a bounded production Public API verification actually succeeded.

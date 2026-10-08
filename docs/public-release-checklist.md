# Public-release checklist

## Repository safeguards

- [x] Customer-facing README organized around zoning, property, development, site-selection, appraisal, and AI use cases.
- [x] API-key acquisition, Organization setup, configuration, first cURL request, and seven-language quickstart.
- [x] Apache-2.0 license, NOTICE, contribution, support, and security-reporting guidance.
- [x] Eighteen documented recipes with 126 native language entry points.
- [x] Credential-free fixture CI for all supported runtimes.
- [x] Root AGENTS.md, contributor confidentiality rules, and PR public-safety checklist.
- [x] Fail-closed public-distribution validator for public links/dependencies, credential patterns, operational metadata, and tracked archives.
- [x] Separate protected, manual, bounded production Public API verification workflow.
- [x] Search-intent technical guides and dedicated MCP integration guide.
- [x] Fixture-first React Zoning Explorer with no browser secret-key path.
- [x] Deterministic clean-history candidate exporter and publication runbook.
- [x] Public bug-report and recipe-request issue templates.

## Repository metadata required before publication

- [ ] Description: "Examples for the Gridics Zoning API: parcel zoning, property search, development capacity, site selection, due diligence, appraisal, MCP and AI integrations."
- [ ] Homepage: https://developer.gridics.com/cookbook
- [ ] Topics include zoning, zoning-api, real-estate, property-data, parcel-data, land-use, geospatial, site-selection, development, proptech, mcp, model-context-protocol, ai-agents, rest-api, and openapi.
- [x] Canonical public repository name selected: gridics/zoning-api-cookbook.
- [ ] Add a social preview image based on docs/assets/zoning-explorer-preview.svg.
- [ ] Consider enabling Discussions for developer Q&A.

## Required before creating the clean public candidate

- [x] Public-distribution/confidentiality validator passes on the approved launch branch.
- [x] Complete seven-language fixture/parity matrix passes from a clean GitHub Actions checkout.
- [ ] All checked-in fixtures/screenshots are synthetic or explicitly approved for publication.
- [ ] Maintainer reviews the current source tree for confidential information and misleading capability claims.
- [ ] Bounded production verification passes for every advertised live-capable workflow available to the test Organization; Location Search remains preview until recipe 18 passes.
- [ ] External-developer onboarding succeeds without Gridics employee-only access.

## External discovery links required before/at launch

- [ ] gridics.com/zoning-data-api links to the official cookbook with descriptive anchor text.
- [ ] developer.gridics.com links to the official cookbook from the API/get-started experience.
- [ ] Hosted MCP documentation links to integrations/mcp.
- [ ] Public cookbook links back to Developer Portal, API documentation, and relevant Gridics product pages.
- [ ] Conflicting wineshmucks/gridics-zoning-cookbook is made private or renamed so it cannot be mistaken for the official cookbook.

## Clean-history candidate command

From the approved launch commit:

```bash
python3 tools/create_public_candidate.py /tmp/zoning-api-cookbook-public
```

This exports committed files only, initializes a new repository with no commits or inherited history, stages the tree, and reruns the core public validators. Follow [the publication runbook](publication-runbook.md) for the final private-candidate and public cutover.

## Required before changing visibility

- [ ] Create the public candidate from the approved working tree only, with fresh Git history.
- [ ] Do not migrate historical Issues, PRs, Actions runs/artifacts, branches, tags, releases, Discussions, environments, secrets, or repository variables unless independently reviewed as public-safe.
- [ ] Confirm the candidate history and repository metadata pass the confidentiality/secret scan.
- [ ] Gridics explicitly authorizes the visibility change.
- [ ] After publication, repeat anonymous clone, links, CI, issue/PR templates, security-contact, and complete-history checks.

Readiness work does not authorize a visibility change.

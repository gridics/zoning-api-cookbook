# Public cookbook publication runbook

The canonical public repository is **gridics/zoning-api-cookbook**. The historical private development repository must not be made public in place.

## 1. Choose the publication status

A preview cookbook may be published before live acceptance is complete when the repository owner explicitly authorizes it. Keep incomplete production and onboarding acceptance visible in the README, retain preview labels, and do not claim production readiness. Public-safety, secret scanning, clean-history export and credential-free candidate CI remain mandatory. Publishing examples does not authorize an API deployment or change its release gates.

Before claiming complete production qualification:

- Public API production Location Search must pass suggest, retrieve, and forward acceptance.
- Recipe 18 must pass the protected production matrix in all seven languages.
- Every other advertised live-capable workflow available to the verification Organization must have current production evidence.
- External onboarding must work without employee-only access.

Fixture success is necessary but is not production acceptance.

## 2. Freeze one approved source commit

Use the exact approved commit from the launch PR. Do not export an uncommitted working tree and do not add cleanup commits after recording the SHA without rerunning qualification.

## 3. Build a clean-history candidate

From the approved source checkout:

~~~bash
python3 tools/create_public_candidate.py /tmp/zoning-api-cookbook-public
cd /tmp/zoning-api-cookbook-public
git status --short
~~~

The exporter:

- requires a clean source checkout;
- validates the source tree;
- exports committed files with git archive;
- initializes a brand-new main branch with **zero inherited commits**;
- stages all public files;
- reruns repository, public-distribution, and OpenAPI-contract validation in the candidate.

Do not copy the source .git directory.

## 4. Run the full candidate matrix

Run the same credential-free checks used by CI, including all language parity suites and both React examples. No employee VPN, private package registry, staging dependency, or employee credential may be necessary.

The candidate must contain only synthetic or deliberately approved public examples.

## 5. Create the new GitHub repository privately

Create **gridics/zoning-api-cookbook** as a new private repository.

Do not import or transfer:

- commits from the historical repository;
- Issues or pull requests;
- Actions runs or artifacts;
- branches, tags, releases, or Discussions;
- environments, Actions secrets, repository variables, or deploy keys.

Commit the staged candidate as the repository's first commit and push only its new main branch.

## 6. Configure public metadata

Description:

> Examples for the Gridics Zoning API: parcel zoning, property search, development capacity, site selection, due diligence, appraisal, MCP and AI integrations.

Homepage:

https://developer.gridics.com/cookbook

Topics:

`zoning`, `zoning-api`, `real-estate`, `real-estate-api`, `property-data`, `parcel-data`, `land-use`, `geospatial`, `gis`, `site-selection`, `development`, `property-api`, `openapi`, `rest-api`, `mcp`, `model-context-protocol`, `ai-agents`, `proptech`.

Use docs/assets/zoning-explorer-preview.svg as the source for the repository social preview. Enable Issues. Enable Discussions only if Gridics wants GitHub to be a public Q&A channel.

## 7. Qualify the private candidate

Before visibility changes:

- Actions are green on the candidate's own first commit.
- README onboarding uses only public dependencies and supported public interfaces. Incomplete end-to-end onboarding acceptance is disclosed for a preview publication.
- Links target only intended public Gridics surfaces.
- The complete candidate history has one intentionally public root commit.
- Secret/confidentiality scanning is clean.

## 8. Publish and activate discovery links together

After explicit publication authorization:

1. change **gridics/zoning-api-cookbook** from private to public;
2. verify anonymous clone and README rendering;
3. merge the prepared Developer Portal cookbook/discovery PR;
4. merge the prepared gridics.com Zoning Data API backlink PR;
5. verify developer.gridics.com/cookbook, gridics.com/zoning-data-api/, and GitHub cross-link correctly;
6. re-run anonymous CI/security/contact checks.

Do not merge public backlinks before the GitHub repository is anonymously reachable.

## 9. Post-launch measurement

Use Google Search Console to monitor the Developer Portal cookbook hub, the Gridics Zoning Data API page, and the GitHub cookbook. Expand guides based on real non-branded impressions and developer behavior rather than adding thin keyword pages.

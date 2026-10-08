
# 17. Appraiser zoning lookup

**Level:** business

## Business outcome

Resolve an appraisal subject by address/APN and report factual zoning with provenance and explicit unknowns.

## API operations

- `POST /v2/parcels/lookup`
- `POST /v2/zoning/query`

## Before you run it

Complete the repository [Getting started](../../README.md#get-an-api-key), copy `.env.example` to `.env`, and replace the synthetic Market, Place, parcel, and address values with IDs returned for your Organization. The examples never discover an ID and then assume that it grants access.

## cURL

### Property

```bash
curl --fail-with-body --request POST \
  --url "${GRIDICS_API_BASE_URL}/v2/parcels/lookup" \
  --header "x-api-key: ${GRIDICS_API_KEY}" \
  --header "Content-Type: application/json" \
  --data "{\"place_id\":\"${GRIDICS_PLACE_ID}\",\"address\":{\"street\":\"${GRIDICS_ADDRESS}\",\"postal_code\":\"${GRIDICS_POSTAL_CODE}\"},\"fields\":[\"parcel.id\",\"parcel.apn\",\"parcel.address\",\"parcel.lot_area\",\"parcel.vacant\",\"zoning.code\"]}" > subject.json
```
### Zoning

```bash
# Requires jq. Derive every zoning identifier from the successful lookup.
jq -e '.data | (.id | type == "string") and (.place_id | type == "string") and (.market_ids | length == 1)' subject.json > /dev/null
jq '.data | {market_id: .market_ids[0], place_id: .place_id, group_id: .id}' subject.json > zoning-request.json
curl --fail-with-body --request POST \
  --url "${GRIDICS_API_BASE_URL}/v2/zoning/query" \
  --header "x-api-key: ${GRIDICS_API_KEY}" \
  --header "Content-Type: application/json" \
  --data @zoning-request.json
```

## Run a port

### Python 3.11+

```bash
cd recipes/17-appraiser-zoning-lookup/python
python3 main.py
```
### Node.js 20+

```bash
cd recipes/17-appraiser-zoning-lookup/nodejs
node main.mjs
```
### TypeScript 5 / Node.js 20+

```bash
cd recipes/17-appraiser-zoning-lookup/typescript
npm --prefix ../../.. install
npm --prefix ../../.. run build
node ../../../dist/recipes/17-appraiser-zoning-lookup/typescript/main.js
```
### PHP 8.2+

```bash
cd recipes/17-appraiser-zoning-lookup/php
php main.php
```
### .NET 8+

```bash
cd recipes/17-appraiser-zoning-lookup/csharp
dotnet run
```
### Java 21+

```bash
cd recipes/17-appraiser-zoning-lookup/java
javac -d build ../../../languages/java/GridicsCookbook.java Main.java && java -cp build Main
```
### Go 1.22+

```bash
cd recipes/17-appraiser-zoning-lookup/go
go run .
```

All ports write the same normalized JSON envelope to stdout. Use `GRIDICS_DRY_RUN=1` to inspect requests without sending them. Use `GRIDICS_FIXTURE_MODE=1` with the test server for deterministic examples.

## Usage and limits

One lookup and one optional zoning operation; no uncertain paid retry.

These are cookbook safety defaults. Your current plan, capabilities, geography, quotas, and pricing are authoritative in the Gridics Developer Portal.

## Important behavior

Use GRIDICS_LOCATOR=address, apn or parcel_id. Resolve canonical IDs before zoning; keep unknowns explicit. Hosted /mcp and appraiser-zoning are documented separately and are not fixture verification.

## Expected result

The command exits `0` only when every required step succeeds. Output includes the recipe ID, API base URL, request count, per-step HTTP status, returned data, and a `fixture` or `live` execution label. Optional capability-gated steps are reported as `unavailable`; they are never filled with invented values.

## Tests

From the repository root, run `python3 tests/validate_repository.py` and the language command documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Normal tests use synthetic fixtures and make no paid requests.

For free-form address/APN search without a required county ID, start with [recipe 18](../18-location-search/README.md).


## Appraiser input and canonical composition

Use the synthetic example `100 Example Ave` when learning the workflow. For a
live request, set `GRIDICS_ADDRESS`, `GRIDICS_POSTAL_CODE` and the entitled
county `GRIDICS_PLACE_ID` using values your Organization is authorized to query.
Direct REST needs a canonical county; use recipe 02 to discover an entitled one.
Discovery does not grant access.

Choose exactly one `GRIDICS_LOCATOR`: `address` (default), `apn`, or
`parcel_id`. Preserve APNs as strings. The runner stops on no match, ambiguity,
unauthorized county, or a lookup without one canonical parcel/Place/Market. It
derives zoning identifiers from the successful lookup rather than trusting
unrelated preconfigured identifiers. Two data operations maximum; each is
attempted once, with no hidden pages or automatic retry of uncertain paid work.

## Output and professional boundary

Every port adds an `appraiser_zoning` workflow with the canonical property,
returned zoning buildings/standards, request/status provenance, retrieval time,
explicit unknowns and a human-readable `markdown` subject summary. Raw returned
facts stay in normalized JSON. Missing description/capacity/uses are not
invented. Null is not zero, false or a negative finding.

The report is a factual Gridics API data summary, not a formal appraisal, title
opinion, legal advice, binding zoning determination or permit assurance. All
checked-in inputs and expected reports are synthetic. Fixture parity covers
address, APN, canonical parcel, no match, ambiguity, wrong county, unavailable
zoning, partial/null standards and quota without billable requests.

Run `python3 tests/run_appraiser_parity.py --language <language>` after the
normal language build to compare the complete report against shared fixtures.
Fixture success is not live production verification.

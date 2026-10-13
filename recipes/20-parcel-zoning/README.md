
# 20. Zoning for a known parcel

**Level:** beginner

## Business outcome

Read the typed zoning resource for a known parcel in its entitled county.

Use this when you already have a canonical parcel ID and its entitled place ID. For an address or APN, start with [recipe 19](../19-address-to-zoning/) instead.

## API operations

- `GET /v2/parcels/{parcel_id}/zoning`

## Before you run it

Complete the repository [Getting started](../../README.md#get-an-api-key), copy `.env.example` to `.env`, and replace the synthetic Market, Place, parcel, and address values with IDs returned for your Organization. The examples never discover an ID and then assume that it grants access.

## cURL

### Zoning

```bash
curl --fail-with-body --request GET \
  --url "${GRIDICS_API_BASE_URL}/v2/parcels/${GRIDICS_PARCEL_ID}/zoning?place_id=${GRIDICS_PLACE_ID}" \
  --header "x-api-key: ${GRIDICS_API_KEY}"
```

## Run a port

### Python 3.11+

```bash
cd recipes/20-parcel-zoning/python
python3 main.py
```
### Node.js 20+

```bash
cd recipes/20-parcel-zoning/nodejs
node main.mjs
```
### TypeScript 5 / Node.js 20+

```bash
cd recipes/20-parcel-zoning/typescript
npm --prefix ../../.. install
npm --prefix ../../.. run build
node ../../../dist/recipes/20-parcel-zoning/typescript/main.js
```
### PHP 8.2+

```bash
cd recipes/20-parcel-zoning/php
php main.php
```
### .NET 8+

```bash
cd recipes/20-parcel-zoning/csharp
dotnet run
```
### Java 21+

```bash
cd recipes/20-parcel-zoning/java
javac -d build ../../../languages/java/GridicsCookbook.java Main.java && java -cp build Main
```
### Go 1.22+

```bash
cd recipes/20-parcel-zoning/go
go run .
```

All ports write the same normalized JSON envelope to stdout. Use `GRIDICS_DRY_RUN=1` to inspect requests without sending them. Use `GRIDICS_FIXTURE_MODE=1` with the test server for deterministic examples.

## Usage and limits

One parcel zoning request; account capability, geographic entitlement, and quota apply.

These are cookbook safety defaults. Your current plan, capabilities, geography, quotas, and pricing are authoritative in the Gridics Developer Portal.

## Important behavior

Use the parcel ID and place ID returned by a successful authorized lookup. Preserve multiple buildings and districts, source provenance, use permissions, units, and unavailable states. Missing values are not negative zoning findings.

## Expected result

The command exits `0` only when every required step succeeds. Output includes the recipe ID, API base URL, request count, per-step HTTP status, returned data, and a `fixture` or `live` execution label. Optional capability-gated steps are reported as `unavailable`; they are never filled with invented values.

## Tests

From the repository root, run `python3 tests/validate_repository.py` and the language command documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Normal tests use synthetic fixtures and make no paid requests.


# 11. Screen redevelopment candidates

**Level:** business / capability-gated

## Business outcome

Check whether capacity fields are released before screening for potential underbuilt parcels.

## API operations

- `GET /v2/parcels/search-fields`
- `POST /v2/parcels/search`

## Before you run it

Complete the repository [Getting started](../../README.md#get-an-api-key), copy `.env.example` to `.env`, and replace the synthetic Market, Place, parcel, and address values with IDs returned for your Organization. The examples never discover an ID and then assume that it grants access.

## cURL

### Fields Gate

```bash
curl --fail-with-body --request GET \
  --url "${GRIDICS_API_BASE_URL}/v2/parcels/search-fields" \
  --header "x-api-key: ${GRIDICS_API_KEY}"
```
### Candidates

```bash
curl --fail-with-body --request POST \
  --url "${GRIDICS_API_BASE_URL}/v2/parcels/search" \
  --header "x-api-key: ${GRIDICS_API_KEY}" \
  --header "Content-Type: application/json" \
  --data "{\"scope\":{\"place_ids\":[\"${GRIDICS_PLACE_ID}\"]},\"filters\":{\"all\":[{\"field\":\"parcel.vacant\",\"operator\":\"eq\",\"value\":true}]},\"fields\":[\"parcel.id\",\"parcel.address\",\"parcel.lot_area\",\"zoning.code\",\"development.max_buildable_area\"],\"sort\":[],\"include_total\":false,\"page_size\":10}"
```

## Run a port

### Python 3.11+

```bash
cd recipes/11-redevelopment-screen/python
python3 main.py
```
### Node.js 20+

```bash
cd recipes/11-redevelopment-screen/nodejs
node main.mjs
```
### TypeScript 5 / Node.js 20+

```bash
cd recipes/11-redevelopment-screen/typescript
npm --prefix ../../.. install
npm --prefix ../../.. run build
node ../../../dist/recipes/11-redevelopment-screen/typescript/main.js
```
### PHP 8.2+

```bash
cd recipes/11-redevelopment-screen/php
php main.php
```
### .NET 8+

```bash
cd recipes/11-redevelopment-screen/csharp
dotnet run
```
### Java 21+

```bash
cd recipes/11-redevelopment-screen/java
javac -d build ../../../languages/java/GridicsCookbook.java Main.java && java -cp build Main
```
### Go 1.22+

```bash
cd recipes/11-redevelopment-screen/go
go run .
```

All ports write the same normalized JSON envelope to stdout. Use `GRIDICS_DRY_RUN=1` to inspect requests without sending them. Use `GRIDICS_FIXTURE_MODE=1` with the test server for deterministic examples.

## Usage and limits

No live capacity claim is made when fields remain unavailable or capability-gated.

These are cookbook safety defaults. Your current plan, capabilities, geography, quotas, and pricing are authoritative in the Gridics Developer Portal.

## Important behavior

This recipe deliberately fails closed when `development.max_buildable_area` is not returned as enabled by field discovery. Schema presence alone does not establish market availability. A blocked result is the correct outcome until the API advertises the required capability.

## Expected result

The command exits `0` only when every required step succeeds. Output includes the recipe ID, API base URL, request count, per-step HTTP status, returned data, and a `fixture` or `live` execution label. Optional capability-gated steps are reported as `unavailable`; they are never filled with invented values.

## Tests

From the repository root, run `python3 tests/validate_repository.py` and the language command documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Normal tests use synthetic fixtures and make no paid requests.

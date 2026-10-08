
# 05. Search a county with simple filters

**Level:** beginner

## Business outcome

Find a small list of vacant parcels; add other constraints only when field discovery confirms filter availability.

## API operations

- `POST /v2/parcels/simple-search`

## Before you run it

Complete the repository [Getting started](../../README.md#get-an-api-key), copy `.env.example` to `.env`, and replace the synthetic Market, Place, parcel, and address values with IDs returned for your Organization. The examples never discover an ID and then assume that it grants access.

## cURL

### Candidates

```bash
curl --fail-with-body --request POST \
  --url "${GRIDICS_API_BASE_URL}/v2/parcels/simple-search" \
  --header "x-api-key: ${GRIDICS_API_KEY}" \
  --header "Content-Type: application/json" \
  --data "{\"place_ids\":[\"${GRIDICS_PLACE_ID}\"],\"filters\":{\"vacant\":true},\"page_size\":10,\"fields\":[\"parcel.id\",\"parcel.apn\",\"parcel.address\",\"parcel.lot_area\",\"parcel.vacant\",\"zoning.code\"]}"
```

## Run a port

### Python 3.11+

```bash
cd recipes/05-simple-search/python
python3 main.py
```
### Node.js 20+

```bash
cd recipes/05-simple-search/nodejs
node main.mjs
```
### TypeScript 5 / Node.js 20+

```bash
cd recipes/05-simple-search/typescript
npm --prefix ../../.. install
npm --prefix ../../.. run build
node ../../../dist/recipes/05-simple-search/typescript/main.js
```
### PHP 8.2+

```bash
cd recipes/05-simple-search/php
php main.php
```
### .NET 8+

```bash
cd recipes/05-simple-search/csharp
dotnet run
```
### Java 21+

```bash
cd recipes/05-simple-search/java
javac -d build ../../../languages/java/GridicsCookbook.java Main.java && java -cp build Main
```
### Go 1.22+

```bash
cd recipes/05-simple-search/go
go run .
```

All ports write the same normalized JSON envelope to stdout. Use `GRIDICS_DRY_RUN=1` to inspect requests without sending them. Use `GRIDICS_FIXTURE_MODE=1` with the test server for deterministic examples.

## Usage and limits

One standard request plus returned parcel rows; defaults to 10 rows.

These are cookbook safety defaults. Your current plan, capabilities, geography, quotas, and pricing are authoritative in the Gridics Developer Portal.

## Important behavior

The same manifest drives every language port, so route, method, request body, bounds, and normalized output stay aligned.

## Expected result

The command exits `0` only when every required step succeeds. Output includes the recipe ID, API base URL, request count, per-step HTTP status, returned data, and a `fixture` or `live` execution label. Optional capability-gated steps are reported as `unavailable`; they are never filled with invented values.

## Tests

From the repository root, run `python3 tests/validate_repository.py` and the language command documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Normal tests use synthetic fixtures and make no paid requests.

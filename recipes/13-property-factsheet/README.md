
# 13. Generate a brokerage property factsheet

**Level:** business

## Business outcome

Collect public parcel and zoning facts with request provenance for a printable report.

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
  --data "{\"place_id\":\"${GRIDICS_PLACE_ID}\",\"address\":{\"street\":\"${GRIDICS_ADDRESS}\",\"postal_code\":\"${GRIDICS_POSTAL_CODE}\"},\"fields\":[\"parcel.id\",\"parcel.apn\",\"parcel.address\",\"parcel.lot_area\",\"parcel.vacant\",\"zoning.code\"]}"
```
### Zoning

```bash
curl --fail-with-body --request POST \
  --url "${GRIDICS_API_BASE_URL}/v2/zoning/query" \
  --header "x-api-key: ${GRIDICS_API_KEY}" \
  --header "Content-Type: application/json" \
  --data "{\"market_id\":\"${GRIDICS_MARKET_ID}\",\"place_id\":\"${GRIDICS_PLACE_ID}\",\"group_id\":\"${GRIDICS_PARCEL_ID}\"}"
```

## Run a port

### Python 3.11+

```bash
cd recipes/13-property-factsheet/python
python3 main.py
```
### Node.js 20+

```bash
cd recipes/13-property-factsheet/nodejs
node main.mjs
```
### TypeScript 5 / Node.js 20+

```bash
cd recipes/13-property-factsheet/typescript
npm --prefix ../../.. install
npm --prefix ../../.. run build
node ../../../dist/recipes/13-property-factsheet/typescript/main.js
```
### PHP 8.2+

```bash
cd recipes/13-property-factsheet/php
php main.php
```
### .NET 8+

```bash
cd recipes/13-property-factsheet/csharp
dotnet run
```
### Java 21+

```bash
cd recipes/13-property-factsheet/java
javac -d build ../../../languages/java/GridicsCookbook.java Main.java && java -cp build Main
```
### Go 1.22+

```bash
cd recipes/13-property-factsheet/go
go run .
```

All ports write the same normalized JSON envelope to stdout. Use `GRIDICS_DRY_RUN=1` to inspect requests without sending them. Use `GRIDICS_FIXTURE_MODE=1` with the test server for deterministic examples.

## Usage and limits

One lookup and one optional zoning request.

These are cookbook safety defaults. Your current plan, capabilities, geography, quotas, and pricing are authoritative in the Gridics Developer Portal.

## Important behavior

Render only returned facts. Unknown values stay unknown. Escape text before inserting it in HTML, keep the key on a server, and separate customer notes from API facts.

## Expected result

The command exits `0` only when every required step succeeds. Output includes the recipe ID, API base URL, request count, per-step HTTP status, returned data, and a `fixture` or `live` execution label. Optional capability-gated steps are reported as `unavailable`; they are never filled with invented values.

## Tests

From the repository root, run `python3 tests/validate_repository.py` and the language command documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Normal tests use synthetic fixtures and make no paid requests.


# 02. Discover coverage and entitled counties

**Level:** beginner

## Business outcome

List coverage separately from the counties the current key may query.

## API operations

- `GET /v2/market-catalog`
- `GET /v2/markets`
- `GET /v2/markets/{market_id}/places`

## Before you run it

Complete the repository [Getting started](../../README.md#get-an-api-key), copy `.env.example` to `.env`, and replace the synthetic Market, Place, parcel, and address values with IDs returned for your Organization. The examples never discover an ID and then assume that it grants access.

## cURL

### Coverage

```bash
curl --fail-with-body --request GET \
  --url "${GRIDICS_API_BASE_URL}/v2/market-catalog?page_size=25" \
  --header "x-api-key: ${GRIDICS_API_KEY}"
```
### Markets

```bash
curl --fail-with-body --request GET \
  --url "${GRIDICS_API_BASE_URL}/v2/markets?page_size=25" \
  --header "x-api-key: ${GRIDICS_API_KEY}"
```
### Counties

```bash
curl --fail-with-body --request GET \
  --url "${GRIDICS_API_BASE_URL}/v2/markets/${GRIDICS_MARKET_ID}/places?page_size=25" \
  --header "x-api-key: ${GRIDICS_API_KEY}"
```

## Run a port

### Python 3.11+

```bash
cd recipes/02-discover-counties/python
python3 main.py
```
### Node.js 20+

```bash
cd recipes/02-discover-counties/nodejs
node main.mjs
```
### TypeScript 5 / Node.js 20+

```bash
cd recipes/02-discover-counties/typescript
npm --prefix ../../.. install
npm --prefix ../../.. run build
node ../../../dist/recipes/02-discover-counties/typescript/main.js
```
### PHP 8.2+

```bash
cd recipes/02-discover-counties/php
php main.php
```
### .NET 8+

```bash
cd recipes/02-discover-counties/csharp
dotnet run
```
### Java 21+

```bash
cd recipes/02-discover-counties/java
javac -d build ../../../languages/java/GridicsCookbook.java Main.java && java -cp build Main
```
### Go 1.22+

```bash
cd recipes/02-discover-counties/go
go run .
```

All ports write the same normalized JSON envelope to stdout. Use `GRIDICS_DRY_RUN=1` to inspect requests without sending them. Use `GRIDICS_FIXTURE_MODE=1` with the test server for deterministic examples.

## Usage and limits

At most three discovery requests per run.

These are cookbook safety defaults. Your current plan, capabilities, geography, quotas, and pricing are authoritative in the Gridics Developer Portal.

## Important behavior

The same manifest drives every language port, so route, method, request body, bounds, and normalized output stay aligned.

## Expected result

The command exits `0` only when every required step succeeds. Output includes the recipe ID, API base URL, request count, per-step HTTP status, returned data, and a `fixture` or `live` execution label. Optional capability-gated steps are reported as `unavailable`; they are never filled with invented values.

## Tests

From the repository root, run `python3 tests/validate_repository.py` and the language command documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Normal tests use synthetic fixtures and make no paid requests.

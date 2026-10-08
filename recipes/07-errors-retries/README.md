
# 07. Handle errors, throttling, and retries

**Level:** intermediate

## Business outcome

Classify authentication, entitlement, validation, throttling, and transient service errors.

## API operations

- `GET /v2/me`

## Before you run it

Complete the repository [Getting started](../../README.md#get-an-api-key), copy `.env.example` to `.env`, and replace the synthetic Market, Place, parcel, and address values with IDs returned for your Organization. The examples never discover an ID and then assume that it grants access.

## cURL

### Retry Demo

```bash
curl --fail-with-body --request GET \
  --url "${GRIDICS_API_BASE_URL}/v2/me" \
  --header "x-api-key: ${GRIDICS_API_KEY}"
```

## Run a port

### Python 3.11+

```bash
cd recipes/07-errors-retries/python
python3 main.py
```
### Node.js 20+

```bash
cd recipes/07-errors-retries/nodejs
node main.mjs
```
### TypeScript 5 / Node.js 20+

```bash
cd recipes/07-errors-retries/typescript
npm --prefix ../../.. install
npm --prefix ../../.. run build
node ../../../dist/recipes/07-errors-retries/typescript/main.js
```
### PHP 8.2+

```bash
cd recipes/07-errors-retries/php
php main.php
```
### .NET 8+

```bash
cd recipes/07-errors-retries/csharp
dotnet run
```
### Java 21+

```bash
cd recipes/07-errors-retries/java
javac -d build ../../../languages/java/GridicsCookbook.java Main.java && java -cp build Main
```
### Go 1.22+

```bash
cd recipes/07-errors-retries/go
go run .
```

All ports write the same normalized JSON envelope to stdout. Use `GRIDICS_DRY_RUN=1` to inspect requests without sending them. Use `GRIDICS_FIXTURE_MODE=1` with the test server for deterministic examples.

## Usage and limits

At most three attempts and 30 seconds; only 429, 502, and 503 are retryable.

These are cookbook safety defaults. Your current plan, capabilities, geography, quotas, and pricing are authoritative in the Gridics Developer Portal.

## Important behavior

The runners retry only `429`, `502`, and `503`, honor `Retry-After`, add bounded exponential delay, and never retry authentication, authorization, validation, not-found, or ambiguity responses.

## Expected result

The command exits `0` only when every required step succeeds. Output includes the recipe ID, API base URL, request count, per-step HTTP status, returned data, and a `fixture` or `live` execution label. Optional capability-gated steps are reported as `unavailable`; they are never filled with invented values.

## Tests

From the repository root, run `python3 tests/validate_repository.py` and the language command documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Normal tests use synthetic fixtures and make no paid requests.

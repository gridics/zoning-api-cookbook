
# 18. Location Search API

**Level:** beginner

## Business outcome

Resolve free-form address/APN with suggest/retrieve or forward without a required county ID.

## API operations

- `GET /v2/locations/suggest`
- `GET /v2/locations/retrieve/{gridics_id}`
- `GET /v2/locations/forward`

## Before you run it

Complete the repository [Getting started](../../README.md#get-an-api-key), copy `.env.example` to `.env`, and configure a free-form address/APN query; no Place or Market ID is required. The examples never discover an ID and then assume that it grants access.

## cURL

```bash
# Generate a UUIDv4 once for this interaction.
SESSION_TOKEN=$(python3 -c "import uuid; print(uuid.uuid4())")
curl --fail-with-body --get "${GRIDICS_API_BASE_URL}/v2/locations/suggest" --header "x-api-key: ${GRIDICS_API_KEY}" --data-urlencode "q=100 Example Ave" --data-urlencode "session_token=${SESSION_TOKEN}" > suggestions.json
# Inspect suggestions before selecting one; requires jq.
GRIDICS_ID=$(jq -er ".suggestions[0].gridics_id" suggestions.json)
curl --fail-with-body --get "${GRIDICS_API_BASE_URL}/v2/locations/retrieve/${GRIDICS_ID}" --header "x-api-key: ${GRIDICS_API_KEY}" --data-urlencode "session_token=${SESSION_TOKEN}"
# Separate one-off lookup (one commercial unit):
curl --fail-with-body --get "${GRIDICS_API_BASE_URL}/v2/locations/forward" --header "x-api-key: ${GRIDICS_API_KEY}" --data-urlencode "q=100 Example Ave"
```

## Run a port

### Python 3.11+

```bash
cd recipes/18-location-search/python
python3 main.py
```
### Node.js 20+

```bash
cd recipes/18-location-search/nodejs
node main.mjs
```
### TypeScript 5 / Node.js 20+

```bash
cd recipes/18-location-search/typescript
npm --prefix ../../.. install
npm --prefix ../../.. run build
node ../../../dist/recipes/18-location-search/typescript/main.js
```
### PHP 8.2+

```bash
cd recipes/18-location-search/php
php main.php
```
### .NET 8+

```bash
cd recipes/18-location-search/csharp
dotnet run
```
### Java 21+

```bash
cd recipes/18-location-search/java
javac -d build ../../../languages/java/GridicsCookbook.java Main.java && java -cp build Main
```
### Go 1.22+

```bash
cd recipes/18-location-search/go
go run .
```

All ports write the same normalized JSON envelope to stdout. Use `GRIDICS_DRY_RUN=1` to inspect requests without sending them. Use `GRIDICS_FIXTURE_MODE=1` with the test server for deterministic examples.

## Usage and limits

One commercial unit per interactive session or forward request; HTTP rate limits count each request.

These are cookbook safety defaults. Your current plan, capabilities, geography, quotas, and pricing are authoritative in the Gridics Developer Portal.

## Important behavior

The same manifest drives every language port, so route, method, request body, bounds, and normalized output stay aligned.

## Expected result

The command exits `0` only when every required step succeeds. Output includes the recipe ID, API base URL, request count, per-step HTTP status, returned data, and a `fixture` or `live` execution label. Optional capability-gated steps are reported as `unavailable`; they are never filled with invented values.

## Tests

From the repository root, run `python3 tests/validate_repository.py` and the language command documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Normal tests use synthetic fixtures and make no paid requests.

## Location Search configuration

These seven ports run on a server using `x-api-key: ${GRIDICS_API_KEY}` with a secret `gk_...` key. Never embed that key in browser JavaScript. Use scoped observable `gpk_...` publishable tokens for the [plain browser](../../examples/browser-location-autocomplete/) or [React example](../../examples/react-location-search/).

Set `GRIDICS_LOCATION_QUERY` to an address or APN (keep leading zeros). `GRIDICS_LOCATION_MODE=suggest_retrieve` runs two bounded suggest calls and retrieves the first returned opaque `gridics_id`; `forward` runs one complete one-off query. Set `GRIDICS_LOCATION_LIMIT` (1–10), `GRIDICS_LOCATION_COUNTRY`, `GRIDICS_LOCATION_LANGUAGE`, `GRIDICS_LOCATION_PROXIMITY=longitude,latitude`, or `GRIDICS_LOCATION_BBOX=minLon,minLat,maxLon,maxLat`. Hints narrow/rank results within your entitled geography. They never grant access. No `place_id` is required.

Each interactive execution generates a fresh UUIDv4. Both suggests and the selected retrieve use the same UUID. A new independent interaction requires a new token; retrieve closes the previous session. The session token is correlation, never authentication. Empty suggestions skip retrieve. One session uses one `location_searches` commercial unit; forward uses one unit per successful request. Each HTTP request still counts toward rate limits. The recipe sends each request once and never automatically retries an uncertain paid operation.

The `workflow` envelope preserves public suggestions (`name`, `full_address`, `place_formatted`, `matched_by`, `feature_type`, `context`) and GeoJSON `features` with canonical `parcel_id`, string APN, address, point coordinates, and county/region context. `state` distinguishes `resolved`, `ambiguous`, `no_match`, and `error`; multiple forward features preserve ambiguity for caller review. Request IDs/status are in `provenance`.

HTTP 422 means malformed input; 400/409 can mean invalid/expired/mismatched session or stale selection; 403 can indicate capability/coverage denial; 429 covers quota or rate controls; 502/503 indicate temporary service failure. Inspect the public response code and correlation ID; start a new interaction when its session expires. Never log keys or expose provider details.

Run `python3 tests/run_location_parity.py --language python` (or nodejs, typescript, php, csharp, java, go) for deterministic address/APN/forward/filter/empty/session/quota/error parity. This is fixture evidence, not hosted or billable acceptance. Check the [compatibility notes](../../docs/compatibility.md) and [public contract](../../contracts/openapi-v2.json) before enabling live calls.

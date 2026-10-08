
# 16. Expose bounded MCP tools

**Level:** advanced

## Business outcome

Run a read-only MCP-compatible JSON-RPC server with typed, allow-listed Gridics tools.

## API operations

- `GET /v2/me`
- `GET /v2/markets`
- `POST /v2/parcels/lookup`
- `POST /v2/parcels/simple-search`
- `POST /v2/zoning/query`

## Before you run it

Complete the repository [Getting started](../../README.md#get-an-api-key), copy `.env.example` to `.env`, and replace the synthetic Market, Place, parcel, and address values with IDs returned for your Organization. The examples never discover an ID and then assume that it grants access.

## cURL

### Credential

```bash
curl --fail-with-body --request GET \
  --url "${GRIDICS_API_BASE_URL}/v2/me" \
  --header "x-api-key: ${GRIDICS_API_KEY}"
```

## Run a port

### Python 3.11+

```bash
cd recipes/16-mcp-tools/python
python3 main.py
```
### Node.js 20+

```bash
cd recipes/16-mcp-tools/nodejs
node main.mjs
```
### TypeScript 5 / Node.js 20+

```bash
cd recipes/16-mcp-tools/typescript
npm --prefix ../../.. install
npm --prefix ../../.. run build
node ../../../dist/recipes/16-mcp-tools/typescript/main.js
```
### PHP 8.2+

```bash
cd recipes/16-mcp-tools/php
php main.php
```
### .NET 8+

```bash
cd recipes/16-mcp-tools/csharp
dotnet run
```
### Java 21+

```bash
cd recipes/16-mcp-tools/java
javac -d build ../../../languages/java/GridicsCookbook.java Main.java && java -cp build Main
```
### Go 1.22+

```bash
cd recipes/16-mcp-tools/go
go run .
```

All ports write the same normalized JSON envelope to stdout. Use `GRIDICS_DRY_RUN=1` to inspect requests without sending them. Use `GRIDICS_FIXTURE_MODE=1` with the test server for deterministic examples.

## Usage and limits

Five Gridics calls per workflow, 10 search results, and two zoning enrichments by default.

These are cookbook safety defaults. Your current plan, capabilities, geography, quotas, and pricing are authoritative in the Gridics Developer Portal.

## Important behavior

Start the JSON-RPC server with the language runner's `--mcp` option. It supports MCP initialization, `tools/list`, and typed `tools/call` for allow-listed read-only operations. The API key stays in the server environment and never appears in tool schemas or results. This is an educational local adapter; use public Gridics documentation for any hosted integration. Never paste an API key into an LLM or hosted connection.

## Expected result

The command exits `0` only when every required step succeeds. Output includes the recipe ID, API base URL, request count, per-step HTTP status, returned data, and a `fixture` or `live` execution label. Optional capability-gated steps are reported as `unavailable`; they are never filled with invented values.

## Tests

From the repository root, run `python3 tests/validate_repository.py` and the language command documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Normal tests use synthetic fixtures and make no paid requests.

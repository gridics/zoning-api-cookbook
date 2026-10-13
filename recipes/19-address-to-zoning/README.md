
# 19. Address to zoning

**Level:** beginner

## Business outcome

Resolve an address or APN and retrieve available zoning in one request, without discovering a county ID.

This is the shortest server-side zoning workflow. For an interactive address/APN field, use [Location Search](../18-location-search/) suggest → retrieve to let the user choose. Use Location Search forward when you need resolution without zoning. The older multi-step zoning query remains in [recipe 04](../04-zoning-query/).

## API operations

- `POST /v2/zoning/lookup`

## Before you run it

Complete the repository [Getting started](../../README.md#get-an-api-key), copy `.env.example` to `.env`, and configure a free-form address/APN query; no Place or Market ID is required. The examples never discover an ID and then assume that it grants access.

## cURL

### Zoning

```bash
curl --fail-with-body --request POST \
  --url "${GRIDICS_API_BASE_URL}/v2/zoning/lookup" \
  --header "x-api-key: ${GRIDICS_API_KEY}" \
  --header "Content-Type: application/json" \
  --data "{\"address\":\"${GRIDICS_ADDRESS}\"}"
```

## Run a port

### Python 3.11+

```bash
cd recipes/19-address-to-zoning/python
python3 main.py
```
### Node.js 20+

```bash
cd recipes/19-address-to-zoning/nodejs
node main.mjs
```
### TypeScript 5 / Node.js 20+

```bash
cd recipes/19-address-to-zoning/typescript
npm --prefix ../../.. install
npm --prefix ../../.. run build
node ../../../dist/recipes/19-address-to-zoning/typescript/main.js
```
### PHP 8.2+

```bash
cd recipes/19-address-to-zoning/php
php main.php
```
### .NET 8+

```bash
cd recipes/19-address-to-zoning/csharp
dotnet run
```
### Java 21+

```bash
cd recipes/19-address-to-zoning/java
javac -d build ../../../languages/java/GridicsCookbook.java Main.java && java -cp build Main
```
### Go 1.22+

```bash
cd recipes/19-address-to-zoning/go
go run .
```

All ports write the same normalized JSON envelope to stdout. Use `GRIDICS_DRY_RUN=1` to inspect requests without sending them. Use `GRIDICS_FIXTURE_MODE=1` with the test server for deterministic examples.

## Usage and limits

One zoning lookup request; account capability, geographic entitlement, and quota apply.

These are cookbook safety defaults. Your current plan, capabilities, geography, quotas, and pricing are authoritative in the Gridics Developer Portal.

## Important behavior

Supply exactly one locator: address, APN, or coordinates. An ambiguous match returns 409; ask the user to choose a property instead of selecting one silently. A denied county or missing capability must remain an error. Preserve every returned building, district, use permission, source, unit, and unavailable value.

## Expected result

The command exits `0` only when every required step succeeds. Output includes the recipe ID, API base URL, request count, per-step HTTP status, returned data, and a `fixture` or `live` execution label. Optional capability-gated steps are reported as `unavailable`; they are never filled with invented values.

## Tests

From the repository root, run `python3 tests/validate_repository.py` and the language command documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Normal tests use synthetic fixtures and make no paid requests.

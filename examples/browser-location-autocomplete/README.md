# Gridics browser autocomplete

Run `python3 -m http.server 8080` from this directory and open `http://localhost:8080`. The default fixture mode uses synthetic address/APN results and never calls an API. Type `empty` for no matches. Tests run with `node --test tests/location_browser.test.mjs` from the repository root.

For live testing, create a scoped test publishable token through the [Developer Portal](https://developer.gridics.com), when token management is enabled for your account, grant Location Search only, and allow the exact development origin `http://localhost:8080`. Copy `config.example.mjs` to the ignored `config.mjs`, set `fixture: false`, the owning API base URL, and your `gpk_test_...` token. Do not enable live mode before backend staging and token/origin acceptance are complete. Production enablement is a separate release decision.

Publishable `gpk_...` tokens are intended for browser use and are observable. Never put a secret `gk_...` API key or Gridics backend token in client code. The request inspector shows endpoint/method/status and an abbreviated session correlation ID; it omits authentication and opaque selection IDs.

Type an address or APN (three characters minimum), use arrows to navigate and Enter to select, Escape to dismiss, or the clear button to start over. Rows show street, place/county, and APN match indicators. Selection retrieves canonical property details. The demo uses a 275 ms debounce, AbortController, stale-response checks, and accessible combobox/listbox semantics. The query does not require a county ID.

One UUIDv4 groups successive suggest requests and the selected retrieve. Retrieve, clear, or a session error starts a fresh interaction. Each session consumes one `location_searches` unit; each HTTP request still counts for rate limiting. A successful forward request is one unit and belongs in [server recipe 18](../../recipes/18-location-search/). This browser demo never automatically retries an uncertain paid request.

Use `errorStatus: 401`, `403`, `409`, `422`, `429`, `502`, or `503` in fixture config for safe error demonstrations. No raw provider error is shown. `client.mjs` is the public adapter and interaction controller; `app.mjs` contains the framework-neutral DOM wiring. The [React example](../react-location-search/) uses the same public adapter and interaction controller with ordinary React.

# React Location Search

A standalone React autocomplete built from this cookbook's public HTTP adapter and interaction controller. All dependencies come from public npm. No Gridics component package, private registry account or GitHub package token is required.

## Run without an API key

Use Node.js 22.12+ or 24. From this directory run:

```bash
npm ci
npm run dev
```

Open the displayed localhost URL. Fixture mode is the default and makes no API calls. Type an address or APN; type `empty` for no matches. Select a result to see canonical property details, or clear to start a new interaction. Use arrow keys, Enter and Escape to navigate.

Run `npm test` and `npm run build` for local verification.

## Use your authorized API access

Confirm that Location Search and publishable-token management are enabled for your environment and account in the [Developer Portal](https://developer.gridics.com). Create a scoped `gpk_test_...` or `gpk_live_...` token and allow the exact example origin, such as `http://localhost:5173` for a test token. Copy `.env.example` to the ignored `.env.local`, set `VITE_FIXTURE=false`, your API base URL and publishable token, then restart the development server.

Publishable tokens are observable in browser code. Never use a secret `gk_...` API key, service credential or backend token in client code. The build rejects secret credential classes before producing assets. Origin restrictions do not replace scope, geography, rate and quota controls. Do not enable production calls from fixture results alone.

## How it works

`LocationSearchTextbox.jsx` is ordinary React composition over `SearchInteraction` from the plain-browser example. The controller handles 275 ms debounce, cancellation, stale-response protection, keyboard navigation and UUID search sessions. `App.jsx` displays the returned property; styling is local example CSS.

The same session groups suggest requests and the selected retrieve. Completion, clear or session failure starts a new interaction. One interactive search consumes one `location_searches` unit; individual requests remain rate-limited. A successful forward request consumes one unit and is demonstrated separately in [recipe 18](../../recipes/18-location-search/). Uncertain paid requests are never automatically retried.

Set `VITE_FIXTURE_ERROR_STATUS=429` or `503` for safe quota/service demonstrations. See the [plain browser example](../browser-location-autocomplete/), [configuration guide](../../docs/location-search.md) and [compatibility notes](../../docs/compatibility.md).

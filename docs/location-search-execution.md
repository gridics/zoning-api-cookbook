# Location Search verification

| Surface | Public implementation | Fixture verification | Live acceptance |
| --- | --- | --- | --- |
| Cookbook 18 | Seven language ports; suggest/retrieve session, separate forward; no required county ID | Thirteen synthetic cases in every runtime, repository and contract checks | Required before declaring live availability |
| Plain browser | HTML/CSS/JavaScript; public HTTP adapter and interaction controller | Desktop/mobile, keyboard, resolution, clear, APN, empty/error states | Requires a scoped publishable token and authorized origin |
| React | Ordinary React with the same public adapter/controller; public npm dependencies | Build, integration/security tests and desktop/mobile fixtures | Requires the same enabled API contract and browser-token proof |

Normal CI runs without an API key or private package credentials. Public dependencies are installed from npm. No proprietary component source, package archives or generated application bundles are distributed here.

The [contract snapshot](../contracts/openapi-v2.json) and synthetic screenshots describe example behavior. They do not prove hosted or production acceptance.

Rendered plain-browser fixtures: [desktop](verification/location-search/browser-desktop-fixture.png) and [mobile](verification/location-search/browser-mobile-fixture.png). React fixtures: [desktop](verification/location-search/react-desktop-fixture.png) and [mobile](verification/location-search/react-mobile-fixture.png).

Live release verification must use the production Public API with a dedicated safe test account and bounded request budget, retain only public-safe status metadata, and clean up or rotate test credentials as appropriate. A successful source build or fixture run is insufficient.

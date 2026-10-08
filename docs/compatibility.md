# API compatibility and verification

The checked-in [V2 snapshot](../contracts/openapi-v2.json) documents the public contract reviewed for this cookbook. It is a contract reference, not proof that a specific account has every capability enabled. Its server entry is `https://api.gridics.com`; server recipes use `x-api-key`, and browser examples use a scoped publishable key.

Routes and fields can vary by released capability, geography entitlement, and account plan. Runners preserve capability failures rather than replacing them with fixture output.

Normal CI verifies requests against synthetic responses. Fixture success proves request/response behavior inside the cookbook; it does not prove live production availability.

`.github/workflows/live-verification.yml` is a manual, bounded production verification workflow. It uses a protected production-verification environment with a dedicated safe test Organization and scoped credentials. Live evidence records only public-safe metadata such as cookbook revision, date, selected recipe/language, request count, and HTTP status categories. Response bodies, customer data, credentials, deployment identifiers, and internal environment details are not retained.

Every selected recipe is bounded to a finite request budget. An unavailable capability remains explicit and is not reported as verified. Live verification should be rerun whenever public API behavior or cookbook request shapes materially change.

V1 is outside this cookbook. Adding V1 examples requires a separate versioned directory and compatibility policy.

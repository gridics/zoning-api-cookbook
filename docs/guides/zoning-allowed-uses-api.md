# Zoning rules and allowed uses

Resolve the canonical parcel first with [Location Search](../../recipes/18-location-search/) or [exact parcel lookup](../../recipes/03-property-lookup/). The current [zoning query](../../recipes/04-zoning-query/) returns the parcel's available zoning response. For detailed use permissions, the public contract also defines `GET /v2/parcels/{parcel_id}/uses` with the parcel's entitled `place_id` and cursor pagination.

Preserve each returned building and district. Keep the returned `permission` for each use; a use absent from the response is not automatically prohibited. Keep ordinance links only when returned by the API, and label missing or unavailable values as unknown. Do not infer permitting or legal conclusions from a missing field.

Check [field discovery](../../recipes/08-advanced-search/) and your active plan before using capability-gated data. The checked-in [OpenAPI V2 contract](../../contracts/openapi-v2.json) describes the shape; fixture results are not live production verification.

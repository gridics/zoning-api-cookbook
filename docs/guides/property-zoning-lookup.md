# Property zoning lookup by address, APN, or parcel

The published V2 contract supports a one-request address/APN-to-zoning lookup. This guide describes the available API; fixture checks do not establish production access for your account.

## Start with zoning by address or APN

Call `POST /v2/zoning/lookup` with one locator, for example `{"address":"100 Example Ave, Example City, FL 00000"}`. No county ID is needed for the usual case. A 409 ambiguity requires a user choice; do not silently pick one property. [Recipe 19](../../recipes/19-address-to-zoning/) has seven language ports. Fixture verification is complete; live production behavior has not been verified by this cookbook.

## Pick the resolver

| Input and interaction | Operation | Follow-up |
|---|---|---|
| Person typing an address or APN | `GET /v2/locations/suggest` | Show suggestions, then call `GET /v2/locations/retrieve/{gridics_id}` with the same session token for the selected item. |
| One-off address or APN text | `GET /v2/locations/forward` | Review all returned features; more than one is ambiguous. |
| Exact parcel, address, APN, or coordinates in a known entitled county | `POST /v2/parcels/lookup` | Use the returned parcel and county identifiers. |

Location Search does not require callers to discover a county ID. It is still a preview capability and depends on current account access. [Recipe 18](../../recipes/18-location-search/) demonstrates both interaction styles; [recipe 03](../../recipes/03-property-lookup/) covers exact county-scoped lookup.

## Query zoning

For a known parcel, call `GET /v2/parcels/{parcel_id}/zoning` with its entitled `place_id`; [recipe 20](../../recipes/20-parcel-zoning/) has seven language ports. The older `POST /v2/zoning/query` flow remains in [recipe 04](../../recipes/04-zoning-query/). Keep multiple matching parcels visible to the user rather than choosing one silently. Retain multiple buildings and zoning districts, ordinance links, request IDs, and unknown values in the result.

For additional available parcel details and paginated use permissions, inspect the public [OpenAPI contract](../../contracts/openapi-v2.json) and your account's field discovery response. Do not treat an omitted field as “not permitted.”

The [appraiser example](../../recipes/17-appraiser-zoning-lookup/) shows a factual subject-property summary with provenance and explicit unknowns.

Use the returned parcel `id` or `identifiers.group_id` as `group_id` for recipe 04, with its returned county and matching market. Basic parcel examples request parcel fields only; add zoning fields only after field discovery confirms caller availability.

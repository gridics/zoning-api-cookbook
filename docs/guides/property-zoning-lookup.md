# Property zoning lookup by address, APN, or parcel

The current published V2 contract uses two steps: resolve the property, then query zoning for its returned identity. This guide describes the available API; fixture checks do not establish production access for your account.

## Pick the resolver

| Input and interaction | Operation | Follow-up |
|---|---|---|
| Person typing an address or APN | `GET /v2/locations/suggest` | Show suggestions, then call `GET /v2/locations/retrieve/{gridics_id}` with the same session token for the selected item. |
| One-off address or APN text | `GET /v2/locations/forward` | Review all returned features; more than one is ambiguous. |
| Exact parcel, address, APN, or coordinates in a known entitled county | `POST /v2/parcels/lookup` | Use the returned parcel and county identifiers. |

Location Search does not require callers to discover a county ID. It is still a preview capability and depends on current account access. [Recipe 18](../../recipes/18-location-search/) demonstrates both interaction styles; [recipe 03](../../recipes/03-property-lookup/) covers exact county-scoped lookup.

## Query zoning

Call `POST /v2/zoning/query` using the returned canonical Market, Place, and parcel identifiers. [Recipe 04](../../recipes/04-zoning-query/) contains seven server-language ports. Keep multiple matching parcels visible to the user rather than choosing one silently. Retain multiple buildings and zoning districts, ordinance links, request IDs, and unknown values in the result.

For additional available parcel details and paginated use permissions, inspect the public [OpenAPI contract](../../contracts/openapi-v2.json) and your account's field discovery response. Do not treat an omitted field as “not permitted.”

The [appraiser example](../../recipes/17-appraiser-zoning-lookup/) shows a factual subject-property summary with provenance and explicit unknowns.

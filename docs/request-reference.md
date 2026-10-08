# Public request conventions

All V2 calls use HTTPS and send the complete API key in the `x-api-key` header. JSON requests also send `Content-Type: application/json`.

Use Market IDs returned by `/v2/markets` and county/Place IDs returned by `/v2/markets/{market_id}/places`. Catalog coverage is informational and does not grant access.

Property lookup accepts one county/Place plus exactly one locator: parcel ID, APN, address and postal code, or longitude/latitude. Keep APNs as strings. A `404` does not reveal whether an out-of-scope parcel exists; a `409` is ambiguous and needs better input; a `422` means the request shape is invalid.

Simple search supports common county-scoped filters. Advanced search uses the authoritative `/v2/parcels/search-fields` response for field names, supported operators, units, projection, sorting, and availability. Never send private backend aliases or raw query syntax.

Pagination cursors are opaque. Send them back unchanged with the same scope/query. Stop on an absent or repeated cursor and enforce page and row limits. Do not describe traversal as a point-in-time snapshot unless the public API explicitly guarantees that behavior.

Error handling distinguishes `401` authentication, `403` capability/entitlement, `404` hidden or missing resources, `409` ambiguity, `422` validation, `429` limits, `502` upstream failure, and `503` temporarily unavailable authorization/catalog/usage/release state. Runners retry only bounded transient statuses and honor `Retry-After` when present.

Search field discovery distinguishes projection availability (`caller_available`) from filter availability (`filter_caller_available`). A returned lot-area value does not imply that lot-area filtering is released. Default searches use vacancy; check discovery before adding lot-area or zoning constraints. Capacity screening skips its search when the capacity projection is unavailable. Only a 403 on an optional request is classified as capability unavailable; validation, missing resources, and service failures remain errors.

Paged results use `pagination.next_cursor`; exports stop at their page/row budget and preserve whether a cursor remains.

`sortable` describes a field's supported operation, but the caller and market release gates still apply. Default examples omit sorting; an unreleased sort returns `sort_not_available`.

# Zoning API for property and parcel applications

The published V2 path resolves the correct parcel first and then requests zoning for that parcel. Keep the returned county, parcel identity, request ID, source context, and unknown values together.

## Start with the right operation

- **Interactive address/APN box:** [Location Search](../../recipes/18-location-search/) suggest → retrieve with one session token.
- **One-off address/APN:** Location Search forward; review all returned candidates.
- **Known exact parcel and county:** [Property lookup](../../recipes/03-property-lookup/).
- **Common county-scoped search:** [Simple search](../../recipes/05-simple-search/).
- **Advanced typed search:** [Field discovery and advanced search](../../recipes/08-advanced-search/); only send fields and operators currently marked available.

Then use [zoning query](../../recipes/04-zoning-query/) with the identifiers returned by resolution. The current query response can contain multiple buildings; do not collapse them into one invented district or capacity value. Detailed use permissions are a separate public parcel operation when entitled. Preserve each returned `permission` value and distinguish it from missing source data.

The checked-in [public OpenAPI](../../contracts/openapi-v2.json) describes request shapes; the Developer Portal is authoritative for your current plan and geography. The cookbook's routine tests use synthetic fixtures, so test an entitled property before depending on a live workflow.

# Recipe verification status

The cookbook remains a preview. On October 16, 2026, its checked-in contract was
compared with the public document at
[the Developer Portal](https://developer.gridics.com/openapi/v2/public.json).
All 20 paths, operations and 68 referenced schemas were identical. The lookup,
simple search, advanced search, zoning query, address-to-zoning and parcel-zoning
request schemas also matched the production API's OpenAPI document.
Contract agreement does not demonstrate provider readiness or plan access.

`GRIDICS_PARCEL_ID` supplies the public `parcel_id` returned by lookup/search.
For the advanced zoning query, supply that returned `id` or
`identifiers.group_id` as `group_id`, retaining its returned `place_id` and a
matching entitled `market_id`. It is neither an APN nor a zoning district ID.
Recipes 19 and 20 offer simpler address-to-zoning and known-parcel workflows.
Never substitute IDs between unrelated counties, suggestions or workspaces.

Protected live verification offers each of recipes 01–20 and the complete matrix.
It runs only from the default branch, requires the production-verification
protected environment, retains bounded request limits and two parallel languages,
and accepts only the dedicated verification profile. Running it can consume paid
usage; fixture success does not authorize a live run. No live verification was
requested as part of the October 16 fixture audit.

See each recipe's availability notes. Capability-unavailable responses are
recorded separately and never count as live verified. In particular, recipe 11
must discover available capacity fields before issuing a capacity search, and
Location Search (18) stays in preview until the complete live matrix passes.

Basic lookup, simple search and advanced-search examples request parcel fields
only. Discover caller-available zoning fields before adding them; a successful
parcel search does not grant zoning access. Use a full address with city, state
and postal code for the county-free address-to-zoning recipe.

## Local fixture matrix — October 16, 2026

All rows passed against synthetic loopback fixtures in Python, Node.js,
TypeScript, PHP, C#, Java and Go. Live production acceptance was not run.

| Recipe | Seven-language fixtures | Live production |
|---|---|---|
| 01 | Pass | Not run |
| 02 | Pass | Not run |
| 03 | Pass | Not run |
| 04 | Pass | Not run |
| 05 | Pass | Not run |
| 06 | Pass | Not run |
| 07 | Pass | Not run |
| 08 | Pass | Not run |
| 09 | Pass | Not run |
| 10 | Pass | Not run |
| 11 | Pass | Not run |
| 12 | Pass | Not run |
| 13 | Pass | Not run |
| 14 | Pass | Not run |
| 15 | Pass | Not run |
| 16 | Pass | Not run |
| 17 | Pass | Not run |
| 18 | Pass | Not run |
| 19 | Pass | Not run |
| 20 | Pass | Not run |

# Parcel zoning data

Parcel zoning data becomes useful when it is joined to the same canonical property record your application already uses.

Gridics examples preserve parcel IDs, APNs, addresses, Market/Place context, zoning codes, and optional development-related fields without collapsing missing values into zero or false.

## Good uses

- show zoning on a property profile;
- enrich a property portfolio;
- search parcels using supported parcel and zoning filters;
- build a zoning factsheet;
- pass structured property/zoning facts into an AI tool.

For a single subject property, use [property lookup](../../recipes/03-property-lookup/) followed by [zoning query](../../recipes/04-zoning-query/). For larger candidate sets, use [advanced parcel search](../../recipes/08-advanced-search/).
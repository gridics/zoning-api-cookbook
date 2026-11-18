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

## Request only the fields you need

Use parcel detail when you need selected property facts or per-building zoning standards for a known parcel. Discover selector names with the field catalog before choosing them. Use the same API key for discovery and detail so the calls use the same account permissions.

```sh
curl --fail-with-body --silent --show-error \
  -H "x-api-key: ${GRIDICS_API_KEY}" \
  https://api.gridics.com/v2/parcels/search-fields
```

Set `GRIDICS_FIELD_SELECTOR` to a parcel-detail selector from the catalog and `GRIDICS_FIELD_GROUP` to its matching include group. Use the canonical parcel and place IDs from public lookup or search. Repeat `fields` and `include` to request multiple selectors or groups.

```sh
curl --fail-with-body --silent --show-error --get \
  -H "x-api-key: ${GRIDICS_API_KEY}" \
  --data-urlencode "place_id=${GRIDICS_PLACE_ID}" \
  --data-urlencode "include=${GRIDICS_FIELD_GROUP}" \
  --data-urlencode "fields=${GRIDICS_FIELD_SELECTOR}" \
  "https://api.gridics.com/v2/parcels/${GRIDICS_PARCEL_ID}"
```

Read the resource and value states before using a result. Keep a reported zero, and preserve missing or unavailable measurements as unknown. Use the units declared by the response schema. For example, the published `total_length_ft` frontage property is in feet. See the [bundled V2 contract](../../contracts/openapi-v2.json) for the response schema.

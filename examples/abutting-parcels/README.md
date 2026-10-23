# Abutting parcel zoning and direction

Retrieve a parcel together with detailed zoning and centroid directions for its
abutting neighbors:

`GET /v2/parcels/{parcel_id}/abutting?place_id={county_place_id}`

This example requires the operation to be available in your API environment,
parcel access, zoning access, and an entitled county. The example response is
synthetic; fixture verification is not live API verification.

## Run without credentials

Python 3.10 or newer; no third-party packages are needed.

```bash
python3 examples/abutting-parcels/main.py --fixture
```

Inspect [response.json](response.json) for the complete illustrative envelope.
The original parcel is in `data.identity`; each neighbor is in `data.abutting`.
Each neighbor's `identity` contains `centroid`, `direction`,
`bearing_degrees`, and `direction_state`. Zoning stays grouped by source
building in `buildings[].zoning`.

## Call the API

Use an API key kept on your server, the parcel ID returned by lookup/search,
and its canonical county Place ID. Never send your secret key from a browser.

```bash
export GRIDICS_API_BASE_URL="https://api.gridics.com"
export GRIDICS_API_KEY="REPLACE_WITH_YOUR_SERVER_SIDE_KEY"
export GRIDICS_PARCEL_ID="REPLACE_WITH_RETURNED_PARCEL_ID"
export GRIDICS_PLACE_ID="REPLACE_WITH_RETURNED_COUNTY_PLACE_ID"
python3 examples/abutting-parcels/main.py
```

The equivalent request is:

```bash
curl --fail-with-body --get \
  --header "x-api-key: ${GRIDICS_API_KEY}" \
  --data-urlencode "place_id=${GRIDICS_PLACE_ID}" \
  "${GRIDICS_API_BASE_URL}/v2/parcels/${GRIDICS_PARCEL_ID}/abutting"
```

## Interpret the result

- Direction points from the original centroid toward the neighbor centroid.
  N, NE, E, SE, S, SW, W, NW use eight compass sectors.
- Bearings are clockwise from true north: north 0, east 90, south 180, west 270.
- Missing centroids return null direction/bearing with `not_available`.
  Coincident centroids use `not_applicable`; do not infer a side or frontage.
- `zoning_state: no_records` means the neighbor exists but has no zoning record.
  Do not invent a zoning district for it.
- `meta.resource_states.abutting` distinguishes available adjacency from
  `no_records` (empty source list) and `not_available` (missing adjacency).
- The response is bounded to 100 neighbors. One standard API request plus
  returned neighbor rows is recorded; the operation reserves 100 result rows
  before lookup, so smaller remaining row quotas can prevent a request.
- Unknown or unauthorized parcels share a 404 response. Permission failures,
  quota limits, and provider failures are errors rather than partial success.
  Review your plan and endpoint availability before treating a 404 as empty adjacency.

Run the example checks with:

```bash
python3 -m unittest discover -s examples/abutting-parcels -p 'test_*.py'
```

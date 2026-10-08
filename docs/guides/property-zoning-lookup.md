# Property zoning lookup by address, APN, or parcel

The safest zoning lookup flow is resolution first, zoning second.

## Address or APN

Use [Location Search](../../recipes/18-location-search/) when you want free-form address/APN input without requiring the caller to know a county ID first. For server-side workflows that already know the entitled county, [property lookup](../../recipes/03-property-lookup/) also resolves address, APN, parcel ID, or coordinates.

After resolution, call [zoning query](../../recipes/04-zoning-query/) with the canonical identifiers returned by Gridics rather than unrelated preconfigured IDs.

## Why the two-stage pattern matters

It makes ambiguity visible, prevents accidental cross-county assumptions, and gives professional workflows a clear chain from user input to canonical parcel to zoning response.

The [appraiser example](../../recipes/17-appraiser-zoning-lookup/) shows this pattern with provenance and explicit unknowns.
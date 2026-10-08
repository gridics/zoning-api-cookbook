# Zoning API for property and parcel applications

A zoning API should answer a developer's real workflow question: identify the correct property, retrieve the zoning attached to that property, preserve the source context, and keep unknown values explicit.

With Gridics, start by resolving a canonical parcel with [property lookup](../../recipes/03-property-lookup/) or [Location Search](../../recipes/18-location-search/). Then use [zoning query](../../recipes/04-zoning-query/) with the returned Market, Place, and parcel identifiers.

## Common applications

- property-detail pages that need zoning alongside parcel facts;
- brokerage, appraisal, and due-diligence workflows;
- development and redevelopment screening;
- site-selection applications;
- zoning-aware AI assistants and agent tools.

## Recommended request flow

1. Resolve the address, APN, parcel ID, or coordinates.
2. Confirm the canonical parcel and geography returned by Gridics.
3. Request zoning using those returned identifiers.
4. Preserve request/provenance metadata and unknown values.
5. Treat the response as factual data, not a permit or legal conclusion.

Start with [recipe 03](../../recipes/03-property-lookup/), [recipe 04](../../recipes/04-zoning-query/), and the [Developer Portal](https://developer.gridics.com/get-started).
# Zoning data for appraisal software

Appraisal software often starts with a subject address or APN and needs factual zoning information attached to the correct parcel.

The [appraiser zoning lookup](../../recipes/17-appraiser-zoning-lookup/) resolves the subject, derives canonical Market/Place/parcel identifiers from the successful lookup, requests zoning, and produces a normalized report with provenance and unknowns.

Use the county-scoped exact lookup when the subject county is known. For free-form input without a county, use [Location Search](../../recipes/18-location-search/): forward for a one-off query, or suggest → retrieve when an appraiser selects a candidate in an interface. Preserve ambiguous matches for review before querying zoning. The current public API uses the two-step flow; a single address-to-zoning request is not in the checked-in published contract.

This is designed to support an appraiser's research workflow. It does not replace professional judgment or create a formal zoning determination.

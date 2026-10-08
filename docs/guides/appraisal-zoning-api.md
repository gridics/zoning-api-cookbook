# Zoning data for appraisal software

Appraisal software often starts with a subject address or APN and needs factual zoning information attached to the correct parcel.

The [appraiser zoning lookup](../../recipes/17-appraiser-zoning-lookup/) resolves the subject, derives canonical Market/Place/parcel identifiers from the successful lookup, requests zoning, and produces a normalized report with provenance and unknowns.

This is designed to support an appraiser's research workflow. It does not replace professional judgment or create a formal zoning determination.
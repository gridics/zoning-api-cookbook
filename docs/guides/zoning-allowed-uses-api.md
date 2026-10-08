# Zoning rules and allowed-use data

Applications often need more than a district code. The useful question is what zoning rules or use information are actually available for the resolved parcel.

The public zoning response can include structured zoning sections defined by the current API contract. Your application should inspect the returned response and capability/field availability rather than assume every jurisdiction releases the same fields.

## Implementation guidance

- resolve the canonical parcel first;
- request zoning for that parcel;
- render returned rules and use information as factual fields;
- keep unavailable or omitted fields distinct from a negative result;
- never infer a legal conclusion from a missing field.

Use [recipe 04](../../recipes/04-zoning-query/) and the checked-in [OpenAPI V2 contract](../../contracts/openapi-v2.json) as the implementation references.
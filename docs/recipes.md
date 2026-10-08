# Recipe index

| # | Recipe | Level | Primary capability |
|---:|---|---|---|
| 01 | [Hello world](../recipes/01-hello-world/) | Beginner | Active V2 key |
| 02 | [Discover counties](../recipes/02-discover-counties/) | Beginner | Market discovery |
| 03 | [Property lookup](../recipes/03-property-lookup/) | Beginner | Standard parcel access |
| 04 | [Zoning query](../recipes/04-zoning-query/) | Beginner | Zoning query |
| 05 | [Simple search](../recipes/05-simple-search/) | Beginner | Standard parcel access |
| 06 | [Paginate/export](../recipes/06-paginate-export/) | Intermediate | Standard parcel access |
| 07 | [Errors/retries](../recipes/07-errors-retries/) | Intermediate | Active V2 key |
| 08 | [Advanced search](../recipes/08-advanced-search/) | Intermediate | Advanced parcel search |
| 09 | [Polygon search](../recipes/09-polygon-search/) | Intermediate | Advanced parcel search + geometry |
| 10 | [Portfolio enrichment](../recipes/10-portfolio-enrichment/) | Business | Standard parcel access |
| 11 | [Redevelopment screen](../recipes/11-redevelopment-screen/) | Business, gated | Capacity field capability |
| 12 | [Retail shortlist](../recipes/12-retail-shortlist/) | Business | Advanced parcel search |
| 13 | [Property factsheet](../recipes/13-property-factsheet/) | Business | Parcel + optional zoning |
| 14 | [Snapshot diff](../recipes/14-snapshot-diff/) | Business | Standard parcel access |
| 15 | [Due diligence](../recipes/15-due-diligence/) | Business | Parcel + optional zoning |
| 16 | [MCP tools](../recipes/16-mcp-tools/) | Advanced | Read-only allow-listed tools |
| 17 | [Appraiser zoning lookup](../recipes/17-appraiser-zoning-lookup/) | Business | Direct V2 + hosted MCP equivalent |
| 18 | [Location Search](../recipes/18-location-search/) | Beginner / preview | Suggest/retrieve/forward; no required county ID; protected live verification required before GA claim |

Every row has seven runnable language entry points. Runtime-specific CI plus `tests/validate_repository.py` enforce completeness.


## Browse by problem

- **Zoning by address/APN:** 18 → 03 → 04
- **Development/redevelopment:** 08 → 09 → 11
- **Site selection:** 08 → 09 → 12
- **Portfolio enrichment:** 10
- **Brokerage/due diligence:** 13 → 14 → 15
- **Appraisal:** 17
- **AI/MCP:** 16 plus [integrations/mcp](../integrations/mcp/)

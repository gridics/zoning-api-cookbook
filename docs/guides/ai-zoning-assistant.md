# Build an AI zoning assistant

A zoning assistant should not ask a language model to guess from an address or invent missing regulations. Give the model typed tools that resolve a property and retrieve structured Gridics facts.

## Recommended agent flow

1. accept the user's address, APN, or parcel reference;
2. resolve it to a canonical Gridics property;
3. call parcel/zoning tools through REST or MCP;
4. retain references, request IDs, and explicit unknowns;
5. let the model explain returned facts and ask clarifying questions when resolution is ambiguous.

This architecture works for chat assistants, brokerage copilots, appraisal research, developer/site-selection agents, and partner applications.

Start with [MCP tools](../../recipes/16-mcp-tools/), [appraiser lookup](../../recipes/17-appraiser-zoning-lookup/), and the [MCP integration guide](../../integrations/mcp/).
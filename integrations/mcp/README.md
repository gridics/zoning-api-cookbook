# Gridics MCP integrations

Gridics Public API provides a hosted Model Context Protocol connection for structured property and zoning workflows. The canonical Public API path is **/mcp**; use the **MCP Connections** experience in the [Gridics Developer Portal](https://developer.gridics.com/) to obtain the deployment-specific connection and complete authorization.

## What to expose to an AI client

Prefer a small, typed tool surface:

- inspect the authenticated Gridics context;
- discover entitled geography;
- resolve or look up a property;
- search parcels with bounded result counts;
- retrieve zoning for a canonical property.

Keep API keys and backend credentials server-side. Never put a Gridics secret in an MCP schema, tool argument, prompt, model result, or browser bundle.

## ChatGPT, Claude, Cursor, and other MCP clients

Use the connection URL and authorization flow shown by the Developer Portal rather than hard-coding an environment hostname from this repository. Client UIs change independently of Gridics; the stable integration contract is the Developer Portal connection plus the MCP protocol.

After connection, verify that the client can initialize the server and list the tools available to your Organization before building a workflow around a specific capability.

## Local adapter example

[Recipe 16](../../recipes/16-mcp-tools/) contains a small read-only MCP-compatible JSON-RPC adapter in all seven cookbook languages. It is useful for understanding tool boundaries and testing local agent behavior. For supported hosted integrations, prefer the Developer Portal connection.

## Agent pattern

A good zoning agent resolves the property first, calls structured Gridics tools, preserves references and unknowns, then asks the language model to explain the returned facts. See [Build an AI zoning assistant](../../docs/guides/ai-zoning-assistant.md).
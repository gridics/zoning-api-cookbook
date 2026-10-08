#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "recipes/manifest.json").read_text())
openapi = json.loads((ROOT / "contracts/openapi-v2.json").read_text())
errors = []

if openapi.get("servers") != [{"url": "https://api.gridics.com"}]:
    errors.append("snapshot server does not match the documented production public API origin")
security = openapi.get("components", {}).get("securitySchemes", {}).get("ApiKeyAuth", {})
if security.get("name") != "x-api-key" or security.get("in") != "header":
    errors.append("snapshot no longer describes x-api-key header authentication")

for recipe in manifest["recipes"]:
    for step in recipe["steps"]:
        path = re.sub(r"\$\{GRIDICS_MARKET_ID\}", "{market_id}", step["path"])
        path = path.split("?", 1)[0]
        operation = openapi.get("paths", {}).get(path, {}).get(step["method"].lower())
        if not operation:
            errors.append(f"recipe {recipe['id']} uses missing operation {step['method']} {path}")
        elif operation.get("x-gridics-audience") != "public":
            errors.append(f"recipe {recipe['id']} operation is not marked public: {step['method']} {path}")

required_schemas = ["ParcelLookupRequest", "SimpleParcelSearchRequest", "ParcelSearchRequest", "ZoningQueryRequest", "PublicError"]
schemas = openapi.get("components", {}).get("schemas", {})
for name in required_schemas:
    if name not in schemas: errors.append(f"missing public schema {name}")

if errors:
    print("Contract validation failed:\n" + "\n".join(f"- {error}" for error in errors)); sys.exit(1)
print(f"Contract validation passed for {sum(len(item['steps']) for item in manifest['recipes'])} recipe steps against the checked-in public OpenAPI snapshot.")

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "recipes/manifest.json").read_text())
openapi = json.loads((ROOT / "contracts/openapi-v2.json").read_text())
parser = argparse.ArgumentParser(description="Validate the bundled Public API contract.")
parser.add_argument("--published-spec", type=Path, help="Compare with a downloaded Developer Portal OpenAPI file")
args = parser.parse_args()
errors = []

if args.published_spec and openapi != json.loads(args.published_spec.read_text()):
    errors.append("snapshot differs from the published Developer Portal OpenAPI")

# Standalone examples are not listed in the multilingual recipe manifest.
for path in ("/v2/parcels/{parcel_id}", "/v2/parcels/{parcel_id}/abutting"):
    operation = openapi.get("paths", {}).get(path, {}).get("get", {})
    if operation.get("x-gridics-audience") != "public":
        errors.append(f"missing public example operation GET {path}")

if openapi.get("servers") != [{"url": "https://api.gridics.com"}]:
    errors.append("snapshot server does not match the documented production public API origin")
security = openapi.get("components", {}).get("securitySchemes", {}).get("ApiKeyAuth", {})
if security.get("name") != "x-api-key" or security.get("in") != "header":
    errors.append("snapshot no longer describes x-api-key header authentication")

for recipe in manifest["recipes"]:
    for step in recipe["steps"]:
        path = re.sub(r"\$\{GRIDICS_MARKET_ID\}", "{market_id}", step["path"])
        path = re.sub(r"\$\{GRIDICS_PARCEL_ID\}", "{parcel_id}", path)
        path = path.split("?", 1)[0]
        operation = openapi.get("paths", {}).get(path, {}).get(step["method"].lower())
        if not operation:
            errors.append(f"recipe {recipe['id']} uses missing operation {step['method']} {path}")
        elif operation.get("x-gridics-audience") != "public":
            errors.append(f"recipe {recipe['id']} operation is not marked public: {step['method']} {path}")

required_schemas = ["ParcelLookupRequest", "SimpleParcelSearchRequest", "ParcelSearchRequest", "ZoningQueryRequest", "ZoningLookupRequest", "ZoningParcelResponse", "PublicError"]
schemas = openapi.get("components", {}).get("schemas", {})
for name in required_schemas:
    if name not in schemas: errors.append(f"missing public schema {name}")

if errors:
    print("Contract validation failed:\n" + "\n".join(f"- {error}" for error in errors)); sys.exit(1)
print(f"Contract validation passed for {sum(len(item['steps']) for item in manifest['recipes'])} recipe steps against the checked-in public OpenAPI snapshot.")

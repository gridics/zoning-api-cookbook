#!/usr/bin/env python3
"""Generate the repetitive cookbook wrappers and recipe documentation."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = {
    "python": ("Python 3.11+", "python3 main.py"),
    "nodejs": ("Node.js 20+", "node main.mjs"),
    "typescript": ("TypeScript 5 / Node.js 20+", "npm --prefix ../../.. install\nnpm --prefix ../../.. run build\nnode ../../../dist/recipes/{slug}/typescript/main.js"),
    "php": ("PHP 8.2+", "php main.php"),
    "csharp": (".NET 8+", "dotnet run"),
    "java": ("Java 21+", "javac -d build ../../../languages/java/GridicsCookbook.java Main.java && java -cp build Main"),
    "go": ("Go 1.22+", "go run ."),
}

recipes = [
    ("01", "hello-world", "Hello world: verify an API key", "beginner", ["GET /v2/me"], "Confirm that a newly issued key works and inspect its effective API context.", "One non-billable credential verification request; authentication and edge limits still apply."),
    ("02", "discover-counties", "Discover coverage and entitled counties", "beginner", ["GET /v2/market-catalog", "GET /v2/markets", "GET /v2/markets/{market_id}/places"], "List coverage separately from the counties the current key may query.", "At most three discovery requests per run."),
    ("03", "property-lookup", "Look up a property", "beginner", ["POST /v2/parcels/lookup"], "Resolve one property by address, APN, parcel ID, or coordinates inside an entitled county.", "One standard request plus the returned parcel row."),
    ("04", "zoning-query", "Retrieve zoning for a known property", "beginner", ["POST /v2/zoning/query"], "Retrieve the current public zoning response for a parcel already resolved by Gridics.", "One zoning-query unit when successful."),
    ("05", "simple-search", "Search a county with simple filters", "beginner", ["POST /v2/parcels/simple-search"], "Find a small list of vacant parcels; add other constraints only when field discovery confirms filter availability.", "One standard request plus returned parcel rows; defaults to 10 rows."),
    ("06", "paginate-export", "Paginate and export results", "intermediate", ["POST /v2/parcels/simple-search"], "Follow opaque cursors safely and create a bounded JSON export suitable for CSV conversion.", "Stops after three pages or 100 rows, whichever comes first."),
    ("07", "errors-retries", "Handle errors, throttling, and retries", "intermediate", ["GET /v2/me"], "Classify authentication, entitlement, validation, throttling, and transient service errors.", "At most three attempts and 30 seconds; only 429, 502, and 503 are retryable."),
    ("08", "advanced-search", "Build an advanced parcel search", "intermediate", ["GET /v2/parcels/search-fields", "POST /v2/parcels/search"], "Discover released fields before submitting a typed, projected search; add sorting only where released.", "One field-discovery request and one advanced search; defaults to 10 rows."),
    ("09", "polygon-search", "Search within a GeoJSON polygon", "intermediate", ["POST /v2/parcels/search"], "Search an explicitly entitled county within a small customer-supplied study polygon.", "One advanced search and at most 10 rows."),
    ("10", "portfolio-enrichment", "Enrich a property portfolio", "business", ["POST /v2/parcels/lookup"], "Resolve the synthetic portfolio inputs and preserve a row-level success or error result.", "The sample contains two rows; production use must set an explicit row and request budget."),
    ("11", "redevelopment-screen", "Screen redevelopment candidates", "business / capability-gated", ["GET /v2/parcels/search-fields", "POST /v2/parcels/search"], "Check whether capacity fields are released before screening for potential underbuilt parcels.", "No live capacity claim is made when fields remain unavailable or capability-gated."),
    ("12", "retail-shortlist", "Shortlist franchise or retail sites", "business", ["GET /v2/parcels/search-fields", "POST /v2/parcels/search"], "Apply supported parcel constraints and produce an explainable, bounded candidate set.", "At most 20 candidates; local preferences do not imply demographics, traffic, rent, or competitors."),
    ("13", "property-factsheet", "Generate a brokerage property factsheet", "business", ["POST /v2/parcels/lookup", "POST /v2/zoning/query"], "Collect public parcel and zoning facts with request provenance for a printable report.", "One lookup and one optional zoning request."),
    ("14", "snapshot-diff", "Detect changes between property snapshots", "business", ["POST /v2/parcels/lookup"], "Capture a bounded current snapshot for comparison with a customer-managed prior snapshot.", "Observed response changes are not an ordinance event feed or historical zoning service."),
    ("15", "due-diligence", "Build a due-diligence screening report", "business", ["POST /v2/parcels/lookup", "POST /v2/zoning/query"], "Gather facts for customer-defined screening rules while preserving unknown values for review.", "Missing data produces needs_review; this is not a legal determination, appraisal, or credit decision."),
    ("16", "mcp-tools", "Expose bounded MCP tools", "advanced", ["GET /v2/me", "GET /v2/markets", "POST /v2/parcels/lookup", "POST /v2/parcels/simple-search", "POST /v2/zoning/query"], "Run a read-only MCP-compatible JSON-RPC server with typed, allow-listed Gridics tools.", "Five Gridics calls per workflow, 10 search results, and two zoning enrichments by default."),
    ("17", "appraiser-zoning-lookup", "Appraiser zoning lookup", "business", ["POST /v2/parcels/lookup", "POST /v2/zoning/query"], "Resolve an appraisal subject by address/APN and report factual zoning with provenance and explicit unknowns.", "One lookup and one optional zoning operation; no uncertain paid retry."),
    ("18", "location-search", "Location Search API", "beginner", ["GET /v2/locations/suggest", "GET /v2/locations/retrieve/{gridics_id}", "GET /v2/locations/forward"], "Resolve free-form address/APN with suggest/retrieve or forward without a required county ID.", "One commercial unit per interactive session or forward request; HTTP rate limits count each request."),
]

def write(relative: str, content: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")

manifest = {
    "schema_version": 1,
    "api": {
        "version": "v2",
        "default_base_url": "https://api.gridics.com",
        "authentication_header": "x-api-key",
        "contract_source": "contracts/openapi-v2.json",
        "reviewed_on": "2026-10-05",
    },
    "defaults": {
        "GRIDICS_MARKET_ID": "market_example",
        "GRIDICS_PLACE_ID": "place_example_county",
        "GRIDICS_PARCEL_ID": "parcel_example_001",
        "GRIDICS_APN": "000000000001",
        "GRIDICS_ADDRESS": "100 Example Ave",
        "GRIDICS_POSTAL_CODE": "00000",
        "GRIDICS_LOCATION_QUERY": "100 Example Ave", "GRIDICS_LOCATION_MODE": "suggest_retrieve", "GRIDICS_LOCATION_LIMIT": "5", "GRIDICS_LOCATION_COUNTRY": "US", "GRIDICS_LOCATION_LANGUAGE": "en", "GRIDICS_LOCATION_PROXIMITY": "", "GRIDICS_LOCATION_BBOX": "",
    },
    "recipes": [],
}

def step(name, method, path, body=None, query=None, optional=False):
    item = {"name": name, "method": method, "path": path}
    if body is not None: item["body"] = body
    if query is not None: item["query"] = query
    if optional: item["optional"] = True
    return item

lookup = {"place_id": "${GRIDICS_PLACE_ID}", "address": {"street": "${GRIDICS_ADDRESS}", "postal_code": "${GRIDICS_POSTAL_CODE}"}, "fields": ["parcel.id", "parcel.apn", "parcel.address", "parcel.lot_area", "parcel.vacant", "zoning.code"]}
zoning = {"market_id": "${GRIDICS_MARKET_ID}", "place_id": "${GRIDICS_PLACE_ID}", "group_id": "${GRIDICS_PARCEL_ID}"}
simple = {"place_ids": ["${GRIDICS_PLACE_ID}"], "filters": {"vacant": True}, "page_size": 10, "fields": ["parcel.id", "parcel.apn", "parcel.address", "parcel.lot_area", "parcel.vacant", "zoning.code"]}
advanced = {"scope": {"place_ids": ["${GRIDICS_PLACE_ID}"]}, "filters": {"all": [{"field": "parcel.vacant", "operator": "eq", "value": True}]}, "fields": ["parcel.id", "parcel.address", "parcel.lot_area", "zoning.code"], "sort": [], "include_total": False, "page_size": 10}
polygon = {**advanced, "geometry": {"type": "Polygon", "coordinates": [[[-80.20, 25.75], [-80.19, 25.75], [-80.19, 25.76], [-80.20, 25.76], [-80.20, 25.75]]]}}

steps_by_id = {
    "01": [step("credential", "GET", "/v2/me")],
    "02": [step("coverage", "GET", "/v2/market-catalog", query={"page_size": "25"}), step("markets", "GET", "/v2/markets", query={"page_size": "25"}), step("counties", "GET", "/v2/markets/${GRIDICS_MARKET_ID}/places", query={"page_size": "25"})],
    "03": [step("property", "POST", "/v2/parcels/lookup", lookup)],
    "04": [step("zoning", "POST", "/v2/zoning/query", zoning)],
    "05": [step("candidates", "POST", "/v2/parcels/simple-search", simple)],
    "06": [step("page_1", "POST", "/v2/parcels/simple-search", simple)],
    "07": [step("retry_demo", "GET", "/v2/me")],
    "08": [step("fields", "GET", "/v2/parcels/search-fields"), step("candidates", "POST", "/v2/parcels/search", advanced)],
    "09": [step("candidates", "POST", "/v2/parcels/search", polygon)],
    "10": [step("portfolio_row_1", "POST", "/v2/parcels/lookup", lookup), step("portfolio_row_2", "POST", "/v2/parcels/lookup", {**lookup, "apn": "${GRIDICS_APN}", "address": None})],
    "11": [step("fields_gate", "GET", "/v2/parcels/search-fields"), step("candidates", "POST", "/v2/parcels/search", {**advanced, "fields": advanced["fields"] + ["development.max_buildable_area"]}, optional=True)],
    "12": [step("fields", "GET", "/v2/parcels/search-fields"), step("candidates", "POST", "/v2/parcels/search", advanced)],
    "13": [step("property", "POST", "/v2/parcels/lookup", lookup), step("zoning", "POST", "/v2/zoning/query", zoning, optional=True)],
    "14": [step("current_snapshot", "POST", "/v2/parcels/lookup", lookup)],
    "15": [step("property", "POST", "/v2/parcels/lookup", lookup), step("zoning", "POST", "/v2/zoning/query", zoning, optional=True)],
    "18": [step("suggest_1", "GET", "/v2/locations/suggest"), step("suggest_2", "GET", "/v2/locations/suggest"), step("retrieve", "GET", "/v2/locations/retrieve/{gridics_id}")],
    "17": [step("property", "POST", "/v2/parcels/lookup", lookup), step("zoning", "POST", "/v2/zoning/query", zoning, optional=True)],
    "16": [step("credential", "GET", "/v2/me")],
}

APPRAISER_GUIDANCE = """
## Appraiser input and canonical composition

Use the synthetic example `100 Example Ave` when learning the workflow. For a
live request, set `GRIDICS_ADDRESS`, `GRIDICS_POSTAL_CODE` and the entitled
county `GRIDICS_PLACE_ID` using values your Organization is authorized to query.
Direct REST needs a canonical county; use recipe 02 to discover an entitled one.
Discovery does not grant access.

Choose exactly one `GRIDICS_LOCATOR`: `address` (default), `apn`, or
`parcel_id`. Preserve APNs as strings. The runner stops on no match, ambiguity,
unauthorized county, or a lookup without one canonical parcel/Place/Market. It
derives zoning identifiers from the successful lookup rather than trusting
unrelated preconfigured identifiers. Two data operations maximum; each is
attempted once, with no hidden pages or automatic retry of uncertain paid work.

## Output and professional boundary

Every port adds an `appraiser_zoning` workflow with the canonical property,
returned zoning buildings/standards, request/status provenance, retrieval time,
explicit unknowns and a human-readable `markdown` subject summary. Raw returned
facts stay in normalized JSON. Missing description/capacity/uses are not
invented. Null is not zero, false or a negative finding.

The report is a factual Gridics API data summary, not a formal appraisal, title
opinion, legal advice, binding zoning determination or permit assurance. All
checked-in inputs and expected reports are synthetic. Fixture parity covers
address, APN, canonical parcel, no match, ambiguity, wrong county, unavailable
zoning, partial/null standards and quota without billable requests.

Run `python3 tests/run_appraiser_parity.py --language <language>` after the
normal language build to compare the complete report against shared fixtures.
Fixture success is not live production verification.
"""

for rid, slug, title, level, endpoints, outcome, usage in recipes:
    manifest["recipes"].append({"id": rid, "slug": slug, "title": title, "level": level, "outcome": outcome, "usage": usage, "endpoints": endpoints, "steps": steps_by_id[rid]})
for entry in manifest["recipes"]:
    if entry["id"] == "17":
        entry.update(verification="fixture-tested; live production verification tracked separately", persona="Appraiser/property professional", required_capabilities=["parcel_search", "zoning_query (optional)"])
write("recipes/manifest.json", json.dumps(manifest, indent=2))

for rid, slug, title, level, endpoints, outcome, usage in recipes:
    endpoint_list = "\n".join(f"- `{e}`" for e in endpoints)
    curl_examples = []
    for example_step in steps_by_id[rid]:
        example_path = example_step["path"]
        if example_step.get("query"):
            example_path += "?" + "&".join(f"{key}={value}" for key, value in example_step["query"].items())
        lines = [
            f"curl --fail-with-body --request {example_step['method']} \\",
            f"  --url \"${{GRIDICS_API_BASE_URL}}{example_path}\" \\",
            "  --header \"x-api-key: ${GRIDICS_API_KEY}\"",
        ]
        if "body" in example_step:
            payload = json.dumps(example_step["body"], separators=(",", ":"))
            lines[-1] += " " + "\\"
            shell_payload = payload.replace('"', '\\"')
            lines += ["  --header \"Content-Type: application/json\" \\", f'  --data "{shell_payload}"']
        if rid == "17" and example_step["name"] == "property":
            lines[-1] += " > subject.json"
        if rid == "17" and example_step["name"] == "zoning":
            lines = [
                '# Requires jq. Derive every zoning identifier from the successful lookup.',
                "jq -e '.data | (.id | type == \"string\") and (.place_id | type == \"string\") and (.market_ids | length == 1)' subject.json > /dev/null",
                "jq '.data | {market_id: .market_ids[0], place_id: .place_id, group_id: .id}' subject.json > zoning-request.json",
                'curl --fail-with-body --request POST \\',
                '  --url "${GRIDICS_API_BASE_URL}/v2/zoning/query" \\',
                '  --header "x-api-key: ${GRIDICS_API_KEY}" \\',
                '  --header "Content-Type: application/json" \\',
                '  --data @zoning-request.json',
            ]
        curl_examples.append(f"### {example_step['name'].replace('_', ' ').title()}\n\n```bash\n" + "\n".join(lines) + "\n```")
    commands = []
    for lang, (label, command) in LANGUAGES.items():
        commands.append(f"### {label}\n\n```bash\ncd recipes/{rid}-{slug}/{lang}\n{command.format(slug=f'{rid}-{slug}')}\n```")
    notes = {
        "03": "Choose exactly one lookup form. The checked-in request uses an address; edit the recipe request or use the APN/parcel/coordinate variants described in `docs/request-reference.md`. A `409` means the locator was ambiguous; do not silently choose a result.",
        "06": "Every native runner follows the opaque `next_cursor` with the original scope and filters, stops on an absent or repeated cursor, and enforces the three-page/100-row bounds. The normalized `workflow` section combines the returned rows and reports whether traversal completed within those bounds.",
        "07": "The runners retry only `429`, `502`, and `503`, honor `Retry-After`, add bounded exponential delay, and never retry authentication, authorization, validation, not-found, or ambiguity responses.",
        "10": "The checked-in two-row synthetic portfolio demonstrates address and APN rows with row-level status in the normalized `workflow` output. Use `fixtures/portfolio.csv` as the input contract when adapting the bounded loop; preserve strings, input order, duplicate lineage, and spreadsheet-safe CSV escaping.",
        "11": "This recipe deliberately fails closed when `development.max_buildable_area` is not returned as enabled by field discovery. Schema presence alone does not establish market availability. A blocked result is the correct outcome until the API advertises the required capability.",
        "12": "The API supplies hard parcel/zoning filters. Any preference score is local and must show its inputs and stable tie-break. Gridics does not supply demographics, traffic, competitors, drive times, rent, or availability unless a future public contract explicitly adds them.",
        "13": "Render only returned facts. Unknown values stay unknown. Escape text before inserting it in HTML, keep the key on a server, and separate customer notes from API facts.",
        "14": "Compare selected stable fields and ignore request IDs when diffing. A failed fetch is not deletion, and an observed response change is not proof of the effective date of a legal zoning change.",
        "15": "Customer rules classify each criterion as `meets`, `does_not_meet`, or `needs_review`. Missing or unavailable inputs always become `needs_review`.",
        "17": "Use GRIDICS_LOCATOR=address, apn or parcel_id. Resolve canonical IDs before zoning; keep unknowns explicit. Hosted /mcp and appraiser-zoning are documented separately and are not fixture verification.",
        "16": "Start the JSON-RPC server with the language runner's `--mcp` option. It supports MCP initialization, `tools/list`, and typed `tools/call` for allow-listed read-only operations. The API key stays in the server environment and never appears in tool schemas or results. This is an educational local adapter; use public Gridics documentation for any hosted integration. Never paste an API key into an LLM or hosted connection.",
    }.get(rid, "The same manifest drives every language port, so route, method, request body, bounds, and normalized output stay aligned.")
    if rid == "18":
        curl_examples = ['```bash\n# Generate a UUIDv4 once for this interaction.\nSESSION_TOKEN=$(python3 -c "import uuid; print(uuid.uuid4())")\ncurl --fail-with-body --get "${GRIDICS_API_BASE_URL}/v2/locations/suggest" --header "x-api-key: ${GRIDICS_API_KEY}" --data-urlencode "q=100 Example Ave" --data-urlencode "session_token=${SESSION_TOKEN}" > suggestions.json\n# Inspect suggestions before selecting one; requires jq.\nGRIDICS_ID=$(jq -er \".suggestions[0].gridics_id\" suggestions.json)\ncurl --fail-with-body --get "${GRIDICS_API_BASE_URL}/v2/locations/retrieve/${GRIDICS_ID}" --header "x-api-key: ${GRIDICS_API_KEY}" --data-urlencode "session_token=${SESSION_TOKEN}"\n# Separate one-off lookup (one commercial unit):\ncurl --fail-with-body --get "${GRIDICS_API_BASE_URL}/v2/locations/forward" --header "x-api-key: ${GRIDICS_API_KEY}" --data-urlencode "q=100 Example Ave"\n```']
    readme = f"""
# {rid}. {title}

**Level:** {level}

## Business outcome

{outcome}

## API operations

{endpoint_list}

## Before you run it

Complete the repository [Getting started](../../README.md#get-an-api-key), copy `.env.example` to `.env`, and replace the synthetic Market, Place, parcel, and address values with IDs returned for your Organization. The examples never discover an ID and then assume that it grants access.

## cURL

{chr(10).join(curl_examples)}

## Run a port

{chr(10).join(commands)}

All ports write the same normalized JSON envelope to stdout. Use `GRIDICS_DRY_RUN=1` to inspect requests without sending them. Use `GRIDICS_FIXTURE_MODE=1` with the test server for deterministic examples.

## Usage and limits

{usage}

These are cookbook safety defaults. Your current plan, capabilities, geography, quotas, and pricing are authoritative in the Gridics Developer Portal.

## Important behavior

{notes}

## Expected result

The command exits `0` only when every required step succeeds. Output includes the recipe ID, API base URL, request count, per-step HTTP status, returned data, and a `fixture` or `live` execution label. Optional capability-gated steps are reported as `unavailable`; they are never filled with invented values.

## Tests

From the repository root, run `python3 tests/validate_repository.py` and the language command documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Normal tests use synthetic fixtures and make no paid requests.
"""
    if rid == "18":
        readme = readme.replace("replace the synthetic Market, Place, parcel, and address values with IDs returned for your Organization", "configure a free-form address/APN query; no Place or Market ID is required")
    if rid in {"03", "17"}:
        readme += "\nFor free-form address/APN search without a required county ID, start with [recipe 18](../18-location-search/README.md).\n"
    if rid == "18":
        readme += "\n" + (ROOT / "docs/location-search.md").read_text().replace("(../examples/", "(../../examples/").replace("(compatibility.md)", "(../../docs/compatibility.md)").replace("(../contracts/", "(../../contracts/")
    if rid == "17":
        readme += "\n" + APPRAISER_GUIDANCE
    write(f"recipes/{rid}-{slug}/README.md", dedent(readme))
    for lang in LANGUAGES:
        base = f"recipes/{rid}-{slug}/{lang}"
        if lang == "python": write(f"{base}/main.py", f"from pathlib import Path\nimport sys\nsys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'languages' / 'python'))\nfrom gridics_cookbook import main\nraise SystemExit(main('{rid}'))")
        elif lang == "nodejs": write(f"{base}/main.mjs", f"import {{ run }} from '../../../languages/nodejs/gridics-cookbook.mjs';\nprocess.exitCode = await run('{rid}');")
        elif lang == "typescript": write(f"{base}/main.ts", f"import {{ run }} from '../../../languages/typescript/gridics-cookbook.js';\nprocess.exitCode = await run('{rid}');")
        elif lang == "php": write(f"{base}/main.php", f"<?php\nrequire_once __DIR__ . '/../../../languages/php/GridicsCookbook.php';\nexit(GridicsCookbook::run('{rid}'));\n")
        elif lang == "csharp":
            write(f"{base}/Program.cs", f"return await GridicsCookbook.RunAsync(\"{rid}\");")
            write(f"{base}/Cookbook.csproj", dedent(f"""
                <Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Compile Include="../../../languages/csharp/GridicsCookbook.cs" Link="GridicsCookbook.cs" /></ItemGroup></Project>
            """))
        elif lang == "java": write(f"{base}/Main.java", f"public final class Main {{ public static void main(String[] args) throws Exception {{ System.exit(GridicsCookbook.run(\"{rid}\", args)); }} }}")
        elif lang == "go": write(f"{base}/main.go", f"package main\nimport (\"os\"; \"github.com/gridics/zoning-api-cookbook/languages/go/cookbook\")\nfunc main() {{ os.Exit(cookbook.Run(\"{rid}\")) }}")

print(f"Generated {len(recipes)} recipe READMEs and {len(recipes) * len(LANGUAGES)} language entry points.")

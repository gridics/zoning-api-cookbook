"""Dependency-free Gridics cookbook runner and bounded MCP stdio server."""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "recipes" / "manifest.json"
TRANSIENT = {429, 502, 503}
MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 20


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _substitute(value: Any, variables: dict[str, str]) -> Any:
    if isinstance(value, str):
        return re.sub(r"\$\{([A-Z0-9_]+)\}", lambda m: variables.get(m.group(1), m.group(0)), value)
    if isinstance(value, list):
        return [_substitute(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: _substitute(item, variables) for key, item in value.items() if item is not None}
    return value


def _variables(manifest: dict[str, Any], overrides: dict[str, Any] | None = None) -> dict[str, str]:
    values = {key: str(os.environ.get(key, value)) for key, value in manifest["defaults"].items()}
    if overrides:
        mapping = {
            "market_id": "GRIDICS_MARKET_ID", "place_id": "GRIDICS_PLACE_ID",
            "parcel_id": "GRIDICS_PARCEL_ID", "apn": "GRIDICS_APN",
            "address": "GRIDICS_ADDRESS", "postal_code": "GRIDICS_POSTAL_CODE",
        }
        for key, value in overrides.items():
            if key in mapping and value is not None:
                values[mapping[key]] = str(value)
    return values


def _error_message(status: int, payload: Any) -> str:
    messages = payload.get("messages") if isinstance(payload, dict) else None
    detail = "; ".join(str(item) for item in messages) if isinstance(messages, list) else "request failed"
    hints = {
        401: "check GRIDICS_API_KEY",
        403: "check the Organization plan, capability, and county entitlement",
        404: "the resource was not found or is hidden outside the entitled scope",
        409: "the property locator is ambiguous; provide a more specific locator",
        422: "check the request fields, locator, units, and canonical IDs",
        429: "a rate, quota, or spending control was reached",
        502: "the upstream property service failed temporarily",
        503: "authorization, catalog, usage, or release state is temporarily unavailable",
    }
    return f"HTTP {status}: {detail}. {hints.get(status, 'inspect the redacted request ID and response')}"


def _request(base_url: str, api_key: str, step: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    query = urllib.parse.urlencode(step.get("query", {}))
    url = base_url.rstrip("/") + step["path"] + (f"?{query}" if query else "")
    request_summary = {"method": step["method"], "url": url, "headers": {"x-api-key": "[REDACTED]"}}
    if "body" in step:
        request_summary["body"] = step["body"]
    if dry_run:
        return {"name": step["name"], "status": "dry_run", "request": request_summary}
    body = json.dumps(step.get("body")).encode() if "body" in step else None
    headers = {"x-api-key": api_key, "Accept": "application/json", "User-Agent": "zoning-api-cookbook/python"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    last: dict[str, Any] | None = None
    for attempt in range(1, step.get("max_attempts", MAX_ATTEMPTS) + 1):
        req = urllib.request.Request(url, data=body, method=step["method"], headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode() or "{}")
                return {"name": step["name"], "status": "ok", "http_status": response.status, "request_id": response.headers.get("x-request-id"), "data": payload}
        except urllib.error.HTTPError as error:
            try:
                payload = json.loads(error.read().decode() or "{}")
            except (ValueError, UnicodeDecodeError):
                payload = {"status": "ERROR", "messages": ["non-JSON error response"]}
            last = {"name": step["name"], "status": "error", "http_status": error.code, "error": _error_message(error.code, payload), "data": payload}
            if error.code not in TRANSIENT or attempt == step.get("max_attempts", MAX_ATTEMPTS):
                return last
            retry_after = error.headers.get("Retry-After")
            delay = min(float(retry_after), 5.0) if retry_after and retry_after.isdigit() else min(0.25 * (2 ** (attempt - 1)) + random.random() * 0.1, 2.0)
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError) as error:
            last = {"name": step["name"], "status": "error", "http_status": None, "error": f"network error: {error.reason if hasattr(error, 'reason') else error}"}
            if attempt == step.get("max_attempts", MAX_ATTEMPTS):
                return last
            time.sleep(min(0.25 * (2 ** (attempt - 1)), 2.0))
    assert last is not None
    return last



def _location_step(step, results, variables, session):
    mode = variables['GRIDICS_LOCATION_MODE']
    if mode == 'forward' and step['name'] != 'suggest_1': return None
    query = {'q': variables['GRIDICS_LOCATION_QUERY'], 'limit': variables['GRIDICS_LOCATION_LIMIT']}
    for key in ('country', 'language', 'proximity', 'bbox'):
        value = variables.get('GRIDICS_LOCATION_' + key.upper())
        if value: query[key] = value
    step['max_attempts'] = 1
    if mode == 'forward':
        step.update(name='forward', path='/v2/locations/forward', query=query)
    elif step['name'] == 'retrieve':
        suggestions = (results[-1].get('data') or {}).get('suggestions', [])
        if not suggestions: return None
        step.update(path='/v2/locations/retrieve/' + urllib.parse.quote(suggestions[0]['gridics_id'], safe=''), query={'session_token': session})
    else: step['query'] = dict(query, session_token=session)
    return step


def _location_report(results):
    suggests = [item for item in results if item['name'].startswith('suggest')]
    suggestions = (suggests[-1].get('data') or {}).get('suggestions', []) if suggests else []
    resolved = next((item.get('data') or {} for item in results if item['name'] in ('retrieve', 'forward')), {})
    features = resolved.get('features', [])
    return {'kind': 'location_search', 'session_token': results[0].get('session_token') if results else None, 'mode': 'forward' if results and results[0]['name'] == 'forward' else 'suggest_retrieve', 'suggestions': suggestions, 'features': features, 'state': 'error' if any(item['status'] == 'error' for item in results) else 'ambiguous' if len(features) > 1 else 'resolved' if features or suggestions else 'no_match', 'provenance': [{'step': item['name'], 'status': item['status'], 'request_id': item.get('request_id') or (item.get('data') or {}).get('response_id')} for item in results]}


def _appraiser_step(step, results, variables):
    step["max_attempts"] = 1
    if step["name"] == "property":
        locator = os.environ.get("GRIDICS_LOCATOR", "address")
        if locator not in {"address", "apn", "parcel_id"}:
            raise ValueError("GRIDICS_LOCATOR must be address, apn or parcel_id")
        if locator != "address":
            step["body"].pop("address", None)
            step["body"][locator] = variables["GRIDICS_APN" if locator == "apn" else "GRIDICS_PARCEL_ID"]
    elif step["name"] == "zoning" and results and results[0]["status"] == "ok":
        subject = results[0]["data"]["data"]
        markets = subject.get("market_ids", [])
        if not subject.get("id") or not subject.get("place_id") or len(markets) != 1:
            raise ValueError("Lookup did not establish one canonical parcel/Place/Market; clarify before zoning")
        step["body"] = {"group_id": subject["id"], "place_id": subject["place_id"], "market_id": markets[0]}
    return step


def _appraiser_report(results):
    from datetime import datetime, timezone
    def data(index):
        return results[index].get("data", {}).get("data") if index < len(results) and results[index]["status"] == "ok" else None
    subject, zoning = data(0), data(1)
    fields = (subject or {}).get("fields", {})
    address = fields.get("parcel.address", (subject or {}).get("address"))
    apn = fields.get("parcel.apn", (subject or {}).get("identifiers", {}).get("apn", (subject or {}).get("apn")))
    code = fields.get("zoning.code", (subject or {}).get("zoning_code"))
    unknowns = ["zoning description", "development capacity", "permitted uses (retrieve separately when authorized)"]
    if address is None: unknowns.append("address")
    if apn is None: unknowns.append("APN")
    if code is None: unknowns.append("zoning designation")
    if fields.get("parcel.lot_area", (subject or {}).get("lot_area")) is None: unknowns.append("lot area")
    envelopes = [b.get("Envelope", {}) for b in (zoning or {}).get("buildings", [])]
    if not any(e.get(k) is not None for e in envelopes for k in ["PrincipalMaxHeight", "TotalBuildingHeightFeet"]): unknowns.append("height")
    if not any(e.get(k) is not None for e in envelopes for k in ["EffectivePFrontSetbackPrincipal", "EffectivePSideSetback", "EffectivePRearSetback"]): unknowns.append("setbacks")
    if not zoning: unknowns.append("zoning response")
    provenance = [{"step": r["name"], "status": r["status"], "request_id": r.get("request_id") or (r.get("data") or {}).get("meta", {}).get("request_id")} for r in results]
    boundary = "Factual Gridics data summary; not a formal appraisal, title opinion, legal advice, binding zoning determination or permit assurance."
    def display(value): return "unknown" if value is None else str(value).replace("\n", " ").replace("`", "")
    markdown = "# Gridics appraisal subject summary\n\n" + "\n".join([
        "Address: " + display(address), "Parcel: " + display((subject or {}).get("id")),
        "APN: " + display(apn), "Zoning designation: " + display(code),
        "Request IDs: " + ", ".join(display(r["request_id"]) for r in provenance),
        "Unknown/unavailable: " + "; ".join(unknowns), boundary]) + "\n"
    return {"kind": "appraiser_zoning", "property": subject, "zoning": zoning,
            "provenance": provenance, "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "unknowns": unknowns, "professional_boundary": boundary, "markdown": markdown}


def _workflow(recipe_id: str, results: list[dict[str, Any]]) -> dict[str, Any] | None:
    def payload(index: int) -> Any:
        if index >= len(results): return None
        envelope = results[index].get("data")
        return envelope.get("data") if isinstance(envelope, dict) else None
    if recipe_id == "18": return _location_report(results)
    if recipe_id == "17": return _appraiser_report(results)
    if recipe_id == "06":
        rows = [row for result in results for row in ((result.get("data") or {}).get("data") or [])]
        return {"kind": "bounded_export", "rows": rows, "row_count": len(rows), "pages": len(results), "complete": not bool(((results[-1].get("data") or {}).get("pagination") or {}).get("next_cursor"))}
    if recipe_id == "10":
        return {"kind": "portfolio_enrichment", "rows": [{"row_id": f"portfolio-{index+1:03d}", "status": result["status"], "property": payload(index)} for index, result in enumerate(results)]}
    if recipe_id == "11":
        blocked = any(result["status"] == "unavailable" for result in results)
        return {"kind": "redevelopment_screen", "assessment_status": "capability_blocked" if blocked else "review_required", "candidates": payload(1) if not blocked else [], "legal_conclusion": False}
    if recipe_id == "12":
        return {"kind": "retail_shortlist", "candidates": payload(1) or [], "scoring": "customer_defined", "excluded_datasets": ["demographics", "traffic", "competitors", "drive_times", "rent", "availability"]}
    if recipe_id == "13":
        return {"kind": "property_factsheet", "property": payload(0), "zoning": payload(1), "provenance": [{"step": item["name"], "request_id": item.get("request_id") or ((item.get("data") or {}).get("meta") or {}).get("request_id")} for item in results], "customer_notes": None}
    if recipe_id == "14":
        return {"kind": "property_snapshot", "property": payload(0), "comparison_semantics": "observed API response; not an ordinance effective-date record"}
    if recipe_id == "15":
        property_data, zoning_data = payload(0), payload(1)
        return {"kind": "due_diligence_screen", "overall": "needs_review", "rule_version": "example-v1", "criteria": [{"name": "property_resolved", "status": "meets" if property_data else "needs_review"}, {"name": "zoning_available", "status": "meets" if zoning_data else "needs_review"}], "facts": {"property": property_data, "zoning": zoning_data}, "legal_conclusion": False}
    return None


def execute(recipe_id: str, overrides: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    _load_dotenv()
    manifest = _manifest()
    recipe = next((item for item in manifest["recipes"] if item["id"] == recipe_id), None)
    if recipe is None:
        return 2, {"status": "error", "error": f"unknown recipe {recipe_id}"}
    dry_run = os.environ.get("GRIDICS_DRY_RUN") == "1"
    fixture = os.environ.get("GRIDICS_FIXTURE_MODE") == "1"
    base_url = os.environ.get("GRIDICS_API_BASE_URL", manifest["api"]["default_base_url"])
    api_key = os.environ.get("GRIDICS_API_KEY", "")
    if not dry_run and not api_key:
        return 2, {"status": "error", "error": "GRIDICS_API_KEY is required; see README.md#get-an-api-key"}
    variables = _variables(manifest, overrides)
    results = []
    failed = False
    location_session = str(uuid.uuid4())
    for raw_step in recipe["steps"]:
        step = _substitute(raw_step, variables)
        if recipe_id == "18":
            step = _location_step(step, results, variables, location_session)
            if step is None: continue
        if recipe_id == "17":
            try: step = _appraiser_step(step, results, variables)
            except ValueError as error:
                results.append({"name": step["name"], "status": "error", "error": str(error)})
                failed = True
                break
        if recipe_id == "11" and step["name"] == "candidates" and not dry_run:
            fields = (results[0].get("data") or {}).get("data", [])
            available = any(field.get("name") == "development.max_buildable_area" and field.get("caller_available") is True and field.get("selectable") is True for field in fields)
            if not available:
                results.append({"name": step["name"], "status": "unavailable", "http_status": None, "request_sent": False, "data": {"messages": ["capacity_fields unavailable"]}})
                continue
        result = _request(base_url, api_key, step, dry_run)
        if recipe_id == "18" and api_key: result = json.loads(json.dumps(result).replace(api_key, "[REDACTED]"))
        if recipe_id == "18": result["session_token"] = None if step["name"] == "forward" else location_session
        if result["status"] == "error":
            if step.get("optional") and result.get("http_status") == 403:
                result["status"] = "unavailable"
            else:
                failed = True
        results.append(result)
        if failed:
            break
        if recipe_id == "06" and result["status"] == "ok" and not dry_run:
            seen: set[str] = set()
            cursor = result.get("data", {}).get("pagination", {}).get("next_cursor")
            row_count = len(result.get("data", {}).get("data", []))
            page = 1
            while cursor and cursor not in seen and page < 3 and row_count < 100:
                seen.add(cursor); page += 1
                next_step = json.loads(json.dumps(step))
                next_step["name"] = f"page_{page}"
                next_step.setdefault("body", {})["cursor"] = cursor
                next_result = _request(base_url, api_key, next_step, False)
                results.append(next_result)
                if next_result["status"] != "ok": failed = True; break
                row_count += len(next_result.get("data", {}).get("data", []))
                cursor = next_result.get("data", {}).get("pagination", {}).get("next_cursor")
    output = {
        "status": "error" if failed else "ok",
        "recipe": recipe_id,
        "title": recipe["title"],
        "execution": "dry_run" if dry_run else "fixture" if fixture else "live",
        "api_base_url": base_url,
        "request_count": sum(1 for item in results if item["status"] != "dry_run" and item.get("request_sent") is not False),
        "results": results,
    }
    workflow = _workflow(recipe_id, results)
    if workflow is not None: output["workflow"] = workflow
    return (1 if failed else 0), output


TOOLS = [
    ("gridics_verify_credential", "Verify the server-side Gridics API key", "01", {}),
    ("gridics_list_counties", "List entitled counties in a Market", "02", {"market_id": {"type": "string"}}),
    ("gridics_lookup_property", "Look up one property in an entitled county", "03", {"place_id": {"type": "string"}, "address": {"type": "string"}, "postal_code": {"type": "string"}}),
    ("gridics_search_parcels", "Run a bounded simple county parcel search", "05", {"place_id": {"type": "string"}}),
    ("gridics_get_zoning", "Get zoning for one known parcel", "04", {"market_id": {"type": "string"}, "place_id": {"type": "string"}, "parcel_id": {"type": "string"}}),
]


def _mcp_response(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "gridics-api-cookbook", "version": "1.0.0"}}
    elif method == "tools/list":
        result = {"tools": [{"name": name, "description": description, "inputSchema": {"type": "object", "properties": schema, "additionalProperties": False}} for name, description, _, schema in TOOLS]}
    elif method == "tools/call":
        params = request.get("params") or {}
        tool = next((item for item in TOOLS if item[0] == params.get("name")), None)
        if tool is None:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "unknown or disallowed tool"}}
        code, output = execute(tool[2], params.get("arguments") or {})
        result = {"content": [{"type": "text", "text": json.dumps(output, separators=(",", ":"))}], "structuredContent": output, "isError": code != 0}
    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def mcp_server() -> int:
    for line in sys.stdin:
        try:
            response = _mcp_response(json.loads(line))
            if response is not None:
                print(json.dumps(response, separators=(",", ":")), flush=True)
        except Exception as error:  # keep protocol errors bounded and key-free
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(error)}}), flush=True)
    return 0


def main(recipe_id: str) -> int:
    if "--mcp" in sys.argv:
        return mcp_server()
    code, output = execute(recipe_id)
    print(json.dumps(output, indent=2, sort_keys=True))
    return code

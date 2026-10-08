#!/usr/bin/env python3
"""Synthetic Gridics V2 fixture server. It never proxies a live request."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

FIXTURE_KEY = "fixture_key_not_secret"


class Handler(BaseHTTPRequestHandler):
    server_version = "GridicsCookbookFixture/1.0"

    def log_message(self, *_args):
        return

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("x-request-id", "fixture-request-001")
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def _authorized(self) -> bool:
        if self.headers.get("x-api-key") == FIXTURE_KEY:
            return True
        self._json(401, {"status": "ERROR", "messages": ["invalid fixture API key"]})
        return False

    def do_GET(self):
        if not self._authorized():
            return
        path = urlparse(self.path).path
        if path.startswith('/v2/locations/'):
            query = parse_qs(urlparse(self.path).query)
            context = {'country': {'name': 'United States', 'country_code': 'US'}, 'region': {'name': 'Example State', 'region_code': 'EX'}, 'county': {'id': 'place_example_county', 'name': 'Example County'}}
            suggestion = {'name': '100 Example Ave', 'gridics_id': 'fixture-location-001', 'full_address': '100 Example Ave, Example City', 'place_formatted': 'Example City, Example State', 'feature_type': 'address', 'matched_by': 'apn' if query.get('q', [''])[0].startswith('000') else 'address', 'context': context}
            if path.endswith('/suggest'):
                self._json(200, {'suggestions': [suggestion], 'response_id': 'fixture-request-001'})
            else:
                properties = dict(suggestion, parcel_id='parcel_example_001', apn='000000000001')
                self._json(200, {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-80.0, 25.0]}, 'properties': properties}], 'response_id': 'fixture-request-001'})
        elif path == "/v2/me":
            self._json(200, {"data": {"principal_type": "api_key", "organization_id": "org_fixture", "capabilities": ["standard_parcel_access", "parcel_search", "zoning_query"]}, "meta": {"request_id": "fixture-request-001"}})
        elif path == "/v2/market-catalog":
            self._json(200, {"data": [{"id": "market_example", "name": "Example State", "availability": "available"}], "meta": {"next_cursor": None, "request_id": "fixture-request-001"}})
        elif path == "/v2/markets":
            self._json(200, {"data": [{"id": "market_example", "name": "Example State"}], "meta": {"next_cursor": None, "request_id": "fixture-request-001"}})
        elif path == "/v2/markets/market_example/places":
            self._json(200, {"data": [{"id": "place_example_county", "name": "Example County", "place_type": "county", "market_id": "market_example"}], "meta": {"next_cursor": None, "request_id": "fixture-request-001"}})
        elif path == "/v2/parcels/search-fields":
            self._json(200, {"data": [
                {"name": "parcel.id", "filterable": True, "selectable": True, "availability": "enabled"},
                {"name": "parcel.address", "filterable": True, "selectable": True, "availability": "enabled"},
                {"name": "parcel.lot_area", "filterable": True, "selectable": True, "sortable": True, "units": ["sqft", "acre"], "availability": "market_dependent"},
                {"name": "development.max_buildable_area", "filterable": True, "selectable": True, "availability": "enabled" if getattr(self.server, "capacity_available", False) else "not_yet_proven", "caller_available": getattr(self.server, "capacity_available", False), "required_capability": "capacity_fields"}
            ], "meta": {"request_id": "fixture-request-001"}})
        else:
            self._json(404, {"status": "ERROR", "messages": ["fixture route not found"]})

    def do_POST(self):
        if not self._authorized():
            return
        path = urlparse(self.path).path
        body = self._body()
        if path == "/v2/parcels/lookup":
            if body.get("place_id") != "place_example_county":
                self._json(404, {"status": "ERROR", "messages": [f"parcel not found in requested fixture county {body.get('place_id')}"]})
                return
            self._json(200, {"data": {"id": "parcel_example_001", "group_id": "parcel_example_001", "place_id": "place_example_county", "market_ids": ["market_example"], "apn": str(body.get("apn") or "000000000001"), "address": "100 Example Ave", "lot_area": 7500, "vacant": True, "zoning_code": "EX-1"}, "meta": {"request_id": "fixture-request-001", "restricted_by_entitlement": True}})
        elif path == "/v2/parcels/simple-search":
            if body.get("filters", {}).get("minimum_lot_area_sqft") is not None:
                self._json(422, {"status": "ERROR", "messages": ["field_not_available"]})
                return
            cursor = body.get("cursor")
            parcel_id = "parcel_example_002" if cursor == "fixture-page-2" else "parcel_example_001"
            next_cursor = None if cursor == "fixture-page-2" else "fixture-page-2"
            self._json(200, {"data": [{"id": parcel_id, "place_id": "place_example_county", "apn": "000000000002" if cursor else "000000000001", "address": "200 Example Ave" if cursor else "100 Example Ave", "lot_area": 9000 if cursor else 7500, "vacant": True, "zoning_code": "EX-1"}], "pagination": {"next_cursor": next_cursor, "has_more": next_cursor is not None}, "meta": {"request_id": "fixture-request-001", "restricted_by_entitlement": True}})
        elif path == "/v2/parcels/search":
            if body.get("sort"):
                self._json(422, {"status": "ERROR", "messages": ["sort_not_available"]})
                return
            if any(item.get("field") == "parcel.lot_area" for item in body.get("filters", {}).get("all", [])):
                self._json(422, {"status": "ERROR", "messages": ["field_not_available"]})
                return
            if "development.max_buildable_area" in body.get("fields", []):
                self.server.capacity_search_requests = getattr(self.server, "capacity_search_requests", 0) + 1
                if not getattr(self.server, "capacity_available", False):
                    self._json(403, {"status": "ERROR", "messages": ["capacity_fields capability is not available"]})
                    return
            self._json(200, {"data": [{"id": "parcel_example_001", "place_id": "place_example_county", "address": "100 Example Ave", "lot_area": 7500, "zoning_code": "EX-1"}], "meta": {"request_id": "fixture-request-001", "next_cursor": None, "total": None}})
        elif path == "/v2/zoning/query":
            if getattr(self.server, "zoning_failure_status", 0):
                self._json(self.server.zoning_failure_status, {"status": "ERROR", "messages": ["synthetic optional request failure"]})
                return
            self._json(200, {"data": {"group_id": body.get("group_id", "parcel_example_001"), "id": "zoning_fixture_001", "calculation_status": "complete", "updated_at": "2026-09-15T00:00:00Z", "buildings": []}, "meta": {"request_id": "fixture-request-001", "market_id": body.get("market_id"), "place_id": body.get("place_id")}})
        else:
            self._json(404, {"status": "ERROR", "messages": ["fixture route not found"]})


def start(port: int = 0) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return server


if __name__ == "__main__":
    server = start(8765)
    print("fixture API listening on http://127.0.0.1:8765", flush=True)
    server.serve_forever()

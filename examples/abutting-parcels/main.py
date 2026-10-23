"""Retrieve abutting parcel zoning and directions using only the public API."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


def fetch_abutting(base_url: str, api_key: str, parcel_id: str, place_id: str) -> dict:
    origin = urlsplit(base_url)
    if origin.scheme != "https" or not origin.netloc or origin.username or origin.password:
        raise ValueError("GRIDICS_API_BASE_URL must be an HTTPS URL without embedded credentials")
    if origin.query or origin.fragment:
        raise ValueError("GRIDICS_API_BASE_URL must not contain a query or fragment")
    if not api_key or not parcel_id or not place_id:
        raise ValueError("Set GRIDICS_API_KEY, GRIDICS_PARCEL_ID, and GRIDICS_PLACE_ID")
    path = f"/v2/parcels/{quote(parcel_id, safe='')}/abutting"
    url = base_url.rstrip("/") + path + "?" + urlencode({"place_id": place_id})
    request = Request(url, headers={"x-api-key": api_key, "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def summarize(payload: dict) -> dict:
    parcel = payload["data"]
    return {
        "parcel_id": parcel["identity"]["id"],
        "resource_state": payload["meta"]["resource_states"]["abutting"],
        "abutting": [
            {
                "parcel_id": neighbor["identity"]["id"],
                "centroid": neighbor["identity"].get("centroid"),
                "direction": neighbor["identity"].get("direction"),
                "bearing_degrees": neighbor["identity"].get("bearing_degrees"),
                "direction_state": neighbor["identity"]["direction_state"],
                "zoning_state": neighbor["zoning_state"],
                "zoning": [building.get("zoning") for building in neighbor["buildings"]],
            }
            for neighbor in parcel["abutting"]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", action="store_true", help="Use synthetic data without network access")
    args = parser.parse_args()
    try:
        payload = (
            json.loads(Path(__file__).with_name("response.json").read_text())
            if args.fixture
            else fetch_abutting(
                os.getenv("GRIDICS_API_BASE_URL", "https://api.gridics.com"),
                os.getenv("GRIDICS_API_KEY", ""),
                os.getenv("GRIDICS_PARCEL_ID", ""),
                os.getenv("GRIDICS_PLACE_ID", ""),
            )
        )
        print(json.dumps(summarize(payload), indent=2))
        return 0
    except HTTPError as error:
        # Never print credentials, request headers or raw upstream error bodies.
        print(json.dumps({"error": "API request failed", "status": error.code}))
    except (URLError, TimeoutError):
        print(json.dumps({"error": "API request failed or timed out"}))
    except (ValueError, KeyError, TypeError) as error:
        print(json.dumps({"error": "Invalid configuration or unexpected response", "type": type(error).__name__}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

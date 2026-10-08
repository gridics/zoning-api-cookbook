"""Bounded discovery of caller-authorized cookbook inputs; never log API bodies."""
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid

calls = []
values = {}
samples = []
shapes = {}


def request(path, body=None):
    if len(calls) >= 10:
        raise ValueError('Ten-request discovery budget exhausted')
    req = urllib.request.Request('https://api.gridics.com' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'x-api-key': os.environ['GRIDICS_API_KEY'], 'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            calls.append({'path': path, 'http_status': response.status})
            return json.load(response)
    except urllib.error.HTTPError as error:
        calls.append({'path': path, 'http_status': error.code})
        raise ValueError('Public API request returned HTTP ' + str(error.code)) from None


def rows(payload):
    data = payload.get('data', [])
    if isinstance(data, dict):
        data = data.get('items', [])
    if not isinstance(data, list):
        raise ValueError('Unexpected public list envelope')
    return data


def shape(value, depth=0):
    if depth > 4:
        return type(value).__name__
    if isinstance(value, dict):
        return {key: shape(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [shape(value[0], depth + 1)] if value else []
    return type(value).__name__


def main():
    if os.environ.get('GRIDICS_VERIFICATION_PROFILE') != 'public-cookbook-test':
        raise ValueError('Dedicated test profile is required')
    if not os.environ.get('GRIDICS_API_KEY'):
        raise ValueError('Environment API key is missing')
    request('/v2/me')
    markets = rows(request('/v2/markets?page_size=100'))
    if os.environ.get('GRIDICS_MARKET_NAME_HINT'):
        markets = [m for m in markets if m.get('name', '').casefold() == os.environ['GRIDICS_MARKET_NAME_HINT'].casefold()]
    if not markets:
        raise ValueError('Test key has no returned entitled markets')
    market = str(markets[0]['id'])
    places = rows(request('/v2/markets/' + urllib.parse.quote(market, safe='') + '/places?page_size=100'))
    if os.environ.get('GRIDICS_PLACE_NAME_HINT'):
        normalize = lambda name: re.sub(r'[^a-z0-9]', '', name.casefold())
        places = [p for p in places if normalize(p.get('name', '')) == normalize(os.environ['GRIDICS_PLACE_NAME_HINT'])]
    if not places:
        raise ValueError('Selected market has no returned entitled places')
    place = str(places[0]['id'])
    shapes['geography'] = {'market_name': markets[0].get('name'), 'place_name': places[0].get('name')}
    values.update(GRIDICS_MARKET_ID=market, GRIDICS_PLACE_ID=place)
    if os.environ.get('GRIDICS_ADDRESS_HINT') and os.environ.get('GRIDICS_POSTAL_CODE_HINT'):
        found = request('/v2/parcels/lookup', {'place_id': place, 'address': {'street': os.environ['GRIDICS_ADDRESS_HINT'], 'postal_code': os.environ['GRIDICS_POSTAL_CODE_HINT']}})
        parcels = [found.get('data', {})]
    else:
        search = request('/v2/parcels/simple-search', {'place_ids': [place], 'page_size': 3})
        shapes['search'] = shape(search)
        parcels = rows(search)
    if not parcels:
        raise ValueError('Selected place returned no parcels')
    for parcel in parcels[:1]:
        if parcel.get('id'):
            parcel = request('/v2/parcels/lookup', {'place_id': place, 'parcel_id': str(parcel['id'])}).get('data', {})
        shapes['parcel'] = shape(parcel)
        fields = parcel.get('fields') or {}
        address = fields.get('parcel.address') or parcel.get('address')
        apn = fields.get('parcel.apn') or (parcel.get('identifiers') or {}).get('apn') or parcel.get('apn')
        postal = parcel.get('postal_code') or parcel.get('zip_code') or fields.get('parcel.postal_code')
        if isinstance(address, dict):
            postal = postal or address.get('postal_code')
            address = address.get('full_address') or address.get('formatted') or address.get('street_address') or address.get('address')
        if isinstance(address, list):
            address = address[0] if len(address) == 1 else None
        postal = postal or os.environ.get('GRIDICS_POSTAL_CODE_HINT')
        if not postal and isinstance(address, str):
            match = re.search(r'\b(\d{5})(?:-\d{4})?\s*(?:USA|US)?\s*$', address)
            postal = match.group(1) if match else None
        samples.append({'parcel_id': parcel.get('id'), 'address': address, 'apn': apn, 'postal_code': postal})
        if not (parcel.get('id') and address and apn and postal):
            continue
        candidate = str(parcel['id'])
        found = request('/v2/parcels/lookup', {'place_id': place, 'address': {'street': address, 'postal_code': str(postal)}}).get('data', {})
        if str(found.get('id')) != candidate or found.get('place_id') != place:
            continue
        if found.get('market_ids') != [market]:
            continue
        by_apn = request('/v2/parcels/lookup', {'place_id': place, 'apn': str(apn)}).get('data', {})
        if str(by_apn.get('id')) != candidate:
            continue
        values.update(GRIDICS_PARCEL_ID=candidate, GRIDICS_APN=str(apn), GRIDICS_ADDRESS=address,
            GRIDICS_POSTAL_CODE=str(postal), GRIDICS_LOCATION_QUERY=address,
            GRIDICS_LOCATION_MODE='suggest_retrieve', GRIDICS_LOCATION_LIMIT='5',
            GRIDICS_LOCATION_COUNTRY='US', GRIDICS_LOCATION_LANGUAGE='en',
            GRIDICS_VERIFICATION_PROFILE='public-cookbook-test')
        if os.environ.get('GRIDICS_VERIFY_ZONING_HINT') == 'true':
            zoning = request('/v2/zoning/query', {'market_id': market, 'place_id': place, 'group_id': candidate})
            shapes['zoning'] = shape(zoning)
        query = address + ', ' + str(postal)
        values['GRIDICS_LOCATION_QUERY'] = query
        token = str(uuid.uuid4())
        suggestions = request('/v2/locations/suggest?' + urllib.parse.urlencode({'q': query, 'limit': 5, 'country': 'US', 'language': 'en', 'session_token': token})).get('suggestions', [])
        if not suggestions or not suggestions[0].get('gridics_id'):
            raise ValueError('Property inputs verified, but Location Search returned no usable suggestion')
        location = request('/v2/locations/retrieve/' + urllib.parse.quote(suggestions[0]['gridics_id'], safe='') + '?' + urllib.parse.urlencode({'session_token': token}))
        features = location.get('features', [])
        if not any(str((feature.get('properties') or {}).get('parcel_id')) == candidate for feature in features):
            raise ValueError('Property inputs verified, but Location Search did not confirm the same parcel')
        return
    raise ValueError('No complete address/APN/postal-code match was verified in the bounded parcel sample')


if __name__ == '__main__':
    failure = None
    try:
        main()
    except (ValueError, KeyError, urllib.error.URLError, TimeoutError) as error:
        failure = str(error) if isinstance(error, ValueError) else type(error).__name__
    output = {'verified': failure is None, 'values': values, 'requests': calls, 'failure': failure, 'samples': samples, 'response_shapes': shapes}
    encoded = json.dumps(output, indent=2)
    secret = os.environ.get('GRIDICS_API_KEY', '')
    if secret and secret in encoded:
        raise SystemExit('Credential material detected; refusing to save output')
    path = Path('reports/discovery/test-values.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded + '\n')
    print('Discovery completed' if failure is None else 'Discovery blocked: ' + failure)
    raise SystemExit(0 if failure is None else 1)

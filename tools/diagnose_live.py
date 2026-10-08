"""Inspect public field availability and bounded request errors without retaining facts."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'languages/python'))
sys.path.insert(0, str(ROOT / 'tools'))
import gridics_cookbook as cookbook
from verify_live import validate_environment

validate_environment(dict(os.environ))
variables = cookbook._variables(cookbook._manifest())
key = os.environ['GRIDICS_API_KEY']

def safe(value):
    text = json.dumps(value)
    for secret in [key] + [v for k, v in variables.items() if k in {'GRIDICS_MARKET_ID', 'GRIDICS_PLACE_ID', 'GRIDICS_PARCEL_ID', 'GRIDICS_APN', 'GRIDICS_ADDRESS', 'GRIDICS_POSTAL_CODE', 'GRIDICS_LOCATION_QUERY'}]:
        if secret:
            text = text.replace(secret, '[REDACTED]')
    return json.loads(text)

results = []
for recipe_id in ['04', '05', '08', '09', '18']:
    _, payload = cookbook.execute(recipe_id)
    steps = []
    for result in payload['results']:
        entry = {'step': result['name'], 'status': result['status'], 'http_status': result.get('http_status')}
        data = result.get('data') or {}
        if result['status'] == 'error':
            entry['messages'] = safe(data.get('messages', []))
            # Public validation errors only: never retain echoed request inputs.
            detail = data.get('details')
            if isinstance(detail, list):
                entry['validation'] = [safe({k: x[k] for k in ['loc', 'type', 'msg'] if k in x}) for x in detail if isinstance(x, dict)]
            elif isinstance(detail, dict):
                entry['detail_keys'] = list(detail)
        if result['name'] == 'fields' and result['status'] == 'ok':
            entry['public_fields'] = safe(data)
        steps.append(entry)
    results.append({'recipe': recipe_id, 'steps': steps})
# Isolate projection, filter, and sort availability with three bounded public searches.
recipe = next(r for r in cookbook._manifest()['recipes'] if r['id'] == '08')
base = cookbook._substitute(recipe['steps'][1], variables)
for name, filters, sort in [('projection_only', None, []), ('vacancy_filter', base['body']['filters'], []), ('lot_area_sort', None, base['body']['sort'])]:
    step = json.loads(json.dumps(base))
    step['max_attempts'] = 1
    step['body']['filters'] = filters
    step['body']['sort'] = sort
    step['body']['page_size'] = 1
    result = cookbook._request('https://api.gridics.com', key, step, False)
    results.append({'probe': name, 'http_status': result.get('http_status'), 'messages': safe((result.get('data') or {}).get('messages', []))})
path = ROOT / 'reports/live/diagnostics.json'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({'cookbook_revision': os.environ.get('GITHUB_SHA'), 'results': results}, indent=2) + '\n')
print('Saved redacted public-contract diagnostics')

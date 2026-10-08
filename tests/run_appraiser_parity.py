#!/usr/bin/env python3
"""Complete recipe-17 report parity against synthetic public V2 fixtures."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from datetime import datetime
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse

from fixture_api import FIXTURE_KEY, Handler
from run_fixture_smoke import command

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / 'fixtures/appraiser-zoning-cases.json').read_text())['cases']


class AppraiserHandler(Handler):
    def do_POST(self):
        if not self._authorized():
            return
        path = urlparse(self.path).path
        body = self._body()
        self.server.requests.append({'path': path, 'body': body})
        case = self.server.case
        if path == '/v2/parcels/lookup':
            # Parse exactly one public locator; APN remains a string with leading zero.
            assert sum(k in body for k in ['address', 'apn', 'parcel_id', 'coordinates']) == 1
            if case['locator'] == 'apn': assert body['apn'] == '000000000001'
            if case['locator'] == 'parcel_id': assert body['parcel_id'] == 'input-parcel-advanced'
            if case['locator'] == 'address': assert body['address'] == {'street':'100 Example Ave','postal_code':'00000'}
            self._json(case['lookup_status'], case['lookup_response'])
        elif path == '/v2/zoning/query':
            # The intentionally unrelated configured parcel/market must never be queried.
            assert body == {'group_id':'parcel_returned_017','place_id':'place_example_county','market_id':'market_returned_017'}
            assert case['zoning_status'] is not None
            self._json(case['zoning_status'], case['zoning_response'])
        else:
            self._json(404, {'messages':['unexpected fixture operation']})

    def _json(self, status, payload):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('x-request-id',payload['meta']['request_id'])
        self.end_headers()
        self.wfile.write(raw)


def verify_report(report, expected):
    copy = dict(report)
    retrieved = copy.pop('retrieved_at')
    assert datetime.fromisoformat(retrieved.replace('Z','+00:00')).tzinfo is not None
    assert copy == expected, f'Appraiser report mismatch: {copy}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--language',required=True,choices=['python','nodejs','typescript','php','csharp','java','go'])
    args=parser.parse_args()
    recipe={'id':'17','slug':'appraiser-zoning-lookup'}
    cmd,cwd=command(args.language,recipe)
    with tempfile.TemporaryDirectory(prefix='appraiser-java-') as build:
        if args.language=='java':
            subprocess.run(['javac','-d',build,str(ROOT/'languages/java/GridicsCookbook.java'),'Main.java'],cwd=cwd,check=True,timeout=120)
            cmd=['java','-cp',build,'Main']
        for case in CASES:
            server=ThreadingHTTPServer(('127.0.0.1',0),AppraiserHandler)
            server.requests=[];server.case=case
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            env=os.environ.copy()
            env.update(GRIDICS_API_KEY=FIXTURE_KEY,GRIDICS_FIXTURE_MODE='1',GRIDICS_DRY_RUN='0',GRIDICS_API_BASE_URL=f'http://127.0.0.1:{server.server_port}',GRIDICS_LOCATOR=case['locator'],GRIDICS_ADDRESS='100 Example Ave',GRIDICS_POSTAL_CODE='00000',GRIDICS_APN='000000000001',GRIDICS_PLACE_ID='unauthorized-county' if case['name']=='wrong_county' else 'place_example_county',GRIDICS_MARKET_ID='unrelated-input-market',GRIDICS_PARCEL_ID='input-parcel-advanced')
            try:
                output=subprocess.run(cmd,cwd=cwd,env=env,text=True,capture_output=True,timeout=120)
                assert FIXTURE_KEY not in output.stdout+output.stderr, 'Credential was exposed'
                payload=json.loads(output.stdout)
                expected_error=case['lookup_status']!=200
                assert output.returncode==(1 if expected_error else 0),output.stderr+output.stdout
                assert payload['status']==('error' if expected_error else 'ok')
                assert payload['request_count']==case['expected_requests']
                assert len(server.requests)==case['expected_requests'], 'Unbounded/hidden retry or extra page'
                assert payload['execution']=='fixture'
                verify_report(payload['workflow'],case['expected_report'])
                print(f'{args.language} appraiser {case["name"]}: parity passed')
            finally:
                server.shutdown();server.server_close()
    return 0


if __name__=='__main__':
    raise SystemExit(main())

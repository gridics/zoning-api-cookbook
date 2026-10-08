#!/usr/bin/env python3
"""Seven-language Location Search parity; synthetic loopback only."""
import argparse, json, os, subprocess, tempfile, threading, uuid
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from fixture_api import Handler, FIXTURE_KEY
from run_fixture_smoke import command
ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'fixtures/location-search-cases.json').read_text())['cases']
class LocationHandler(Handler):
 def _json(self,status,payload):
  if self.server.case=='ambiguous' and 'features' in payload:payload['features'].append(dict(payload['features'][0],properties=dict(payload['features'][0]['properties'],parcel_id='parcel_example_002')))
  super()._json(status,payload)
 def do_GET(self):
  if not self._authorized():return
  path=urlparse(self.path).path;query={k:v[0] for k,v in parse_qs(urlparse(self.path).query).items()};self.server.requests.append((path,query))
  if self.server.status!=200 and (self.server.case!='tampered' or '/retrieve/' in path):self._json(self.server.status,{'code':self.server.case,'messages':['Synthetic public error '+FIXTURE_KEY],'response_id':'fixture-request-001'});return
  if path.endswith('/suggest') and self.server.case=='empty':self._json(200,{'suggestions':[],'response_id':'fixture-request-001'});return
  super().do_GET()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--language',required=True);args=parser.parse_args();cmd,cwd=command(args.language,{'id':'18','slug':'location-search'})
 with tempfile.TemporaryDirectory() as build:
  if args.language=='java':subprocess.run(['javac','-d',build,str(ROOT/'languages/java/GridicsCookbook.java'),'Main.java'],cwd=cwd,check=True);cmd=['java','-cp',build,'Main']
  for name,query,mode,status in CASES:
   server=ThreadingHTTPServer(('127.0.0.1',0),LocationHandler);server.requests=[];server.case=name;server.status=status;threading.Thread(target=server.serve_forever,daemon=True).start()
   env=dict(os.environ,GRIDICS_FIXTURE_MODE='1',GRIDICS_DRY_RUN='0',GRIDICS_API_BASE_URL=f'http://127.0.0.1:{server.server_port}',GRIDICS_API_KEY=FIXTURE_KEY,GRIDICS_LOCATION_QUERY=query,GRIDICS_LOCATION_MODE=mode,GRIDICS_LOCATION_PROXIMITY='-80,25',GRIDICS_LOCATION_BBOX='-81,24,-79,26',GRIDICS_LOCATION_COUNTRY='US',GRIDICS_LOCATION_LANGUAGE='en',GRIDICS_LOCATION_LIMIT='5')
   try:
    run=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True,timeout=120);assert run.returncode==(0 if status==200 else 1),run.stderr+run.stdout
    output=json.loads(run.stdout[run.stdout.find('{'):]);report=output['workflow'];assert report['kind']=='location_search' and report['mode']==mode
    assert FIXTURE_KEY not in run.stdout and 'x-api-key": "fixture' not in run.stdout
    assert report['state']==('error' if status!=200 else 'no_match' if name=='empty' else 'ambiguous' if name=='ambiguous' else 'resolved')
    assert len(server.requests)==(3 if name=='tampered' else 1 if status!=200 or mode=='forward' else 2 if name=='empty' else 3),server.requests
    for path,q in server.requests:
     assert 'place_id' not in q
     if not '/retrieve/' in path:assert q['q']==query and q['proximity']=='-80,25' and q['bbox']=='-81,24,-79,26' and q['country']=='US' and q['language']=='en' and q['limit']=='5'
    if mode!='forward':
     sessions={q['session_token'] for _,q in server.requests};assert report['session_token']==next(iter(sessions));assert len(sessions)==1;assert uuid.UUID(next(iter(sessions))).version==4
    if status==200 and name!='empty':
     assert report['features'][0]['type']=='Feature';assert report['features'][0]['properties']['context']['county']=={'id':'place_example_county','name':'Example County'}
     assert report['features'][0]['properties']['apn']=='000000000001';assert report['features'][0]['geometry']['coordinates']==[-80,25]
     if name=='apn':assert report['suggestions'][0]['matched_by']=='apn'
    print(f'{args.language} location {name}: ok')
   finally:server.shutdown();server.server_close()
if __name__=='__main__':main()

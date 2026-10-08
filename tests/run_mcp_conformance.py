#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from fixture_api import FIXTURE_KEY, start

ROOT = Path(__file__).resolve().parents[1]


def command(language: str) -> tuple[list[str], Path, tempfile.TemporaryDirectory | None]:
    directory = ROOT / "recipes/16-mcp-tools" / language
    temp = None
    if language == "python": return [sys.executable, "main.py", "--mcp"], directory, temp
    if language == "nodejs": return ["node", "main.mjs", "--mcp"], directory, temp
    if language == "typescript": return ["node", str(ROOT / "dist/recipes/16-mcp-tools/typescript/main.js"), "--mcp"], directory, temp
    if language == "php": return ["php", "main.php", "--mcp"], directory, temp
    if language == "go": return ["go", "run", ".", "--mcp"], directory, temp
    if language == "csharp": return ["dotnet", "run", "--", "--mcp"], directory, temp
    temp = tempfile.TemporaryDirectory(prefix="gridics-mcp-java-")
    built = subprocess.run(["javac", "-d", temp.name, str(ROOT / "languages/java/GridicsCookbook.java"), "Main.java"], cwd=directory, text=True, capture_output=True)
    if built.returncode: raise RuntimeError(built.stderr)
    return ["java", "-cp", temp.name, "Main", "--mcp"], directory, temp


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--language", required=True); args = parser.parse_args()
    server = start(0); threading.Thread(target=server.serve_forever, daemon=True).start()
    env = os.environ.copy(); env.update({"GRIDICS_API_KEY":FIXTURE_KEY,"GRIDICS_API_BASE_URL":f"http://127.0.0.1:{server.server_port}","GRIDICS_FIXTURE_MODE":"1","GRIDICS_PLACE_ID":"place_example_county","GRIDICS_MARKET_ID":"market_example","GRIDICS_PARCEL_ID":"parcel_example_001"})
    cmd,cwd,temp=command(args.language)
    messages = [
        {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"fixture","version":"1"}}},
        {"jsonrpc":"2.0","method":"notifications/initialized"},
        {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}},
        {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"gridics_verify_credential","arguments":{}}},
        {"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"gridics_arbitrary_proxy","arguments":{"path":"/internal"}}},
        {"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"gridics_lookup_property","arguments":{"place_id":"place_custom_input","address":"100 Example Ave","postal_code":"00000"}}},
    ]
    result=subprocess.run(cmd,cwd=cwd,env=env,input="\n".join(json.dumps(item,separators=(",",":")) for item in messages)+"\n",text=True,capture_output=True,timeout=120)
    if temp: temp.cleanup()
    server.shutdown();server.server_close()
    if result.returncode: print(result.stderr);return 1
    responses=[json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    by_id={item.get("id"):item for item in responses}
    tools=by_id[2]["result"]["tools"]
    names={tool["name"] for tool in tools}
    expected={"gridics_verify_credential","gridics_list_counties","gridics_lookup_property","gridics_search_parcels","gridics_get_zoning"}
    assertions=[by_id[1]["result"]["serverInfo"]["name"]=="gridics-api-cookbook",names==expected,by_id[3]["result"]["isError"] is False,by_id[4]["error"]["code"]==-32602,by_id[5]["result"]["isError"] is True,"place_custom_input" in json.dumps(by_id[5]),FIXTURE_KEY not in result.stdout+result.stderr,all("x-api-key" not in json.dumps(tool) for tool in tools)]
    if not all(assertions): print(json.dumps(responses,indent=2));return 1
    print(f"{args.language}: MCP initialize, tool schemas, bounded call, rejection, and secret redaction passed")
    return 0


if __name__ == "__main__": raise SystemExit(main())

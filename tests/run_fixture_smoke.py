#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import tempfile
from pathlib import Path

from fixture_api import FIXTURE_KEY, start

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "recipes/manifest.json").read_text())


def command(language: str, recipe: dict) -> tuple[list[str], Path]:
    directory = ROOT / "recipes" / f"{recipe['id']}-{recipe['slug']}" / language
    commands = {
        "python": [sys.executable, "main.py"],
        "nodejs": ["node", "main.mjs"],
        "typescript": ["node", str(ROOT / "dist" / "recipes" / f"{recipe['id']}-{recipe['slug']}" / "typescript" / "main.js")],
        "php": ["php", "main.php"],
        "csharp": ["dotnet", "run"],
        "java": ["java", "Main"],
        "go": ["go", "run", "."],
    }
    return commands[language], directory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", required=True, choices=["python", "nodejs", "typescript", "php", "csharp", "java", "go"])
    parser.add_argument("--recipe")
    args = parser.parse_args()
    server = start(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = os.environ.copy()
    env.update({"GRIDICS_API_KEY": FIXTURE_KEY, "GRIDICS_API_BASE_URL": f"http://127.0.0.1:{server.server_port}", "GRIDICS_FIXTURE_MODE": "1", "GRIDICS_DRY_RUN": "0", "GRIDICS_MARKET_ID": "market_example", "GRIDICS_PLACE_ID": "place_example_county", "GRIDICS_PARCEL_ID": "parcel_example_001"})
    selected = [item for item in manifest["recipes"] if not args.recipe or item["id"] == args.recipe]
    failures = []
    try:
        for recipe in selected:
            cmd, cwd = command(args.language, recipe)
            java_build = None
            if args.language == "java":
                java_build = tempfile.TemporaryDirectory(prefix="gridics-java-")
                compile_result = subprocess.run(["javac", "-d", java_build.name, str(ROOT / "languages/java/GridicsCookbook.java"), "Main.java"], cwd=cwd, env=env, text=True, capture_output=True, timeout=120)
                if compile_result.returncode != 0:
                    failures.append({"recipe": recipe["id"], "code": compile_result.returncode, "stdout": compile_result.stdout[-1000:], "stderr": compile_result.stderr[-1000:]})
                    java_build.cleanup()
                    continue
                cmd = ["java", "-cp", java_build.name, "Main"]
            result = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=120)
            if recipe["id"] == "13":
                for status in [404, 422, 500]:
                    server.zoning_failure_status = status
                    negative = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=120)
                    negative_payload = json.loads(negative.stdout)
                    if negative.returncode == 0 or negative_payload["results"][-1]["status"] != "error" or negative_payload["results"][-1].get("http_status") != status:
                        failures.append({"recipe": "13", "case": f"optional-{status}", "error": "optional error was hidden"})
                server.zoning_failure_status = 0
            if recipe["id"] == "11":
                if getattr(server, "capacity_search_requests", 0):
                    failures.append({"recipe": "11", "error": "unavailable capacity search was sent"})
                server.capacity_available = True
                enabled = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=120)
                enabled_payload = json.loads(enabled.stdout)
                if enabled.returncode or enabled_payload["results"][-1]["status"] != "ok" or enabled_payload["request_count"] != 2 or getattr(server, "capacity_search_requests", 0) != 1:
                    failures.append({"recipe": "11", "error": "available capacity search did not execute"})
                server.capacity_available = False
                server.capacity_search_requests = 0
            if java_build is not None: java_build.cleanup()
            try: payload = json.loads(result.stdout)
            except json.JSONDecodeError: payload = None
            expected_names = ["page_1", "page_2"] if recipe["id"] == "06" else [step["name"] for step in recipe["steps"]]
            actual_results = payload.get("results", []) if isinstance(payload, dict) else []
            parity_ok = (
                [item.get("name") for item in actual_results] == expected_names
                and payload.get("request_count") == len(expected_names) - (1 if recipe["id"] == "11" else 0)
                and all(item.get("status") in {"ok", "unavailable"} for item in actual_results)
                and all((item.get("http_status") in {200, 403} or (recipe["id"] == "11" and item.get("request_sent") is False)) for item in actual_results)
                and all("data" in item for item in actual_results)
                and (recipe["id"] not in {"06", "10", "11", "12", "13", "14", "15", "17"} or isinstance(payload.get("workflow"), dict))
            )
            if result.returncode != 0 or not isinstance(payload, dict) or payload.get("status") != "ok" or payload.get("execution") != "fixture" or not parity_ok or FIXTURE_KEY in result.stdout + result.stderr:
                failures.append({"recipe": recipe["id"], "code": result.returncode, "stdout": result.stdout[-1000:], "stderr": result.stderr[-1000:]})
            else:
                print(f"{args.language} recipe {recipe['id']}: ok")
    finally:
        server.shutdown(); server.server_close()
    if failures:
        print(json.dumps(failures, indent=2)); return 1
    print(f"{args.language}: {len(selected)} fixture recipes passed")
    return 0


if __name__ == "__main__": raise SystemExit(main())

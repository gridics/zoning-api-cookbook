"""Bounded production Public API acceptance; retain metadata, never response bodies or keys."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ["python", "nodejs", "typescript", "php", "csharp", "java", "go"]


def validate_environment(env: dict[str, str]) -> None:
    required = ["GRIDICS_API_KEY", "GRIDICS_API_BASE_URL", "GRIDICS_VERIFICATION_PROFILE"]
    missing = [name for name in required if not env.get(name)]
    if missing:
        raise ValueError("Missing protected configuration: " + ", ".join(missing))
    if env["GRIDICS_VERIFICATION_PROFILE"] != "public-cookbook-test":
        raise ValueError("Protected environment is not the dedicated cookbook verification profile")
    url = urlsplit(env["GRIDICS_API_BASE_URL"])
    if (
        url.scheme != "https"
        or url.hostname != "api.gridics.com"
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in {"", "/"}
    ):
        raise ValueError("Live verification must use the production public API origin")


def summarize(payload: dict, recipe: str, secret: str, expected_parcel_id: str | None = None) -> dict:
    if secret in json.dumps(payload):
        raise ValueError("Recipe returned credential material")
    if payload.get("execution") != "live" or payload.get("recipe") != recipe:
        raise ValueError("Recipe did not produce the selected live execution")
    count = payload.get("request_count")
    results = payload.get("results")
    if not isinstance(count, int) or not 1 <= count <= 6 or not isinstance(results, list) or not results:
        raise ValueError("Recipe evidence exceeded the bounded request contract")
    steps = []
    for item in results:
        state = item.get("status")
        if state not in {"ok", "unavailable"}:
            raise ValueError("A required live recipe step failed")
        steps.append({"status": state, "http_status": item.get("http_status")})
    if payload.get("status") != "ok":
        raise ValueError("Live recipe did not pass")
    if recipe == "18":
        workflow = payload.get("workflow") or {}
        features = workflow.get("features")
        if workflow.get("state") != "resolved" or not isinstance(features, list) or len(features) != 1:
            raise ValueError("Location Search did not resolve one property")
        properties = features[0].get("properties") or {}
        if not properties.get("parcel_id") or (expected_parcel_id and properties["parcel_id"] != expected_parcel_id):
            raise ValueError("Location Search did not match the approved test property")
    return {
        "recipe": recipe,
        "request_count": count,
        "steps": steps,
        "result_status": "capability_unavailable" if any(s["status"] == "unavailable" for s in steps) else "verified",
    }


def missing_fixture_variables(recipe: dict, env: dict[str, str]) -> list[str]:
    required = set(re.findall(r"\$\{(GRIDICS_[A-Z_]+)\}", json.dumps(recipe["steps"])))
    return sorted(name for name in required if not env.get(name))


def failure_metadata(raw: str, recipe: str) -> dict:
    evidence = {"recipe": recipe, "result_status": "failed"}
    try:
        payload = json.loads(raw)
        results = payload.get("results", []) if isinstance(payload, dict) else []
        evidence["http_statuses"] = [
            item["http_status"] for item in results[:6]
            if isinstance(item, dict)
            and type(item.get("http_status")) is int
            and 100 <= item["http_status"] <= 599
        ]
    except (ValueError, TypeError):
        pass
    return evidence


def command(language: str, recipe: dict, build_dir: str) -> tuple[list[str], Path]:
    directory = ROOT / "recipes" / f"{recipe['id']}-{recipe['slug']}" / language
    commands = {
        "python": [sys.executable, "main.py"],
        "nodejs": ["node", "main.mjs"],
        "typescript": ["node", str(ROOT / "dist/recipes" / directory.parent.name / "typescript/main.js")],
        "php": ["php", "main.php"],
        "csharp": ["dotnet", "run"],
        "go": ["go", "run", "."],
        "java": ["java", "-cp", build_dir, "Main"],
    }
    if language == "java":
        compiled = subprocess.run(
            ["javac", "-d", build_dir, str(ROOT / "languages/java/GridicsCookbook.java"), "Main.java"],
            cwd=directory, capture_output=True, timeout=120
        )
        if compiled.returncode:
            raise ValueError("Java compilation failed; no API request sent")
    return commands[language], directory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", required=True, choices=LANGUAGES)
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    env = dict(os.environ)
    validate_environment(env)
    env.update(GRIDICS_DRY_RUN="0", GRIDICS_FIXTURE_MODE="0")

    manifest = json.loads((ROOT / "recipes/manifest.json").read_text())
    selected = [r for r in manifest["recipes"] if args.recipe == "all" or r["id"] == args.recipe]
    if not selected:
        raise ValueError("Unknown recipe")

    evidence = {
        "environment": "production",
        "language": args.language,
        "api_base_url": "https://api.gridics.com",
        "cookbook_revision": env.get("GITHUB_SHA"),
        "workflow_run": env.get("GITHUB_RUN_ID"),
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "contract_source": manifest["api"].get("contract_source", "contracts/openapi-v2.json"),
        "results": [],
        "passed": False,
    }

    try:
        for recipe in selected:
            missing = missing_fixture_variables(recipe, env)
            if missing:
                evidence["results"].append(
                    {"recipe": recipe["id"], "result_status": "configuration_missing", "missing_variables": missing}
                )
                continue
            raw = ""
            try:
                with tempfile.TemporaryDirectory(prefix="gridics-live-") as build:
                    cmd, directory = command(args.language, recipe, build)
                    result = subprocess.run(cmd, cwd=directory, env=env, capture_output=True, text=True, timeout=120)
                    raw = result.stdout
                    if result.returncode:
                        raise ValueError("Recipe process failed")
                    evidence["results"].append(
                        summarize(json.loads(result.stdout), recipe["id"], env["GRIDICS_API_KEY"], env.get("GRIDICS_PARCEL_ID"))
                    )
            except (ValueError, subprocess.TimeoutExpired):
                evidence["results"].append(failure_metadata(raw, recipe["id"]))

        evidence["passed"] = all(r["result_status"] == "verified" for r in evidence["results"])
        return 0 if evidence["passed"] else 1
    finally:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, subprocess.TimeoutExpired) as exc:
        print(
            "Protected live verification failed: "
            + ("invalid JSON output" if isinstance(exc, json.JSONDecodeError) else str(exc)),
            file=sys.stderr,
        )
        raise SystemExit(1)

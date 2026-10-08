#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "recipes/manifest.json").read_text())
languages = {"python": "main.py", "nodejs": "main.mjs", "typescript": "main.ts", "php": "main.php", "csharp": "Program.cs", "java": "Main.java", "go": "main.go"}
errors: list[str] = []

if len(manifest["recipes"]) != 18:
    errors.append(f"expected 18 recipes, got {len(manifest['recipes'])}")

for recipe in manifest["recipes"]:
    directory = ROOT / "recipes" / f"{recipe['id']}-{recipe['slug']}"
    readme = directory / "README.md"
    if not readme.exists(): errors.append(f"missing {readme.relative_to(ROOT)}")
    for language, filename in languages.items():
        target = directory / language / filename
        if not target.exists() or target.stat().st_size < 20: errors.append(f"missing or empty {target.relative_to(ROOT)}")

required_readme = ["Get an API key", "https://developer.gridics.com/get-started", "Workspace → API Keys", "x-api-key", "GRIDICS_API_KEY", "Language support"]
readme_text = (ROOT / "README.md").read_text()
for phrase in required_readme:
    if phrase not in readme_text: errors.append(f"README missing {phrase!r}")

for required in [".env.example", ".gitignore", "LICENSE", "SECURITY.md", "SUPPORT.md", "CONTRIBUTING.md", "NOTICE", "docs/compatibility.md", "docs/request-reference.md"]:
    if not (ROOT / required).exists(): errors.append(f"missing {required}")

for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts or path.name == "validate_repository.py": continue
    try: text = path.read_text()
    except UnicodeDecodeError: continue
    if re.search(r"gk_[A-Za-z0-9_-]{16,}", text): errors.append(f"possible live Gridics key in {path.relative_to(ROOT)}")
    for banned in ["state_env", "raw Solr", "gapi_id"]:
        if banned in text and path.suffix not in {".md"}: errors.append(f"private implementation term {banned!r} in executable {path.relative_to(ROOT)}")

count = sum(1 for recipe in manifest["recipes"] for language in languages if (ROOT / "recipes" / f"{recipe['id']}-{recipe['slug']}" / language / languages[language]).exists())
if count != 126: errors.append(f"expected 126 language entry points, got {count}")

if errors:
    print("Repository validation failed:")
    print("\n".join(f"- {item}" for item in errors))
    sys.exit(1)
print(f"Repository validation passed: {len(manifest['recipes'])} recipes, {len(languages)} languages, {count} entry points.")

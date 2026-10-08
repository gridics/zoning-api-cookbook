"""Fail closed when the checked-in distribution contains non-public or sensitive material."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {
    "", ".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".py", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".go", ".java", ".cs",
    ".php", ".sh", ".bash", ".html", ".css", ".xml", ".csv", ".env", ".example",
}

PUBLIC_GRIDICS_HOSTS = {
    "api.gridics.com",
    "developer.gridics.com",
    "gridics.com",
    "www.gridics.com",
}

PUBLIC_GRIDICS_GITHUB_REPOS = {
    "gridics/zoning-api-cookbook",
}

SECRET_PATTERNS = {
    "Gridics API key": re.compile(r"\bgk_[A-Za-z0-9_-]{16,}\b"),
    "Gridics publishable key": re.compile(r"\bgpk_(?!test_REPLACE_ME\b|test_SYNTHETIC\b)[A-Za-z0-9_-]{16,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "JWT-like credential": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
}

SUSPICIOUS_DEPENDENCY_MARKERS = (
    "npm.pkg.github.com",
    "NODE_AUTH_TOKEN",
    "GRIDICS_NPM_TOKEN",
    "packages: read",
)

SUSPICIOUS_OPERATIONAL_MARKERS = (
    "GRIDICS_API_IMAGE_DIGEST",
    "GRIDICS_API_REVISION",
)


def tracked_files() -> list[Path]:
    names = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    return [ROOT / name for name in names if (ROOT / name).is_file()]


def read_text(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
        "Dockerfile", "Makefile", "LICENSE", "NOTICE", ".gitignore"
    }:
        return None
    try:
        return path.read_text()
    except UnicodeDecodeError:
        return None


def check_gridics_links(path: Path, text: str, problems: list[str]) -> None:
    for match in re.finditer(r"https?://[^\s)>'\"]+", text):
        raw = match.group(0).rstrip(".,;")
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()

        if host.endswith(".gridics.com") or host == "gridics.com":
            if host not in PUBLIC_GRIDICS_HOSTS:
                problems.append(f"{path.relative_to(ROOT)}: non-public Gridics hostname")

        if host == "github.com":
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2 and parts[0].lower() == "gridics":
                repo = f"{parts[0]}/{parts[1].removesuffix('.git')}"
                if repo not in PUBLIC_GRIDICS_GITHUB_REPOS:
                    problems.append(f"{path.relative_to(ROOT)}: non-public/unapproved Gridics GitHub link")


def validate() -> None:
    problems: list[str] = []

    package_files = (
        "package.json",
        "package-lock.json",
        "examples/react-location-search/package.json",
        "examples/react-location-search/package-lock.json",
        "examples/react-zoning-explorer/package.json",
        "examples/react-zoning-explorer/package-lock.json",
    )
    for name in package_files:
        data = (ROOT / name).read_text()
        json.loads(data)

    for path in tracked_files():
        rel = path.relative_to(ROOT)
        parts = set(rel.parts)
        if {"node_modules", "dist", "build"} & parts or str(rel).endswith((".tgz", ".tar.gz", ".zip")):
            problems.append(f"{rel}: generated package/archive is tracked")

        text = read_text(path)
        if text is None:
            continue

        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                problems.append(f"{rel}: possible {label}")

        if rel != Path("tests/validate_public_distribution.py"):
            if any(marker in text for marker in SUSPICIOUS_DEPENDENCY_MARKERS):
                problems.append(f"{rel}: private/authenticated dependency marker")

            if any(marker.lower() in text.lower() for marker in SUSPICIOUS_OPERATIONAL_MARKERS):
                problems.append(f"{rel}: internal deployment/source metadata marker")

        check_gridics_links(path, text, problems)

    for example in ("react-location-search", "react-zoning-explorer"):
        if (ROOT / f"examples/{example}/.npmrc").exists():
            problems.append(f"examples/{example}/.npmrc: registry configuration must not be required")

    if problems:
        unique = sorted(set(problems))
        raise SystemExit("Public distribution validation failed:\n" + "\n".join(f"- {p}" for p in unique))

    print("Public distribution validation passed: public-only Gridics links/dependencies, no tracked archives, and no detected credentials.")


if __name__ == "__main__":
    validate()

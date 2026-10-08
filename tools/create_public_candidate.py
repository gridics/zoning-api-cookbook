#!/usr/bin/env python3
"""Export the approved HEAD into a fresh-history public candidate working tree."""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VALIDATORS = (
    ("tests/validate_repository.py",),
    ("tests/validate_public_distribution.py",),
    ("tests/validate_contract.py",),
)


def run(*args: str, cwd: Path = ROOT, capture: bool = False) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        check=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def require_clean_head() -> str:
    status = run("git", "status", "--porcelain=v1", "--untracked-files=all", capture=True)
    if status:
        raise SystemExit(
            "Refusing to export a candidate from a dirty working tree. "
            "Commit or remove all tracked/untracked changes first."
        )
    return run("git", "rev-parse", "HEAD", capture=True)


def validate(root: Path) -> None:
    for command in VALIDATORS:
        run(sys.executable, *command, cwd=root)


def safe_extract(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r") as bundle:
        for member in bundle.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise SystemExit(f"Unsafe archive member: {member.name}")
            if member.issym() or member.islnk():
                raise SystemExit(
                    f"Public candidate export does not permit symlinks/hardlinks: {member.name}"
                )
        bundle.extractall(destination)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a public-candidate working tree from committed HEAD only, "
            "with a new empty Git history."
        )
    )
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    source_sha = require_clean_head()
    validate(ROOT)

    destination = args.destination.expanduser().resolve()
    root_resolved = ROOT.resolve()
    if destination == root_resolved or root_resolved in destination.parents:
        raise SystemExit("Destination must be outside the source repository.")
    if destination.exists():
        raise SystemExit(f"Destination already exists: {destination}")

    destination.mkdir(parents=True)
    try:
        with tempfile.TemporaryDirectory(prefix="gridics-public-candidate-") as temp_dir:
            archive = Path(temp_dir) / "candidate.tar"
            run("git", "archive", "--format=tar", f"--output={archive}", "HEAD")
            safe_extract(archive, destination)

        run("git", "init", "--quiet", "-b", "main", cwd=destination)
        run("git", "add", "--all", cwd=destination)
        validate(destination)

        tracked = run("git", "ls-files", capture=True, cwd=destination).splitlines()
        if (destination / ".git").exists() is False:
            raise SystemExit("Candidate Git repository was not initialized.")

        print(f"Public candidate prepared from source SHA: {source_sha}")
        print(f"Destination: {destination}")
        print(f"Staged files: {len(tracked)}")
        print("Inherited commits: 0")
        print("")
        print("Next:")
        print(f"  cd {destination}")
        print("  git status --short")
        print('  git commit -m "Initial public release"')
        print("  # Push only this fresh main branch to the new private gridics/zoning-api-cookbook repository.")
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


if __name__ == "__main__":
    main()

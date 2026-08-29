#!/usr/bin/env python3
"""Validate Fynvo release metadata consistency without external services."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ROADMAP_RELEASE = re.compile(r"^## v\d+\.\d+\.\d+ - .+$", re.MULTILINE)


def fail(message: str) -> None:
    raise SystemExit(message)


def backend_version() -> str:
    path = ROOT / "fynvo/backend/app/config.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    fail("Could not find string APP_VERSION in fynvo/backend/app/config.py")
    raise AssertionError("unreachable")


def require_version_entry(text: str, version: str, label: str) -> None:
    patterns = (
        rf"^## v{re.escape(version)}(?:\s|$)",
        rf"^## \[{re.escape(version)}\](?:\s|$)",
        rf"^## {re.escape(version)}(?:\s|$)",
    )
    if not any(re.search(pattern, text, re.MULTILINE) for pattern in patterns):
        fail(f"{label} does not contain a release heading for {version}")


def main() -> None:
    manifest_path = ROOT / "fynvo/config.yaml"
    frontend_path = ROOT / "fynvo/frontend/package.json"
    root_changelog_path = ROOT / "CHANGELOG.md"
    addon_changelog_path = ROOT / "fynvo/CHANGELOG.md"
    roadmap_path = ROOT / "ROADMAP.md"
    main_path = ROOT / "fynvo/backend/app/main.py"

    required_paths = (
        manifest_path,
        frontend_path,
        root_changelog_path,
        addon_changelog_path,
        roadmap_path,
        main_path,
    )
    missing = [str(path.relative_to(ROOT)) for path in required_paths if not path.is_file()]
    if missing:
        fail(f"Missing required release metadata files: {', '.join(missing)}")

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    frontend = json.loads(frontend_path.read_text(encoding="utf-8"))

    expected = str(manifest.get("version") or "")
    if not SEMVER.fullmatch(expected):
        fail(f"Home Assistant manifest version '{expected}' is not semantic X.Y.Z format")

    frontend_version = str(frontend.get("version") or "")
    if frontend_version != expected:
        fail(
            f"Frontend version {frontend_version or '<missing>'} does not match "
            f"Home Assistant version {expected}"
        )

    backend = backend_version()
    if backend != expected:
        fail(f"Backend APP_VERSION {backend} does not match Home Assistant version {expected}")

    main_source = main_path.read_text(encoding="utf-8")
    if 'from .config import APP_VERSION' not in main_source:
        fail("Backend API must import APP_VERSION from app.config")
    health_match = re.search(
        r'@app\.get\(["\']/api/health["\']\).*?def\s+health\s*\([^)]*\).*?return\s*\{(?P<body>.*?)\}',
        main_source,
        re.DOTALL,
    )
    if not health_match or '"version": APP_VERSION' not in health_match.group("body"):
        fail("/api/health must expose version from APP_VERSION")

    require_version_entry(root_changelog_path.read_text(encoding="utf-8"), expected, "Root CHANGELOG.md")
    require_version_entry(addon_changelog_path.read_text(encoding="utf-8"), expected, "Home Assistant CHANGELOG.md")

    roadmap = roadmap_path.read_text(encoding="utf-8")
    if not ROADMAP_RELEASE.search(roadmap):
        fail("ROADMAP.md has no parser-friendly planned release heading like '## v1.17.0 - Release Name'")
    if not re.search(r"^## Future\s*$", roadmap, re.MULTILINE):
        fail("ROADMAP.md is missing the required '## Future' section")
    if not re.search(r"^Status:\s*Planned\s*$", roadmap, re.MULTILINE):
        fail("ROADMAP.md has no planned release status")
    if "- [ ]" not in roadmap:
        fail("ROADMAP.md has no task-list deliverables")

    print(f"Fynvo release metadata is consistent for {expected}")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== Backend: compile =="
python -m compileall fynvo/backend/app

echo "== Backend: Ruff =="
python -m ruff check --ignore DTZ011 fynvo/backend/app fynvo/backend/tests

echo "== Backend: tests =="
PYTHONPATH=fynvo/backend python -m pytest fynvo/backend/tests

echo "== Backend: import application =="
PYTHONPATH=fynvo/backend python -c "from app.main import app; print(app.title)"

echo "== Frontend: tests =="
(
  cd fynvo/frontend
  npm test
  npm run build
)

echo "== Home Assistant metadata =="
python - <<'PY'
import json
import re
from pathlib import Path

import yaml

for path in (Path("repository.yaml"), Path("fynvo/config.yaml"), Path("fynvo/build.yaml")):
    with path.open("r", encoding="utf-8") as handle:
        yaml.safe_load(handle)
    print(f"Validated {path}")

with Path("fynvo/config.yaml").open("r", encoding="utf-8") as handle:
    config = yaml.safe_load(handle)
with Path("fynvo/frontend/package.json").open("r", encoding="utf-8") as handle:
    package = json.load(handle)

required = ["name", "version", "slug", "description", "arch", "startup", "boot"]
missing = [key for key in required if key not in config]
if missing:
    raise SystemExit(f"Missing required config.yaml keys: {', '.join(missing)}")
version = str(config.get("version") or "")
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    raise SystemExit("config.yaml version must use semantic version format")
if package.get("version") != version:
    raise SystemExit(f"Version mismatch: {version} != {package.get('version')}")
if config.get("slug") != "fynvo" or config.get("ingress_port") != 8097:
    raise SystemExit("Home Assistant app metadata is inconsistent")
print(f"Home Assistant app metadata looks valid for Fynvo {version}")
PY

echo "== Docker build =="
docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20 -t fynvo-ci fynvo

echo "All CI-equivalent checks passed."

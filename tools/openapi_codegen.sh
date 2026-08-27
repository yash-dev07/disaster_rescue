#!/usr/bin/env bash
# Generates a Python client from docs/openapi.yaml, as specified in
# project_brief.md Section 6. Run from the repo root:
#   ./tools/openapi_codegen.sh
# Requires Java + the openapi-generator-cli (or the npm wrapper below).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

npx @openapitools/openapi-generator-cli generate \
  -i docs/openapi.yaml \
  -g python \
  -o build/clients/python \
  --additional-properties=packageName=floodrescue_client

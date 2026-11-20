#!/usr/bin/env bash
# Render one API/environment using native decK environment substitutions.
set -euo pipefail
set +x
umask 077
export DECK_ANALYTICS=false
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
: "${PYTHON:=python3}"
[[ $# == 3 ]] || { echo 'Usage: bash scripts/build.sh API ENV OUTPUT_DIRECTORY' >&2; exit 2; }
api=$1; environment=$2; output=$3
# Require explicit decK 1.70.0; no silent tool drift.
deck version | grep -Eq 'v1\.70\.0([[:space:]]|$)' || { echo 'Install pinned decK 1.70.0' >&2; exit 2; }
mkdir -p "$output"
variables=$(mktemp)
trap 'rm -f "$variables"' EXIT
"$PYTHON" scripts/validate.py env "$api" "$environment" > "$variables"
# No eval/source of YAML. Export only the validator allow-listed DECK_ variables.
while IFS= read -r -d '' key && IFS= read -r -d '' value; do export "$key=$value"; done < "$variables"
# JSON quoting preserves the entire OpenAPI document as one YAML string, including newlines.
# Derived from the API contract, never entered separately in environment values.
DECK_OPENAPI_SPEC=$("$PYTHON" -c 'import json,pathlib,sys; print(json.dumps(pathlib.Path(sys.argv[1]).read_text()))' "apis/$api/openapi.yaml")
export DECK_OPENAPI_SPEC
deck file render --config "$ROOT/config/deck.yaml" --populate-env-vars "apis/$api/kong.yaml" -o "$output/state.yaml"
"$PYTHON" scripts/validate.py scope "$api" "$output/state.yaml"
deck file validate --config "$ROOT/config/deck.yaml" "$output/state.yaml"
"$PYTHON" scripts/validate.py state "$api" "$environment" "$output/state.yaml" --draft

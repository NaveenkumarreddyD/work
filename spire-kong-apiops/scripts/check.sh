#!/usr/bin/env bash
# Credential-free checks: suitable for merge requests on isolated validation agents.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
: "${PYTHON:=python3}"
"$PYTHON" -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"'
"$PYTHON" -m unittest discover -s tests -v
"$PYTHON" scripts/validate.py source
for api_dir in apis/*; do
  [[ -d "$api_dir" ]] || continue
  for environment in dev uat training preprod prod; do
    bash scripts/build.sh "${api_dir##*/}" "$environment" "build/check/${api_dir##*/}/$environment"
  done
done
for script in scripts/*.sh; do bash -n "$script"; done
echo 'Offline checks passed. Live plugin schema, credential, DP and runtime checks are still required.'

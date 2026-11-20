#!/usr/bin/env bash
# Functional HTTP tests through the gateway. No redirect following with bearer credentials.
set -euo pipefail
set +x
umask 077
ROOT=$(cd "$(dirname "$0")/.." && pwd)
: "${PYTHON:=python3}"
[[ $# == 4 ]] || { echo 'Usage: verify.sh PACKAGE API ENV EVIDENCE_DIRECTORY' >&2; exit 2; }
package=$1; api=$2; environment=$3; evidence=$4
: "${SMOKE_BEARER_TOKEN:?Bind a valid API-specific test token}"
: "${EXPECTED_CP:?}"; : "${EXPECTED_ADDR:?}"
"$PYTHON" "$ROOT/scripts/release.py" verify "$package" "$api" "$environment" "$EXPECTED_CP" "$EXPECTED_ADDR" >/dev/null
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
# Header file prevents bearer token disclosure through process command-line arguments.
[[ "$SMOKE_BEARER_TOKEN" =~ ^[A-Za-z0-9._~+/=-]+$ ]] || { echo 'Invalid bearer token format' >&2; exit 2; }
printf 'Authorization: Bearer %s\n' "$SMOKE_BEARER_TOKEN" > "$scratch/valid-header"
printf 'Authorization: Bearer deliberately-invalid-test-token\n' > "$scratch/invalid-header"
: > "$scratch/none-header"
"$PYTHON" - "$package" "$environment" > "$scratch/tests" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); env=sys.argv[2]
gateway=json.loads((p/'manifest.json').read_text())['environments'][env]['gateway_url'].rstrip('/')
for test in json.loads((p/'tests.json').read_text()):
    for value in (test['name'],test['method'],gateway+test['path'],test['auth'],str(test['expected_status']),test['body_contains']):
        if '\0' in value: raise SystemExit('NUL in test definition')
        sys.stdout.buffer.write(value.encode()+b'\0')
PY
: > "$evidence/http-tests.txt"
count=0
while IFS= read -r -d '' name && IFS= read -r -d '' method && IFS= read -r -d '' url && IFS= read -r -d '' auth && IFS= read -r -d '' expected && IFS= read -r -d '' contains; do
  actual=$(curl --silent --show-error --connect-timeout 5 --max-time 20 --request "$method" --header "@$scratch/$auth-header" --output "$scratch/body" --write-out '%{http_code}' "$url")
  printf '%s: actual=%s expected=%s\n' "$name" "$actual" "$expected" >> "$evidence/http-tests.txt"
  [[ "$actual" == "$expected" ]] || { echo "HTTP test failed: $name" >&2; exit 1; }
  if [[ -n "$contains" ]]; then grep -Fq -- "$contains" "$scratch/body" || { echo "Body assertion failed: $name" >&2; exit 1; }; fi
  count=$((count+1))
done < "$scratch/tests"
[[ "$count" -ge 3 ]] || { echo 'At least three positive/negative tests required' >&2; exit 1; }
printf 'Passed %s HTTP tests; node/site convergence still requires platform verification.\n' "$count" >> "$evidence/http-tests.txt"

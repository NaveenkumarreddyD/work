#!/usr/bin/env bash
set -euo pipefail
set +x
: "${SMOKE_BEARER_TOKEN:?Trusted test token required from Jenkins credentials}"
: "${STATE_MANIFEST:?Path to manifest required}"
mapfile -t TEST < <(python3 - "$STATE_MANIFEST" <<'PY'
import json,sys
from urllib.parse import urljoin
m=json.load(open(sys.argv[1]))
print(m['gateway_url'].rstrip('/')+m['smoke_path'])
print(m['smoke_expected_status'])
PY
)
actual=$(curl --silent --show-error --location --max-time 20 --output /dev/null --write-out '%{http_code}' --header "Authorization: Bearer ${SMOKE_BEARER_TOKEN}" "${TEST[0]}")
if [[ "$actual" != "${TEST[1]}" ]]; then echo "Smoke test failed: HTTP $actual expected ${TEST[1]}" >&2;exit 1;fi
echo "Authenticated smoke test succeeded: HTTP ${actual}"

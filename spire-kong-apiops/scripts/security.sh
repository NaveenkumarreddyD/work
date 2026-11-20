#!/usr/bin/env bash
# Pin the official scanner. Redact findings; never archive unredacted secrets.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
gitleaks version | grep -Eq '^8\.30\.1$' || { echo 'Install approved Gitleaks 8.30.1' >&2; exit 2; }
mkdir -p evidence/security
gitleaks dir . --redact --no-banner --report-format json --report-path evidence/security/gitleaks.json

#!/usr/bin/env bash
# Called only from a trusted Jenkins agent after checkout, approval and policy checks.
set -euo pipefail
set +x
umask 077
: "${DEPLOY_ACTION:?DEPLOY_ACTION required: plan|deploy|drift|backup}"
: "${TARGET_ENV:?TARGET_ENV missing}"
: "${API_NAME:?API_NAME missing}"
: "${DECK_KONNECT_TOKEN:?Konnect token not bound from Jenkins}"
: "${BACKUP_ALLOWED:=false}"
STATE="build/${TARGET_ENV}-${API_NAME}.yaml"
python3 scripts/kong_config.py --api "$API_NAME" --env "$TARGET_ENV" --strict --out "$STATE"
python3 - "$STATE" <<'PY_CHECK'
import json,sys,hashlib,pathlib
p=pathlib.Path(sys.argv[1]);m=json.loads(p.with_suffix('.manifest.json').read_text())
assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256'], 'State artifact checksum mismatch'
print('Artifact checksum verified')
PY_CHECK
# Read only approved metadata from manifest; do not eval arbitrary YAML.
mapfile -t META < <(python3 - "$STATE" <<'PY_META'
import json,pathlib,sys
m=json.loads(pathlib.Path(sys.argv[1]).with_suffix('.manifest.json').read_text())
for key in ('control_plane','konnect_addr'):
 print(m[key])
PY_META
)
export DECK_KONNECT_CONTROL_PLANE_NAME="${META[0]}"
export DECK_KONNECT_ADDR="${META[1]}"
mkdir -p build
LOG="build/${TARGET_ENV}-${API_NAME}-diff.txt"
case "$DEPLOY_ACTION" in
  plan|deploy|drift)
    deck gateway ping
    deck file validate --konnect-compatibility "$STATE"
    deck gateway validate "$STATE"
    deck gateway diff "$STATE" | tee "$LOG"
    if [[ "$DEPLOY_ACTION" == drift ]]; then exit 0; fi
    if [[ "$DEPLOY_ACTION" == plan ]]; then exit 0; fi
    if grep -Eq 'Deleted: [1-9][0-9]*' "$LOG" && [[ "${ALLOW_DELETIONS:-false}" != true ]]; then
      echo 'Deletion detected. Explicit ALLOW_DELETIONS=true and elevated approval required.' >&2;exit 20
    fi
    if [[ "$BACKUP_ALLOWED" == true ]]; then
      # Only on explicitly approved high-risk changes; keep artifact encrypted outside Jenkins workspace.
      : "${BACKUP_DIR:?Secure restricted backup directory required}"
      mkdir -p "$BACKUP_DIR"
      chmod 700 "$BACKUP_DIR"
      deck gateway dump --select-tag "owner-${API_NAME}" -o "$BACKUP_DIR/${TARGET_ENV}-${API_NAME}-prechange-${BUILD_NUMBER:-manual}-$(date -u +%Y%m%dT%H%M%SZ).yaml"
      chmod 600 "$BACKUP_DIR/${TARGET_ENV}-${API_NAME}-prechange-${BUILD_NUMBER:-manual}-$(date -u +%Y%m%dT%H%M%SZ).yaml"
    fi
    deck gateway sync "$STATE" --yes
    deck gateway diff "$STATE" | tee "build/${TARGET_ENV}-${API_NAME}-postdiff.txt"
    python3 scripts/assert_no_diff.py "build/${TARGET_ENV}-${API_NAME}-postdiff.txt"
    ;;
  backup)
    : "${BACKUP_DIR:?Secure restricted backup directory required}"
    mkdir -p "$BACKUP_DIR"
    deck gateway dump --select-tag "owner-${API_NAME}" -o "$BACKUP_DIR/${TARGET_ENV}-${API_NAME}-scheduled.yaml"
    chmod 600 "$BACKUP_DIR/${TARGET_ENV}-${API_NAME}-scheduled.yaml"
    ;;
  *) echo "Unknown action $DEPLOY_ACTION" >&2;exit 2;;
esac

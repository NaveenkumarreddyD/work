#!/usr/bin/env bash
# Run only on trusted deploy agents. Jenkins holds the Control Plane lock for all phases.
set -euo pipefail
set +x
umask 077
ROOT=$(cd "$(dirname "$0")/.." && pwd)
: "${PYTHON:=python3}"
[[ $# == 5 ]] || { echo 'Usage: deploy.sh plan|apply|auto-dev|drift|backup PACKAGE API ENV EVIDENCE_DIRECTORY' >&2; exit 2; }
phase=$1; package=$2; api=$3; environment=$4; evidence=$5
case "$phase" in plan|apply|auto-dev|drift|backup) ;; *) exit 2;; esac
: "${EXPECTED_CP:?Set trusted expected Control Plane name}"
: "${EXPECTED_ADDR:?Set trusted expected Konnect regional address}"
: "${DECK_KONNECT_TOKEN:?Bind environment-specific Jenkins credential}"
# Do not inherit select-tags, workspaces, addresses, verbosity or TLS bypass from agent setup.
# Allow only the bound token and explicitly approved custom CA trust inputs.
while IFS= read -r deck_variable; do
  case "$deck_variable" in
    DECK_KONNECT_TOKEN|DECK_CA_CERT|DECK_CA_CERT_FILE) ;;
    *) unset "$deck_variable" ;;
  esac
done < <(compgen -v DECK_)
export DECK_ANALYTICS=false
export DECK_KONNECT_CONTROL_PLANE_NAME="$EXPECTED_CP"
export DECK_KONNECT_ADDR="$EXPECTED_ADDR"
deck version | grep -Eq 'v1\.70\.0([[:space:]]|$)' || exit 2
"$PYTHON" "$ROOT/scripts/release.py" verify "$package" "$api" "$environment" "$EXPECTED_CP" "$EXPECTED_ADDR" >/dev/null
if [[ "$phase" != apply && "$phase" != auto-dev ]]; then
  "$PYTHON" "$ROOT/scripts/release.py" stage "$package" "$evidence" "$api" "$environment" "$EXPECTED_CP" "$EXPECTED_ADDR"
fi
[[ -d "$evidence" && ! -L "$evidence" ]] || exit 2
# Record an outcome on success AND failure; Jenkins archives evidence in finally.
if [[ "$phase" == auto-dev ]]; then status_phase=apply; else status_phase=$phase; fi
phase_outcome=failed
finish() {
  result=$?
  # Some Bash versions report 0 to EXIT after a fatal parameter expansion in a function.
  if [[ "$phase_outcome" != success && "$result" == 0 ]]; then result=1; fi
  printf 'exit_code=%s\n' "$result" > "$evidence/$status_phase-status.txt"
  trap - EXIT
  exit "$result"
}
trap finish EXIT
state="$evidence/state.yaml"
common=(--config "$ROOT/config/deck.yaml" --konnect-control-plane-name "$EXPECTED_CP" --konnect-addr "$EXPECTED_ADDR")
# Prevent a user/home .deck.yaml or self-managed target override from changing the target.
export DECK_KONG_ADDR=http://localhost:8001
unset DECK_KONG_ADMIN_TOKEN DECK_KONG_COOKIE_JAR_PATH DECK_HEADERS DECK_TLS_SKIP_VERIFY || true
deck gateway ping "${common[@]}" > "$evidence/$phase-ping.txt" 2>&1
deck gateway validate "$state" "${common[@]}" > "$evidence/$phase-validate.txt" 2>&1
if [[ "$phase" == plan ]]; then
  deck gateway diff "$state" --json-output "${common[@]}" > "$evidence/plan.json" 2> "$evidence/plan-stderr.txt"
  "$PYTHON" "$ROOT/scripts/release.py" diff "$evidence/plan.json" --allow-deletions
  echo "Plan saved to $evidence/plan.json; no changes applied."
  phase_outcome=success
  exit 0
fi
if [[ "$phase" == drift ]]; then
  deck gateway diff "$state" --json-output "${common[@]}" > "$evidence/drift.json" 2> "$evidence/drift-stderr.txt"
  "$PYTHON" "$ROOT/scripts/release.py" diff "$evidence/drift.json" --allow-deletions --empty
  phase_outcome=success
  exit 0
fi
snapshot() {
  : "${BACKUP_DIR:?Provide enterprise encrypted backup directory}"
  [[ ${BACKUP_STORAGE_APPROVED:-false} == true ]] || { echo 'Backup encryption/access/retention must be approved externally' >&2; exit 2; }
  [[ -d "$BACKUP_DIR" && ! -L "$BACKUP_DIR" ]] || { echo 'Provision restricted backup directory first' >&2; exit 2; }
  snapshot_file="$BACKUP_DIR/$environment-$api-$(date -u +%Y%m%dT%H%M%SZ)-$$.yaml"
  deck gateway dump --select-tag "owner-$api" -o "$snapshot_file" "${common[@]}" > "$evidence/backup-status.txt" 2>&1
  [[ -s "$snapshot_file" ]] || { echo 'Empty backup; deployment stopped' >&2; exit 2; }
  chmod 600 "$snapshot_file"
  printf 'Snapshot retained outside Jenkins artifacts\n' >> "$evidence/backup-status.txt"
}
if [[ "$phase" == backup ]]; then snapshot; phase_outcome=success; exit 0; fi
if [[ "$phase" == auto-dev ]]; then
  [[ "$environment" == dev && ${TRUSTED_AUTO_DEV:-false} == true && ${ALLOW_DELETIONS:-false} == false ]] || { echo 'Automatic DEV gate rejected' >&2; exit 2; }
  "$PYTHON" "$ROOT/scripts/release.py" approve "$package" "$evidence" "$api" "$environment" "$EXPECTED_CP" "$EXPECTED_ADDR" protected-main-auto "${BUILD_NUMBER:-local-test}"
fi
"$PYTHON" "$ROOT/scripts/release.py" binding "$package" "$evidence" "$api" "$environment" "$EXPECTED_CP" "$EXPECTED_ADDR"
deck gateway diff "$state" --json-output "${common[@]}" > "$evidence/current-plan.json" 2> "$evidence/current-plan-stderr.txt"
"$PYTHON" "$ROOT/scripts/release.py" compare "$evidence/plan.json" "$evidence/current-plan.json"
if [[ ${ALLOW_DELETIONS:-false} == true ]]; then
  "$PYTHON" "$ROOT/scripts/release.py" diff "$evidence/current-plan.json" --allow-deletions
  snapshot
else
  "$PYTHON" "$ROOT/scripts/release.py" diff "$evidence/current-plan.json"
  if [[ ${TAKE_SNAPSHOT:-false} == true ]]; then snapshot; fi
fi
# Check binding again immediately before mutation; immutable artifact storage remains required.
"$PYTHON" "$ROOT/scripts/release.py" binding "$package" "$evidence" "$api" "$environment" "$EXPECTED_CP" "$EXPECTED_ADDR"
deck gateway sync "$state" --yes "${common[@]}" > "$evidence/sync.txt" 2>&1
deck gateway diff "$state" --json-output "${common[@]}" > "$evidence/postdiff.json" 2> "$evidence/postdiff-stderr.txt"
"$PYTHON" "$ROOT/scripts/release.py" diff "$evidence/postdiff.json" --allow-deletions --empty
bash "$ROOT/scripts/verify.sh" "$package" "$api" "$environment" "$evidence"
phase_outcome=success

#!/usr/bin/env bash
# Build once from the checked-out annotated tag. Never call this during deployment.
set -euo pipefail
set +x
umask 077
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
: "${PYTHON:=python3}"
[[ $# == 3 ]] || { echo 'Usage: bash scripts/release.sh TAG API OUTPUT_DIRECTORY' >&2; exit 2; }
tag=$1; api=$2; output=$3
[[ "$api" =~ ^[a-z][a-z0-9-]{2,62}$ ]] || exit 2
[[ ! -e "$output" ]] || { echo 'Never overwrite a release' >&2; exit 2; }
commit=$(git rev-parse HEAD)
if [[ "$tag" == "dev-$commit" ]]; then
  git merge-base --is-ancestor HEAD refs/remotes/origin/main
else
  [[ "$tag" =~ ^kong-v[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$ ]] || exit 2
  bash scripts/verify-source.sh "$tag" >/dev/null
  [[ $(git rev-parse "refs/tags/$tag^{commit}") == "$commit" ]] || exit 2
fi
[[ -z $(git status --porcelain --untracked-files=no) ]] || { echo 'Tracked changes prevent release' >&2; exit 2; }
mkdir -p "$output"
# A failed package has no manifest and is not deployable. Retain it for diagnostics.
for environment in dev uat training preprod prod; do
  bash scripts/build.sh "$api" "$environment" "$output/$environment"
done
"$PYTHON" scripts/release.py manifest "$output" "$api" "$tag"

#!/usr/bin/env bash
# Execute THIS copy from trusted tooling before checking out any requested release.
# Prints only the verified commit; never executes code from the candidate tag.
set -euo pipefail
[[ $# == 1 && "$1" =~ ^kong-v[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$ ]] || exit 2
tag=$1
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || { echo 'Annotated tag required' >&2; exit 2; }
commit=$(git rev-parse "refs/tags/$tag^{commit}")
git merge-base --is-ancestor "$commit" refs/remotes/origin/main || { echo 'Tag is not on fetched protected main' >&2; exit 2; }
if [[ ${REQUIRE_SIGNED_TAG:-false} == true ]]; then git verify-tag "$tag" >&2; fi
printf '%s\n' "$commit"

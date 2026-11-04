#!/usr/bin/env bash
set -euo pipefail
: "${RELEASE_TAG:?Set RELEASE_TAG to a protected annotated Git tag}"
[[ "$RELEASE_TAG" =~ ^kong-v[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$ ]] || { echo 'Invalid release tag naming' >&2;exit 1; }
git fetch --no-tags origin "refs/tags/$RELEASE_TAG:refs/tags/$RELEASE_TAG"
[[ "$(git cat-file -t "refs/tags/$RELEASE_TAG")" == tag ]] || { echo 'Annotated tag required' >&2;exit 1; }
REV=$(git rev-list -n 1 "refs/tags/$RELEASE_TAG")
git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main
if ! git merge-base --is-ancestor "$REV" refs/remotes/origin/main; then
  echo 'Release tag must point to a reviewed commit on protected main' >&2;exit 1
fi
git checkout --detach "$REV"
test "$(git rev-parse HEAD)" = "$REV"
echo "Release tag $RELEASE_TAG resolves to commit $REV"
# Require admins to protect GitLab tags, restrict creation and enforce signed tags.

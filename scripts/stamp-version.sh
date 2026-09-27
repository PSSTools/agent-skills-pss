#!/bin/bash
# Stamp src/agent_skills_pss/__about__.py with the version derived from git.
#
# Releases are tag-driven, so the source carries only a 0.0.0 placeholder and
# the version comes from the nearest v* tag:
#
#   tag build (GITHUB_REF=refs/tags/vX.Y.Z)   X.Y.Z
#   anything else                              <tag>.post<N>+<forge>.g<sha>
#                                              e.g. 0.1.0.post3+gh.g1b7503e
#
# <N> is the commit count since the tag -- the same shape as `git describe`.
# `.post<N>` sorts after the tag it builds on and before the next release. The
# `+<forge>.g<sha>` local segment names the commit and the forge that built it,
# and PyPI rejects local versions outright, so a dev build can never be
# published.
#
# Usage: scripts/stamp-version.sh <forge>     (gh | fj | local)
# Needs full history and tags (actions/checkout with fetch-depth: 0).
set -euo pipefail

forge=${1:?usage: $0 <gh|fj|local>}
about=src/agent_skills_pss/__about__.py
cd "$(dirname "$0")/.."

case "${GITHUB_REF:-}" in
  refs/tags/v*)
    version=${GITHUB_REF#refs/tags/v}
    if ! printf '%s' "$version" | grep -qE '^[0-9]+(\.[0-9]+)*((a|b|rc)[0-9]+)?$'; then
      echo "::error::tag v$version is not a release version (vX.Y.Z[aN|bN|rcN])"
      exit 1
    fi
    ;;
  *)
    sha=$(git rev-parse --short=7 HEAD)
    if desc=$(git describe --tags --long --match 'v[0-9]*' 2>/dev/null); then
      # v0.1.0-3-g1b7503e -> base 0.1.0, count 3
      base=${desc%-*-g*}; base=${base#v}
      count=${desc%-g*}; count=${count##*-}
    else
      base=0.0.0
      count=$(git rev-list --count HEAD)
    fi
    version="${base}.post${count}+${forge}.g${sha}"
    ;;
esac

sed -i 's/^__version__ = ".*"$/__version__ = "'"$version"'"/' "$about"
grep -q "^__version__ = \"$version\"\$" "$about" || { echo "::error::failed to stamp $about"; exit 1; }
echo "version: $version"

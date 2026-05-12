#!/usr/bin/env bash
# scripts/release-prep.sh
#
# Generate the input files used to compose Toshy release notes.
# Auto-detects the most recent Toshy_v* tag and writes four files
# describing the changes from that tag to HEAD into the repo root.

set -euo pipefail

# shellcheck disable=SC2034
VERSION='20260507'

# Required external command.
if ! command -v git >/dev/null 2>&1; then
    printf 'Error: required command not found: git\n' >&2
    exit 1
fi

# Must be inside a git working tree.
if ! REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    printf 'Error: not inside a git repository.\n' >&2
    exit 1
fi

cd "$REPO_ROOT"

# Find the newest Toshy_v* tag using version-aware sort.
LATEST_TAG="$(git tag --list 'Toshy_v*' --sort=-version:refname | head -n 1)"
if [[ -z "$LATEST_TAG" ]]; then
    printf "Error: no tag matching 'Toshy_v*' found.\n" >&2
    exit 1
fi

RANGE="${LATEST_TAG}..HEAD"
COMMIT_COUNT="$(git rev-list --count "$RANGE")"

printf 'Repo root : %s\n' "$REPO_ROOT"
printf 'Latest tag: %s\n' "$LATEST_TAG"
printf 'Range     : %s\n' "$RANGE"
printf 'Commits   : %s\n' "$COMMIT_COUNT"
printf '\n'

if [[ "$COMMIT_COUNT" -eq 0 ]]; then
    printf 'Warning: no commits in range; output files will be empty.\n' >&2
fi

OUT_DIR='release-prep-files'
mkdir -p "$OUT_DIR"

OUT_COMMITS="${OUT_DIR}/toshy_commits_since_last_release.txt"
OUT_MERGES="${OUT_DIR}/toshy_merges_since_last_release.txt"
OUT_DIFFSTAT="${OUT_DIR}/toshy_diff_stat.txt"
OUT_DATEDLOG="${OUT_DIR}/toshy_dated_log.txt"

# Non-merge commits (catches squash-merge PR titles too), oldest first.
printf 'Writing %s\n' "$OUT_COMMITS"
git log "$RANGE" --no-merges --reverse --format='%h %s' > "$OUT_COMMITS"

# Merge commits on the main line of history, with body for PR titles.
printf 'Writing %s\n' "$OUT_MERGES"
git log "$RANGE" --merges --first-parent --reverse \
    --format='%h %s%n    %b' > "$OUT_MERGES"

# Cumulative file change summary across the range.
printf 'Writing %s\n' "$OUT_DIFFSTAT"
git diff --stat "$RANGE" > "$OUT_DIFFSTAT"

# Same commit list with committer dates, oldest first.
printf 'Writing %s\n' "$OUT_DATEDLOG"
git log "$RANGE" --reverse --format='%cs %h %s' > "$OUT_DATEDLOG"

printf '\nDone. Files written to: %s/%s\n' "$REPO_ROOT" "$OUT_DIR"

# End of file #

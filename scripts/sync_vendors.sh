#!/usr/bin/env bash
#
# Toshy/scripts/sync_vendors.sh   (adjust path to wherever this lives in the repo)
#
# One-way vendoring of external repos into Toshy's `vendors/` folder.
#
# For each configured entry this script:
#   1. Asks the remote for the current branch SHA via `git ls-remote` (cheap probe).
#   2. Compares it to the SHA recorded in the vendored copy's `.vendored-ref`.
#   3. If (and only if) they differ, downloads that branch as a codeload tarball,
#      clears the destination folder, extracts a filtered copy, and records the SHA.
#
# Nothing is ever pushed back out. The vendored copies are generated; the upstream
# repos are the source of truth. Local edits under `vendors/` are overwritten on sync.
#
# Default is populate-only (review the diff yourself, then commit). Pass --commit to
# stage and commit the `vendors/` changes automatically.

set -euo pipefail

# shellcheck disable=SC2034
VERSION='20260712'

SCRIPT_NAME="$(basename "$0")"


#############################################################################
# Configuration
#############################################################################

# A file that must exist at the git repo root to confirm we are in the Toshy
# repo (not some other repo we happened to be standing in). Adjust if needed.
REPO_ROOT_SENTINEL='setup_toshy.py'

# Vendor table. One record per line: name|url|branch|folder|exclude,csv,list
#   name     : human label for logs
#   url      : upstream repo base URL (https://github.com/OWNER/REPO)
#   branch   : branch to track
#   folder   : destination subfolder under vendors/ (branch-tagged where relevant)
#   excludes : comma-separated top-level paths to drop after extraction
#
# NOTE: verify the xwaykeyz URL below before first run.
VENDOR_RECORDS='
kwin-application-switcher|https://github.com/RedBearAK/kwin-application-switcher|kde6_kde5_merged|kwin-application-switcher|.img
xwaykeyz-dev_beta|https://github.com/RedBearAK/xwaykeyz|dev_beta|xwaykeyz-dev_beta|tests,bin,examples,contrib,tools
xwaykeyz-main|https://github.com/RedBearAK/xwaykeyz|main|xwaykeyz-main|tests,bin,examples,contrib,tools
'


#############################################################################
# Logging
#############################################################################

info() { printf '  %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
err()  { printf 'ERROR: %s\n' "$*" >&2; }


#############################################################################
# Preconditions
#############################################################################

reject_root() {
    if [ "$(id -u)" -eq 0 ]; then
        err "Do not run ${SCRIPT_NAME} as root; it writes files into your repo."
        exit 1
    fi
}


DOWNLOAD_TOOL=''

detect_download_tool() {
    if command -v curl >/dev/null 2>&1; then
        DOWNLOAD_TOOL='curl'
    elif command -v wget >/dev/null 2>&1; then
        DOWNLOAD_TOOL='wget'
    else
        err "Neither curl nor wget is available; cannot download tarballs."
        exit 1
    fi
    info "download tool: ${DOWNLOAD_TOOL}"
}


require_commands() {
    if ! command -v git >/dev/null 2>&1; then
        err "git is required (for ls-remote and repo-root detection)."
        exit 1
    fi
    if ! command -v tar >/dev/null 2>&1; then
        err "tar is required (for archive extraction)."
        exit 1
    fi
}


# Sets REPO_ROOT_DIR and VENDORS_DIR, verified via the .git discovery that
# git rev-parse performs, plus the sentinel check.
resolve_repo_root() {
    local repo_root_path
    repo_root_path="$(git rev-parse --show-toplevel 2>/dev/null)" || repo_root_path=''
    if [ -z "$repo_root_path" ]; then
        err "Not inside a git repository (no .git found). Run from the Toshy repo."
        exit 1
    fi
    if [ ! -e "${repo_root_path}/${REPO_ROOT_SENTINEL}" ]; then
        err "Repo root '${repo_root_path}' has no '${REPO_ROOT_SENTINEL}'."
        err "Refusing to run: this does not look like the Toshy repo."
        exit 1
    fi
    REPO_ROOT_DIR="$repo_root_path"
    VENDORS_DIR="${REPO_ROOT_DIR}/vendors"
    mkdir -p -- "$VENDORS_DIR"
    info "repo root: ${REPO_ROOT_DIR}"
    info "vendors:   ${VENDORS_DIR}"
}


#############################################################################
# Safe filesystem helpers
#############################################################################

# Validate that a name is a single, safe path component (no traversal).
assert_safe_component() {
    local component_name="$1"
    if [ -z "$component_name" ]; then
        err "Internal: empty path component"
        return 1
    fi
    case "$component_name" in
        */*|.|..)
            err "Unsafe path component: '${component_name}'"
            return 1
            ;;
    esac
    return 0
}


# Clear (delete + recreate) a vendors subfolder. Every destructive path here is
# built as "${VENDORS_DIR}/<validated-name>", and both halves are asserted
# non-empty and contained, so an empty variable can never widen the target.
safe_clear_dir() {
    local folder_name="$1"
    local target_dir

    assert_safe_component "$folder_name" || return 1

    if [ -z "${VENDORS_DIR:-}" ] || [ ! -d "$VENDORS_DIR" ]; then
        err "Internal: VENDORS_DIR unset or missing: '${VENDORS_DIR:-}'"
        return 1
    fi

    target_dir="${VENDORS_DIR}/${folder_name}"

    # Belt-and-suspenders containment check when realpath is available.
    if command -v realpath >/dev/null 2>&1; then
        local resolved_vendors_dir resolved_parent_dir
        resolved_vendors_dir="$(realpath -- "$VENDORS_DIR")"
        resolved_parent_dir="$(realpath -- "$(dirname -- "$target_dir")")"
        if [ "$resolved_parent_dir" != "$resolved_vendors_dir" ]; then
            err "Refusing to clear a path outside vendors/: ${target_dir}"
            return 1
        fi
    fi

    rm -rf -- "${target_dir:?}"
    mkdir -p -- "$target_dir"
}


# Remove specific top-level entries from an already-extracted vendor folder.
# base_dir is a validated destination; each entry is validated as a safe component.
prune_paths() {
    local base_dir="$1"
    shift
    local prune_entry
    for prune_entry in "$@"; do
        [ -n "$prune_entry" ] || continue
        if ! assert_safe_component "$prune_entry"; then
            warn "Skipping unsafe exclude entry: '${prune_entry}'"
            continue
        fi
        rm -rf -- "${base_dir:?}/${prune_entry}"
    done
}


#############################################################################
# Remote / local SHA helpers
#############################################################################

remote_branch_sha() {
    local repo_url="$1" branch_name="$2"
    # pipefail makes a failed ls-remote propagate; empty output is caught by caller.
    git ls-remote "$repo_url" "refs/heads/${branch_name}" 2>/dev/null | awk 'NR==1 {print $1}'
}


vendored_branch_sha() {
    local folder_name="$1"
    local ref_file_path="${VENDORS_DIR}/${folder_name}/.vendored-ref"
    [ -f "$ref_file_path" ] || { printf ''; return 0; }
    awk -F= '/^sha=/ {print $2; exit}' "$ref_file_path"
}


vendored_branch_name() {
    local folder_name="$1"
    local ref_file_path="${VENDORS_DIR}/${folder_name}/.vendored-ref"
    [ -f "$ref_file_path" ] || { printf ''; return 0; }
    awk -F= '/^branch=/ {print $2; exit}' "$ref_file_path"
}


write_vendored_ref() {
    local dest_dir="$1" repo_url="$2" branch_name="$3" commit_sha="$4"
    local timestamp_utc
    timestamp_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    cat > "${dest_dir}/.vendored-ref" <<EOF
# Vendored copy generated by ${SCRIPT_NAME}. Do not edit files in this folder.
# The upstream repo is the source of truth; local changes are overwritten on sync.
url=${repo_url}
branch=${branch_name}
sha=${commit_sha}
synced=${timestamp_utc}
EOF
}


#############################################################################
# Download shim
#############################################################################

download_file() {
    local source_url="$1" dest_path="$2"
    case "$DOWNLOAD_TOOL" in
        curl)
            # --retry-all-errors needs a reasonably recent curl; drop it if you
            # must support very old curl builds.
            curl -fL --retry 5 --retry-delay 2 --retry-all-errors \
                 --connect-timeout 20 -o "$dest_path" "$source_url"
            ;;
        wget)
            wget --tries=5 --waitretry=2 --timeout=20 -O "$dest_path" "$source_url"
            ;;
        *)
            err "No download tool selected"
            return 1
            ;;
    esac
}


#############################################################################
# Per-entry sync
#############################################################################

sync_entry() {
    local vendor_record="$1"
    local entry_name repo_url branch_name folder_name excludes_csv

    IFS='|' read -r entry_name repo_url branch_name folder_name excludes_csv <<< "$vendor_record"

    if [ -z "$entry_name" ] || [ -z "$repo_url" ] || [ -z "$branch_name" ] || [ -z "$folder_name" ]; then
        err "Malformed vendor record: '${vendor_record}'"
        return 1
    fi

    # Destination folder name must be a safe single component.
    assert_safe_component "$folder_name" || return 1

    local owner_repo_path codeload_url
    owner_repo_path="${repo_url#https://github.com/}"
    if [ "$owner_repo_path" = "$repo_url" ]; then
        err "Unexpected URL form (need https://github.com/OWNER/REPO): ${repo_url}"
        return 1
    fi
    codeload_url="https://codeload.github.com/${owner_repo_path}/tar.gz/refs/heads/${branch_name}"

    # Behind check.
    local remote_sha_value vendored_sha_value vendored_branch_value
    remote_sha_value="$(remote_branch_sha "$repo_url" "$branch_name")"
    if [ -z "$remote_sha_value" ]; then
        err "Could not resolve remote SHA for ${repo_url} (branch ${branch_name}). Check URL/branch/network."
        return 1
    fi
    vendored_sha_value="$(vendored_branch_sha "$folder_name")"
    vendored_branch_value="$(vendored_branch_name "$folder_name")"

    # Only skip when BOTH the commit and the recorded branch still match. A branch
    # repoint that happens to land on the same commit must still force a re-sync,
    # otherwise the folder would keep a stale branch label in its .vendored-ref.
    if [ "$remote_sha_value" = "$vendored_sha_value" ] \
            && [ "$branch_name" = "$vendored_branch_value" ]; then
        info "up-to-date: ${folder_name} (${branch_name} @ ${remote_sha_value:0:12})"
        return 0
    fi

    if [ -n "$vendored_branch_value" ] && [ "$branch_name" != "$vendored_branch_value" ]; then
        info "syncing: ${folder_name} branch change " \
                "'${vendored_branch_value}' -> '${branch_name}' @ ${remote_sha_value:0:12}"
    elif [ -n "$vendored_sha_value" ]; then
        info "syncing: ${folder_name} (${branch_name}) ${vendored_sha_value:0:12} -> ${remote_sha_value:0:12}"
    else
        info "syncing: ${folder_name} (${branch_name}) new -> ${remote_sha_value:0:12}"
    fi

    # Download to a temp dir.
    local temp_dir tarball_path
    temp_dir="$(mktemp -d)" || { err "mktemp failed"; return 1; }
    tarball_path="${temp_dir}/archive.tar.gz"

    if ! download_file "$codeload_url" "$tarball_path"; then
        err "download failed: ${codeload_url}"
        rm -rf -- "${temp_dir:?}"
        return 1
    fi

    # Integrity check: a valid gzip tar must list cleanly.
    if ! tar -tzf "$tarball_path" >/dev/null 2>&1; then
        err "downloaded file is not a valid gzip tarball: ${codeload_url}"
        rm -rf -- "${temp_dir:?}"
        return 1
    fi

    # Clear destination, then extract the full tree (strip the single top folder).
    if ! safe_clear_dir "$folder_name"; then
        rm -rf -- "${temp_dir:?}"
        return 1
    fi

    local dest_dir="${VENDORS_DIR}/${folder_name}"

    if ! tar -xzf "$tarball_path" -C "$dest_dir" --strip-components=1; then
        err "extraction failed for ${folder_name}"
        rm -rf -- "${temp_dir:?}"
        return 1
    fi

    rm -rf -- "${temp_dir:?}"

    # Prune excluded top-level paths by exact name.
    if [ -n "$excludes_csv" ]; then
        local -a exclude_paths=()
        local saved_ifs="$IFS"
        IFS=','
        read -r -a exclude_paths <<< "$excludes_csv"
        IFS="$saved_ifs"
        prune_paths "$dest_dir" "${exclude_paths[@]}"
    fi

    write_vendored_ref "$dest_dir" "$repo_url" "$branch_name" "$remote_sha_value"

    info "done: ${folder_name}"
    return 0
}


#############################################################################
# Commit (optional)
#############################################################################

commit_vendors() {
    git -C "$REPO_ROOT_DIR" add -A -- vendors
    if git -C "$REPO_ROOT_DIR" diff --cached --quiet -- vendors; then
        info "no vendor changes to commit"
        return 0
    fi
    git -C "$REPO_ROOT_DIR" commit -m "Sync vendored dependencies" -- vendors
}


#############################################################################
# Table validation
#############################################################################

# Abort loudly if two records target the same destination folder, since the
# later record would silently clobber the earlier one's synced files.
assert_unique_folders() {
    local record folder_field
    local seen_folders=''
    local duplicate_found=0

    while IFS= read -r record; do
        [ -n "$record" ] || continue
        case "$record" in \#*) continue ;; esac

        folder_field="$(printf '%s\n' "$record" | cut -d'|' -f4)"
        if [ -z "$folder_field" ]; then
            err "Vendor record has an empty folder field: '${record}'"
            duplicate_found=1
            continue
        fi

        case "|${seen_folders}|" in
            *"|${folder_field}|"*)
                err "Duplicate destination folder in vendor table: '${folder_field}'"
                duplicate_found=1
                ;;
            *)
                seen_folders="${seen_folders}|${folder_field}"
                ;;
        esac
    done <<< "$VENDOR_RECORDS"

    if [ "$duplicate_found" -ne 0 ]; then
        err "Fix the vendor table before running; refusing to sync."
        exit 1
    fi
}


#############################################################################
# Main
#############################################################################

usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [--commit]

  Populates the Toshy 'vendors/' folder from configured upstream repos,
  syncing each only when its tracked branch has moved.

  --commit    Stage and commit vendors/ changes after syncing (default: off).
  -h, --help  Show this help.
EOF
}


main() {
    local do_commit=0

    while [ $# -gt 0 ]; do
        case "$1" in
            --commit)   do_commit=1 ;;
            -h|--help)  usage; exit 0 ;;
            *)          err "Unknown argument: $1"; usage; exit 1 ;;
        esac
        shift
    done

    reject_root
    require_commands
    detect_download_tool
    resolve_repo_root
    assert_unique_folders

    local overall_exit_code=0
    local vendor_record
    while IFS= read -r vendor_record; do
        [ -n "$vendor_record" ] || continue
        case "$vendor_record" in \#*) continue ;; esac
        if ! sync_entry "$vendor_record"; then
            overall_exit_code=1
        fi
    done <<< "$VENDOR_RECORDS"

    if [ "$do_commit" -eq 1 ]; then
        if [ "$overall_exit_code" -ne 0 ]; then
            warn "Skipping commit because one or more entries failed."
        else
            commit_vendors
        fi
    fi

    if [ "$overall_exit_code" -ne 0 ]; then
        err "One or more vendor entries failed to sync."
    else
        info "All vendor entries processed."
    fi

    return "$overall_exit_code"
}


main "$@"

# End of file #

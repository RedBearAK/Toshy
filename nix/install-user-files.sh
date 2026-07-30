#!/usr/bin/env bash
# Repo location: toshy/nix/install-user-files.sh

# Convenience front door for installing the Toshy user-level files on
# systems with an externally managed (Nix-provided) runtime: finds the
# runtime, finds setup_toshy.py next to this script's folder, and runs
# the 'install-user-files' subcommand with it. All arguments are passed
# through (e.g. --barebones-config, --fancy-pants).
#
# Equivalent to:
#   <runtime>/bin/python ./setup_toshy.py install-user-files [options]

# shellcheck disable=SC2034
SCRIPT_VERSION='20260730'

if [[ $EUID -eq 0 ]]; then
    echo "ERROR: Do not run this as root or with sudo. Run as your normal user."
    exit 1
fi

runtime_dir="${TOSHY_RUNTIME_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/toshy/runtime}"

if [[ ! -x "${runtime_dir}/bin/python" ]]; then
    echo "ERROR: No usable Toshy runtime found at:"
    echo "    ${runtime_dir}"
    echo "Apply the NixOS / Home Manager configuration first (see nix/README.md)."
    exit 1
fi

setup_script="$(dirname "$0")/../setup_toshy.py"

if [[ ! -f "$setup_script" ]]; then
    echo "ERROR: setup_toshy.py not found relative to this script."
    echo "Run this from an extracted/cloned copy of the Toshy source tree."
    exit 1
fi

exec "${runtime_dir}/bin/python" "$setup_script" install-user-files "$@"

# End of file #

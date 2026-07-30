#!/usr/bin/env bash


# Reinstall Toshy from the tracked GitHub branch.
#
# Normal distros: launches the bootstrap reinstaller (downloads a fresh
# tree and runs the full installer).
#
# NixOS: performs the equivalent "refresh" for a flake-managed install:
# advances the pinned toshy flake input to the current branch tip, rebuilds
# the system (which rebuilds the runtime and moves the runtime link), then
# reinstalls the user files from a source tree matching the exact locked
# revision, preserving the runtime/user-files coupling.

# shellcheck disable=SC2034
SCRIPT_VERSION='20260729'

echo        # blank line to separate from command

os_release_id=''
if [[ -r /etc/os-release ]]; then
    os_release_id="$(. /etc/os-release && echo "${ID:-}")"
fi

# ---------------------------------------------------------------------------
# Normal distro path: unchanged behavior, hand off to bootstrap.
# ---------------------------------------------------------------------------
if [[ "$os_release_id" != "nixos" ]]; then
    echo "This usually works but could potentially break a working Toshy install."
    echo "Not advised if you don't have some time to revert to a working release."
    echo
    read -r -p "Are you sure you want to reinstall Toshy from a GitHub branch? [y/N]: " result

    if [[ "$result" == "y" || "$result" == "Y" ]]; then
        :   # no-op lets script continue
    else
        echo
        echo "Toshy reinstall canceled."
        echo
        exit 0
    fi

    if [[ -f "$HOME/.config/toshy/scripts/bootstrap.sh" ]]; then
        exec "$HOME/.config/toshy/scripts/bootstrap.sh"
    else
        echo "Bootstrap script missing. Exiting."
        echo
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# NixOS path: refresh the flake input, rebuild, reinstall user files from
# the matching locked revision.
# ---------------------------------------------------------------------------

runtime_link="${XDG_STATE_HOME:-$HOME/.local/state}/toshy/runtime"
system_flake='/etc/nixos/flake.nix'

if [[ ! -e "$system_flake" ]] || ! grep -q 'toshy' "$system_flake"; then
    echo "ERROR: No system flake with a 'toshy' input was found at:"
    echo "    $system_flake"
    echo "This command can only refresh a flake-managed Toshy install."
    echo "See nix/README.md in the Toshy repo for setup instructions."
    exit 1
fi

if [[ ! -x "${runtime_link}/bin/python" ]]; then
    echo "ERROR: The Toshy runtime link is missing or broken:"
    echo "    $runtime_link"
    echo "Re-apply your NixOS / Home Manager configuration first."
    exit 1
fi

echo "This will update the pinned Toshy flake input to the current tip of the"
echo "branch it tracks, rebuild the system, and reinstall the user files from"
echo "the matching revision. Admin (sudo) access is required."
echo
read -r -p "Refresh the flake-managed Toshy install? [y/N]: " result

if [[ "$result" != "y" && "$result" != "Y" ]]; then
    echo
    echo "Toshy reinstall canceled."
    echo
    exit 0
fi

echo
echo "Advancing the 'toshy' flake input to the current branch tip..."
if ! sudo nix flake update toshy --flake /etc/nixos; then
    # Older Nix used a different spelling for updating a single input.
    echo "Retrying with older 'nix flake lock' syntax..."
    if ! sudo nix flake lock --update-input toshy /etc/nixos; then
        echo "ERROR: Could not update the flake input. Fix the errors above and retry."
        exit 1
    fi
fi

host_name="$(hostname 2>/dev/null || cat /proc/sys/kernel/hostname)"

echo
echo "Rebuilding the system (this rebuilds the Toshy runtime)..."
if ! sudo nixos-rebuild switch --flake "/etc/nixos#${host_name}"; then
    echo "ERROR: 'nixos-rebuild switch' failed. Fix the errors above and retry."
    exit 1
fi

if [[ ! -x "${runtime_link}/bin/python" ]]; then
    echo "ERROR: The runtime link is broken after the rebuild:"
    echo "    $runtime_link"
    echo "If the link is managed by STANDALONE home-manager (not the NixOS"
    echo "module), run 'home-manager switch' as well, then rerun this command."
    exit 1
fi

echo
echo "Determining the locked Toshy revision..."
locked_rev="$("${runtime_link}/bin/python" -c '
import json, subprocess
out = subprocess.check_output(
    ["nix", "flake", "metadata", "/etc/nixos", "--json"])
print(json.loads(out)["locks"]["nodes"]["toshy"]["locked"]["rev"])
')"

if [[ -z "$locked_rev" ]]; then
    echo "ERROR: Could not determine the locked Toshy revision."
    exit 1
fi
echo "Locked revision: $locked_rev"

src_tmp_dir="$(mktemp -d /tmp/toshy-reinstall-src-XXXXXX)"
tarball_url="https://codeload.github.com/RedBearAK/toshy/tar.gz/${locked_rev}"

echo
echo "Fetching the matching source tree..."
if ! curl -sL "$tarball_url" | tar xz --strip-components=1 -C "$src_tmp_dir"; then
    echo "ERROR: Could not download/unpack the Toshy source for revision:"
    echo "    $locked_rev"
    rm -rf "$src_tmp_dir"
    exit 1
fi

echo
echo "Reinstalling the Toshy user files from the matching revision..."
cd "$src_tmp_dir" || exit 1
if "${runtime_link}/bin/python" ./setup_toshy.py install-user-files; then
    cd / && rm -rf "$src_tmp_dir"
else
    echo
    echo "ERROR: 'install-user-files' failed. Source tree left for inspection at:"
    echo "    $src_tmp_dir"
    exit 1
fi

# End of file #

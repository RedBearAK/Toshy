#!/usr/bin/env bash
# Repo location: toshy/nix/nixos-scaffold.sh

# EXPERIMENTAL. Generates a system flake for a fresh NixOS install that has
# no existing /etc/nixos/flake.nix, wiring in the Toshy NixOS module, Home
# Manager, and the Toshy Home Manager module, so that the standard Toshy
# NixOS setup instructions can be followed from a stock installation.
#
# This script is deliberately unprivileged and never modifies any existing
# file. It writes its output to ./toshy-scaffold/flake.nix in the current
# directory and prints the commands to review and place it. If a system
# flake already exists, it refuses and points at the manual instructions
# in nix/README.md instead.
#
# NixOS only. On SteamOS (or any other distro), even with the Nix package
# manager installed, there is no nixos-rebuild and no /etc/nixos, so this
# scaffold does not apply. See nix/README.md for what does.

# shellcheck disable=SC2034
SCRIPT_VERSION='20260729'

# Guard: never run as root; user detection and ownership would be wrong,
# and nothing here needs privileges.
if [[ $EUID -eq 0 ]]; then
    echo "ERROR: Do not run this script as root or with sudo."
    echo "Run it as your normal user. It only writes into the current directory."
    exit 1
fi

# Guard: must be on NixOS. Everything generated is for nixos-rebuild.
os_release_id=''
os_release_version_id=''
if [[ -r /etc/os-release ]]; then
    os_release_id="$(. /etc/os-release && echo "${ID:-}")"
    os_release_version_id="$(. /etc/os-release && echo "${VERSION_ID:-}")"
fi

if [[ "$os_release_id" == "steamos" ]]; then
    echo "ERROR: This is SteamOS, not NixOS."
    echo "SteamOS has no nixos-rebuild and no /etc/nixos, so this scaffold does"
    echo "not apply, even with the Nix package manager installed."
    echo "See nix/README.md in the Toshy repo for what applies on other systems."
    exit 1
fi

if [[ "$os_release_id" != "nixos" ]]; then
    echo "ERROR: This script only works on NixOS."
    echo "Detected distro ID: '${os_release_id:-unknown}'"
    echo "On other distros, use the normal Toshy installer instead:"
    echo ""
    echo "    ./setup_toshy.py install"
    echo ""
    exit 1
fi

# Guard: refuse when a system flake already exists. Editing an existing
# flake programmatically is out of scope; a person maintaining one can add
# the few lines themselves.
if [[ -e /etc/nixos/flake.nix ]]; then
    echo "ERROR: /etc/nixos/flake.nix already exists."
    echo "This script only scaffolds a system flake where none exists, and"
    echo "will not modify an existing one."
    echo ""
    echo "To add Toshy to your existing flake, follow the 'Setup' section of"
    echo "nix/README.md in the Toshy repo: add the toshy input, import the"
    echo "NixOS and Home Manager modules, and enable services.toshy in both."
    exit 1
fi

if [[ ! -r /etc/nixos/configuration.nix ]]; then
    echo "ERROR: /etc/nixos/configuration.nix was not found or is not readable."
    echo "The generated flake wraps the existing configuration, so a standard"
    echo "NixOS installation is expected. If your configuration lives elsewhere,"
    echo "follow the manual instructions in nix/README.md instead."
    exit 1
fi

# ---- Detection (each detected value is printed; nothing is silent) ----

user_name="${USER:-}"
if [[ -z "$user_name" ]]; then
    echo "ERROR: \$USER is not set; cannot detect the username."
    exit 1
fi

host_name="$(hostname 2>/dev/null || cat /proc/sys/kernel/hostname 2>/dev/null)"
if [[ -z "$host_name" ]]; then
    echo "ERROR: Could not detect the hostname."
    echo "The flake's configuration attribute must match it for nixos-rebuild."
    exit 1
fi

machine_arch="$(uname -m)"
case "$machine_arch" in
    x86_64)     nix_system='x86_64-linux' ;;
    aarch64)    nix_system='aarch64-linux' ;;
    *)
        echo "ERROR: Unsupported machine architecture: ${machine_arch}"
        echo "The Toshy flake currently targets x86_64-linux and aarch64-linux."
        exit 1
        ;;
esac

# NixOS release for the nixpkgs and Home Manager branch pins. Stable
# releases have VERSION_ID like '25.11'. Anything else falls back to the
# unstable branches, with a warning.
if [[ "$os_release_version_id" =~ ^[0-9][0-9]\.[0-9][0-9]$ ]]; then
    nixpkgs_branch="nixos-${os_release_version_id}"
    hm_branch="release-${os_release_version_id}"
else
    echo "NOTICE: Could not detect a stable NixOS release from VERSION_ID"
    echo "        ('${os_release_version_id:-unknown}'). Pinning to the unstable branches."
    nixpkgs_branch='nixos-unstable'
    hm_branch='master'
fi

# stateVersion: the installer writes this into configuration.nix. Fall back
# to the detected release, with a warning, if the grep finds nothing.
state_version="$(grep -oE 'system\.stateVersion[[:space:]]*=[[:space:]]*"[0-9]+\.[0-9]+"' \
    /etc/nixos/configuration.nix | grep -oE '[0-9]+\.[0-9]+' | head -1)"
if [[ -z "$state_version" ]]; then
    if [[ "$os_release_version_id" =~ ^[0-9][0-9]\.[0-9][0-9]$ ]]; then
        state_version="$os_release_version_id"
        echo "NOTICE: system.stateVersion not found in configuration.nix;"
        echo "        using detected release '${state_version}' for home.stateVersion."
    else
        echo "ERROR: Could not determine a stateVersion from configuration.nix"
        echo "or from the OS release. Edit the generated file manually, or use"
        echo "the manual instructions in nix/README.md."
        exit 1
    fi
fi

echo ""
echo "Detected values (used in the generated flake):"
echo "    User:             ${user_name}"
echo "    Hostname:         ${host_name}"
echo "    System:           ${nix_system}"
echo "    nixpkgs branch:   ${nixpkgs_branch}"
echo "    Home Manager:     ${hm_branch}"
echo "    stateVersion:     ${state_version}"
echo ""

# ---- Generation (into the current directory only) ----

out_dir='./toshy-scaffold'
out_file="${out_dir}/flake.nix"

mkdir -p "$out_dir"
if [[ -e "$out_file" ]]; then
    echo "NOTICE: Overwriting previously generated ${out_file}"
fi

cat > "$out_file" << EOF
# Generated by Toshy's nix/nixos-scaffold.sh (version ${SCRIPT_VERSION}).
# Review before use. Intended destination: /etc/nixos/flake.nix
#
# Wraps the existing /etc/nixos/configuration.nix and adds:
#   - flakes enablement (baked in after the first flake-based rebuild)
#   - the Toshy NixOS module (udev rules, uinput, input group)
#   - Home Manager, with the Toshy Home Manager module (runtime link)
#
# UPGRADING TOSHY LATER: the toshy input below is PINNED in flake.lock at
# the revision first fetched; rebuilds do not advance it. To update to the
# current tip of the tracked branch, either run 'toshy-reinstall' (which
# does all of this plus the user-files reinstall), or manually:
#
#   sudo nix flake update toshy --flake /etc/nixos
#   sudo nixos-rebuild switch --flake /etc/nixos#${host_name}

{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/${nixpkgs_branch}";
    home-manager.url = "github:nix-community/home-manager/${hm_branch}";
    home-manager.inputs.nixpkgs.follows = "nixpkgs";
    toshy.url = "github:RedBearAK/toshy/main";
  };

  outputs = { self, nixpkgs, home-manager, toshy }: {
    nixosConfigurations.${host_name} = nixpkgs.lib.nixosSystem {
      system = "${nix_system}";
      modules = [
        ./configuration.nix
        toshy.nixosModules.toshy
        home-manager.nixosModules.home-manager
        {
          nix.settings.experimental-features = [ "nix-command" "flakes" ];

          services.toshy = {
            enable = true;
            users  = [ "${user_name}" ];
          };

          home-manager.users.${user_name} = {
            imports = [ toshy.homeManagerModules.toshy ];
            services.toshy.enable = true;
            home.stateVersion = "${state_version}";
          };
        }
      ];
    };
  };
}

# End of file #
EOF

echo "Generated: ${out_file}"
echo ""
echo "Next steps:"
echo ""
echo "1. Review the generated file (it will manage your system):"
echo ""
echo "       less ${out_file}"
echo ""
echo "   (To track Toshy's dev_beta branch instead of main, edit the"
echo "   toshy input URL in the file before proceeding.)"
echo ""
echo "2. Place it (the only privileged step, done by you, not this script):"
echo ""
echo "       sudo cp ${out_file} /etc/nixos/flake.nix"
echo ""
echo "3. Rebuild. The first flake-based rebuild needs flakes enabled on the"
echo "   command line; after it succeeds, the setting is baked in:"
echo ""
echo "       sudo NIX_CONFIG='experimental-features = nix-command flakes' \\"
echo "           nixos-rebuild switch --flake /etc/nixos#${host_name}"
echo ""
echo "   NOTE: If this rebuild FAILS, nothing gets baked in. Until one"
echo "   rebuild succeeds, keep the NIX_CONFIG prefix on every rebuild, and"
echo "   add:  --extra-experimental-features 'nix-command flakes'"
echo "   to any other 'nix' commands you run (nix run, nix flake, etc.)."
echo ""
echo "4. Log out and back in, so the 'input' group membership takes effect."
echo ""
echo "5. Install the Toshy user-level files, from this repo clone:"
echo ""
echo "       ~/.local/state/toshy/runtime/bin/python ./setup_toshy.py install-user-files"
echo ""
echo "6. UPGRADING LATER: the flake pins Toshy at the revision it first"
echo "   fetches; plain rebuilds never advance it. To update to the current"
echo "   tip of the tracked branch, just run the installed command:"
echo ""
echo "       toshy-reinstall"
echo ""
echo "   (It advances the pin, rebuilds, and reinstalls the user files from"
echo "   the matching revision. The same commands are also in a comment at"
echo "   the top of the generated flake.)"
echo ""

# End of file #

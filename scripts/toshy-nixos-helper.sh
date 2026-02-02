#!/usr/bin/env bash
# toshy-nixos-helper.sh - NixOS configuration generator for Toshy
#
# This script generates NixOS configuration snippets that users must add
# to /etc/nixos/configuration.nix for Toshy to work properly.

set -euo pipefail

# Check if running on NixOS
if [ ! -f /etc/NIXOS ] && ! grep -q 'ID=nixos' /etc/os-release 2>/dev/null; then
    echo "ERROR: This script is for NixOS only"
    exit 1
fi

echo "=== Toshy NixOS Configuration Helper ==="
echo ""
echo "This script generates configuration snippets for NixOS."
echo ""

# Check required packages
echo "Checking for required packages..."
missing=()
for pkg in python3 git gcc pkg-config; do
    if ! command -v "$pkg" &> /dev/null; then
        missing+=("$pkg")
    fi
done

if [ ${#missing[@]} -gt 0 ]; then
    echo "WARNING: Missing packages: ${missing[*]}"
    echo "They will be included in the generated configuration."
fi

# Get username for configuration
USERNAME="${USER:-<username>}"

# Generate config
cat << EOF

# =============================================================================
# Add to /etc/nixos/configuration.nix:
# =============================================================================

{ config, pkgs, ... }:
{
  # Toshy dependencies
  environment.systemPackages = with pkgs; [
    git python3 python3Packages.pip python3Packages.dbus-python
    libnotify zenity cairo gobject-introspection
    libappindicator-gtk3 systemd libxkbcommon wayland
    dbus gcc libjpeg evtest xorg.xset pkg-config
  ];

  # Udev rules for input device access
  services.udev.extraRules = ''
    SUBSYSTEM=="input", GROUP="input", MODE="0660", TAG+="uaccess"
    KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input", MODE="0660", TAG+="uaccess"
  '';

  # Add your user to input group (replace <username>)
  users.users.$USERNAME.extraGroups = [ "input" "systemd-journal" ];

  # Load uinput kernel module
  boot.kernelModules = [ "uinput" ];
}

# =============================================================================
# After editing configuration.nix:
# =============================================================================

# 1. Replace <username> with your actual username (if needed)
# 2. Run: sudo nixos-rebuild switch
# 3. Log out and log back in (for group changes)
# 4. Run Toshy installer: ./setup_toshy.py install

EOF

echo ""
echo "Configuration snippet generated above."
echo "Copy it to /etc/nixos/configuration.nix and follow the instructions."

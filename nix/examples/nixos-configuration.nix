# NixOS configuration.nix example for Toshy
# This shows how to add Toshy to a traditional (non-flake) NixOS configuration

{ config, pkgs, ... }:

{
  # System-wide Toshy configuration (udev rules, kernel modules, packages)
  # This only sets up the system-level requirements.
  # Users still need to enable Toshy via home-manager.

  # Add required packages to system
  environment.systemPackages = with pkgs; [
    git
    python3
    python3Packages.pip
    python3Packages.dbus-python
    libnotify
    zenity
    cairo
    gobject-introspection
    libappindicator-gtk3
    systemd
    libxkbcommon
    wayland
    dbus
    gcc
    libjpeg
    evtest
    xorg.xset
    pkg-config
  ];

  # Udev rules for input device access
  services.udev.extraRules = ''
    # Toshy keymapper input device access
    SUBSYSTEM=="input", GROUP="input", MODE="0660", TAG+="uaccess"
    KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input", MODE="0660", TAG+="uaccess"
  '';

  # Add your user to required groups
  users.users.myuser.extraGroups = [ "input" "systemd-journal" ];

  # Load uinput kernel module
  boot.kernelModules = [ "uinput" ];

  # Note: After setting up system configuration, users need to:
  # 1. Log out and back in (for group changes to take effect)
  # 2. Install Toshy via home-manager or the Python installer
  #
  # Recommended: Use home-manager with the Toshy flake
  # See nix/examples/flake-example.nix for a complete setup
}

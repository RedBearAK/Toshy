{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.toshy;

in
{
  options.services.toshy = {
    enable = mkEnableOption "Toshy keyboard remapper (system-wide configuration)";

    package = mkOption {
      type = types.package;
      default = pkgs.toshy;
      defaultText = literalExpression "pkgs.toshy";
      description = "The Toshy package to use.";
    };
  };

  config = mkIf cfg.enable {
    # Install system packages required by Toshy
    environment.systemPackages = with pkgs; [
      cfg.package
      pkgs.xwaykeyz
      git
      python3
      dbus
      libnotify
      zenity
      cairo
      gobject-introspection
      libappindicator-gtk3
      systemd
      libxkbcommon
      wayland
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

    # Load uinput kernel module
    boot.kernelModules = [ "uinput" ];

    # Note: Users still need to configure Toshy via home-manager
    # This NixOS module only provides system-level configuration (packages, udev rules, kernel modules)
    # The actual Toshy services are configured via the home-manager module
  };
}

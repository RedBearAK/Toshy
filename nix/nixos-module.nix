# Repo location: toshy/nix/nixos-module.nix
#
# EXPERIMENTAL. System-level pieces that Toshy's normal installer would set up
# imperatively on other distros: the uinput kernel module, the udev rules that
# grant the "input" group access to input devices and /dev/uinput, and "input"
# group membership for the listed users.
#
# This module intentionally does NOT install any Toshy files or services.
# Those are user-level, handled by "setup_toshy.py install-user-files" after
# the home-manager module has placed the runtime link.

{ config, lib, pkgs, ... }:

let
  cfg = config.services.toshy;
in
{
  options.services.toshy = {
    enable = lib.mkEnableOption
      "system-level support for the Toshy keymapper (udev rules, uinput, input group)";

    users = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      example = [ "alice" ];
      description = ''
        Users to add to the "input" group so the keymapper can read input
        devices and write to /dev/uinput. A logout/login (or reboot) is
        required after membership is first granted.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    boot.kernelModules = [ "uinput" ];

    # Mirrors the rules Toshy's installer writes on other distros
    # ('70-toshy-keymapper-input.rules'), with the setfacl path made
    # deterministic instead of located with which().
    services.udev.extraRules = ''
      SUBSYSTEM=="input", GROUP="input", MODE="0660", TAG+="uaccess"
      KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input", MODE="0660", TAG+="uaccess", RUN+="${pkgs.acl}/bin/setfacl -m g::rw /dev/uinput"
    '';

    users.users = lib.genAttrs cfg.users (user: {
      extraGroups = [ "input" ];
    });
  };
}

# End of file #

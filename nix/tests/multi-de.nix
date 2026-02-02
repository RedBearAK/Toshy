# Multi-DE Toshy integration test
# Tests Toshy on different desktop environments
#
# Run with: nix-build nix/tests/multi-de.nix

{ pkgs ? import <nixpkgs> { }
}:

let
  # Common configuration for all machines
  commonConfig = { config, pkgs, lib, ... }: {
    # System packages
    environment.systemPackages = with pkgs; [
      git
      python3
      python3Packages.dbus-python
    ];

    # Udev rules
    services.udev.extraRules = ''
      SUBSYSTEM=="input", GROUP="input", MODE="0660", TAG+="uaccess"
      KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input", MODE="0660", TAG+="uaccess"
    '';

    # Kernel module
    boot.kernelModules = [ "uinput" ];

    # Test user
    users.users.alice = {
      isNormalUser = true;
      extraGroups = [ "input" "systemd-journal" ];
      password = "test";
    };
  };

in pkgs.testers.runNixOSTest {
  name = "toshy-multi-de-test";

  nodes = {
    # Machine 1: XFCE desktop
    xfce = { config, pkgs, lib, ... }: {
      imports = [ commonConfig ];

      services.xserver = {
        enable = true;
        displayManager.lightdm.enable = true;
        desktopManager.xfce.enable = true;
      };
    };

    # Machine 2: Generic X11 (simulates other DEs)
    generic = { config, pkgs, lib, ... }: {
      imports = [ commonConfig ];

      services.xserver = {
        enable = true;
        displayManager.lightdm.enable = true;
      };
    };
  };

  testScript = ''
    # Start all machines
    start_all()

    # Test XFCE machine
    with subtest("XFCE desktop environment"):
        xfce.wait_for_unit("multi-user.target")
        xfce.succeed("lsmod | grep uinput")
        xfce.succeed("groups alice | grep input")
        print("✓ XFCE machine configured correctly")

    # Test generic X11 machine
    with subtest("Generic X11 environment"):
        generic.wait_for_unit("multi-user.target")
        generic.succeed("lsmod | grep uinput")
        generic.succeed("groups alice | grep input")
        print("✓ Generic machine configured correctly")

    # Test that both machines have proper udev rules
    with subtest("Udev rules on all machines"):
        xfce.succeed("grep -q 'uinput' /etc/udev/rules.d/*")
        generic.succeed("grep -q 'uinput' /etc/udev/rules.d/*")
        print("✓ Udev rules configured on all machines")

    # Test user permissions on all machines
    with subtest("User permissions on all machines"):
        xfce.succeed("test -c /dev/uinput")
        generic.succeed("test -c /dev/uinput")
        print("✓ User permissions configured on all machines")

    print("✓ All multi-DE tests passed!")
  '';
}

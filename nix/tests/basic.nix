# Basic Toshy integration test
# Tests package installation and basic functionality
#
# Run with: nix-build basic.nix

{ pkgs ? import <nixpkgs> { }
, self ? null
}:

pkgs.testers.runNixOSTest {
  name = "toshy-basic-test";

  nodes.machine = { config, pkgs, lib, ... }: {
    # Create a test user
    users.users.alice = {
      isNormalUser = true;
      extraGroups = [ "input" "systemd-journal" ];
      password = "test";
    };

    # System packages
    environment.systemPackages = with pkgs; [
      git
      python3
      python3Packages.dbus-python
    ];

    # Udev rules for input device access
    services.udev.extraRules = ''
      SUBSYSTEM=="input", GROUP="input", MODE="0660", TAG+="uaccess"
      KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input", MODE="0660", TAG+="uaccess"
    '';

    # Load uinput module
    boot.kernelModules = [ "uinput" ];

    # Enable a minimal X server for testing
    services.xserver = {
      enable = true;
      displayManager.lightdm.enable = true;
    };
  };

  testScript = ''
    # Start the machine and wait for it to be ready
    machine.start()
    machine.wait_for_unit("multi-user.target")

    # Test 1: Verify system packages are available
    with subtest("System packages installed"):
        machine.succeed("which git")
        machine.succeed("which python3")

    # Test 2: Verify udev rules are present
    with subtest("Udev rules configured"):
        machine.succeed("grep -q 'uinput' /etc/udev/rules.d/*")
        machine.succeed("grep -q 'input' /etc/udev/rules.d/*")

    # Test 3: Verify uinput module is loaded
    with subtest("Uinput kernel module loaded"):
        machine.succeed("lsmod | grep uinput")
        machine.succeed("test -c /dev/uinput")

    # Test 4: Verify user is in input group
    with subtest("User in input group"):
        machine.succeed("groups alice | grep input")
        machine.succeed("groups alice | grep systemd-journal")

    # Test 5: Test uinput device permissions
    with subtest("Uinput device permissions"):
        machine.succeed("ls -la /dev/uinput")
        machine.succeed("stat -c '%G' /dev/uinput | grep -E '(input|root)'")

    print("✓ All basic tests passed!")
  '';
}

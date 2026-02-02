# Full Toshy integration test
# Tests complete system configuration
#
# Run with: nix-build nix/tests/integration.nix

{ pkgs ? import <nixpkgs> { }
}:

pkgs.testers.runNixOSTest {
  name = "toshy-integration";

  nodes.machine = { config, pkgs, ... }: {
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

    # Create a test user
    users.users.alice = {
      isNormalUser = true;
      extraGroups = [ "input" "systemd-journal" ];
      password = "test";
    };

    # Enable a minimal desktop environment for testing
    services.xserver = {
      enable = true;
      displayManager.lightdm.enable = true;
      desktopManager.xfce.enable = true;
    };
  };

  testScript = ''
    # Start the machine and wait for it to be ready
    machine.start()
    machine.wait_for_unit("multi-user.target")
    machine.wait_for_unit("graphical.target")

    # Test 1: Verify system packages are installed
    with subtest("System packages"):
        machine.succeed("which git")
        machine.succeed("which python3")
        machine.succeed("python3 --version")
        print("✓ System packages installed")

    # Test 2: Verify udev rules are present
    with subtest("Udev rules"):
        machine.succeed("grep -q 'uinput' /etc/udev/rules.d/*")
        machine.succeed("grep -q 'input' /etc/udev/rules.d/*")
        print("✓ Udev rules configured")

    # Test 3: Verify uinput module is loaded
    with subtest("Kernel module"):
        machine.succeed("lsmod | grep uinput")
        machine.succeed("test -c /dev/uinput")
        print("✓ Uinput module loaded")

    # Test 4: Verify user is in input group
    with subtest("User groups"):
        machine.succeed("groups alice | grep input")
        machine.succeed("groups alice | grep systemd-journal")
        print("✓ User in correct groups")

    # Test 5: Verify Python dbus module works
    with subtest("Python environment"):
        machine.succeed("python3 -c 'import dbus'")
        print("✓ Python dbus module working")

    print("✓ All integration tests passed!")
  '';
}

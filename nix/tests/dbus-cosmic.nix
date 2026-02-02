# Test COSMIC D-Bus service
# Uses environment override since COSMIC desktop may not be fully available in nixpkgs
#
# Run with: nix build .#checks.x86_64-linux.toshy-dbus-cosmic-test

{ pkgs ? import <nixpkgs> { }
, self ? null
, home-manager ? null
}:

let
  toshy = if self != null then self else {
    nixosModules.default = import ../modules/nixos.nix;
    homeManagerModules.default = import ../modules/home-manager.nix;
  };

  # Fetch home-manager for the test VM
  home-manager-src = if home-manager != null then home-manager else builtins.fetchTarball {
    url = "https://github.com/nix-community/home-manager/archive/master.tar.gz";
  };
in

pkgs.testers.runNixOSTest {
  name = "toshy-dbus-cosmic-test";

  nodes.machine = { config, lib, ... }: {
    imports = [
      toshy.nixosModules.default
      "${home-manager-src}/nixos"
    ];

    # Use the pkgs with overlay (from outer scope)
    nixpkgs.pkgs = lib.mkForce pkgs;

    # Enable Toshy at system level
    services.toshy.enable = true;

    # Set up minimal Wayland environment (using Sway as base)
    # We'll override to COSMIC via desktopEnvironment option
    services.xserver.enable = true;
    services.displayManager.sddm.enable = true;
    services.displayManager.sddm.wayland.enable = true;

    # Install Sway as the base compositor
    programs.sway.enable = true;

    # Auto-login for testing
    services.displayManager.autoLogin.enable = true;
    services.displayManager.autoLogin.user = "alice";

    # Create test user
    users.users.alice = {
      isNormalUser = true;
      extraGroups = [ "input" "wheel" ];
      password = "alice";
    };

    # Home Manager configuration
    home-manager = {
      useGlobalPkgs = true;
      useUserPackages = true;
      users.alice = {
        imports = [ toshy.homeManagerModules.default ];

        services.toshy = {
          enable = true;
          # Override to COSMIC even though we're running Sway
          desktopEnvironment = "cosmic";
          autoStart = true;
        };

        home.stateVersion = "24.11";
      };
    };
  };

  testScript = ''
    start_all()

    # Wait for system to be ready
    machine.wait_for_unit("multi-user.target")
    machine.wait_for_unit("graphical.target")

    # Wait for user session
    machine.wait_until_succeeds("loginctl show-user alice")

    # Wait for graphical-session target
    machine.wait_until_succeeds(
        "systemctl --user -M alice@ is-active graphical-session.target",
        timeout=60
    )

    with subtest("COSMIC D-Bus service should start with DE override"):
        # Service should be active when desktopEnvironment = "cosmic"
        machine.wait_until_succeeds(
            "systemctl --user -M alice@ is-active toshy-cosmic-dbus.service",
            timeout=30
        )

    with subtest("COSMIC D-Bus service should register on D-Bus"):
        # D-Bus service name should be registered
        machine.wait_until_succeeds(
            "busctl --user -M alice@ list | grep org.toshy.Cosmic",
            timeout=10
        )

    with subtest("Service should have TOSHY_DE_OVERRIDE environment variable"):
        # Check that environment override is set
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-cosmic-dbus.service -p Environment"
        )
        assert "TOSHY_DE_OVERRIDE=cosmic" in output, \
            f"Expected TOSHY_DE_OVERRIDE=cosmic in environment, got: {output}"

    with subtest("Service should have Wayland environment variables"):
        # Verify Wayland-specific env vars
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-cosmic-dbus.service -p Environment"
        )
        # Should have PYTHONPATH at minimum
        assert "PYTHONPATH" in output

    with subtest("Service should be Type=dbus"):
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-cosmic-dbus.service -p Type"
        )
        assert "Type=dbus" in output

    with subtest("Service should not have import errors"):
        status = machine.succeed(
            "systemctl --user -M alice@ status toshy-cosmic-dbus.service"
        )
        assert "ImportError" not in status
        assert "ModuleNotFoundError" not in status

    with subtest("Service should be part of graphical-session"):
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-cosmic-dbus.service -p PartOf"
        )
        assert "graphical-session.target" in output

    with subtest("Service journal should show it started"):
        journal = machine.succeed(
            "journalctl --user -M alice@ -u toshy-cosmic-dbus.service --no-pager"
        )
        # Check for Python process start (should not be completely empty)
        assert len(journal) > 0, "Journal is empty, service may not have started"
  '';
}

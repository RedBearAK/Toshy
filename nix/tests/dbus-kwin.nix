# Test KWin D-Bus service on KDE Plasma Wayland
# Tests that the window context provider service starts correctly
#
# Run with: nix build .#checks.x86_64-linux.toshy-dbus-kwin-test

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
  name = "toshy-dbus-kwin-test";

  nodes.machine = { config, lib, ... }: {
    imports = [
      toshy.nixosModules.default
      "${home-manager-src}/nixos"
    ];

    # Use the pkgs with overlay (from outer scope)
    nixpkgs.pkgs = lib.mkForce pkgs;

    # Enable Toshy at system level
    services.toshy.enable = true;

    # Set up KDE Plasma 6 with Wayland
    services.xserver.enable = true;
    services.displayManager.sddm.enable = true;
    services.displayManager.sddm.wayland.enable = true;
    services.desktopManager.plasma6.enable = true;

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
          desktopEnvironment = "kde";
          autoStart = true;
        };

        home.stateVersion = "24.11";
      };
    };
  };

  # RED: Write failing tests first
  testScript = ''
    start_all()

    # Wait for graphical session to be ready
    machine.wait_for_unit("multi-user.target")
    machine.wait_for_unit("graphical.target")

    # Wait for user session
    machine.wait_until_succeeds("loginctl show-user alice")

    # Wait for graphical-session target for user
    machine.wait_until_succeeds(
        "systemctl --user -M alice@ is-active graphical-session.target",
        timeout=60
    )

    with subtest("KWin D-Bus service should start successfully"):
        # Service should be active
        machine.wait_until_succeeds(
            "systemctl --user -M alice@ is-active toshy-kwin-dbus.service",
            timeout=30
        )

    with subtest("KWin D-Bus service should register on D-Bus"):
        # D-Bus service name should be registered
        machine.wait_until_succeeds(
            "busctl --user -M alice@ list | grep org.toshy.Kwin",
            timeout=10
        )

    with subtest("KWin D-Bus service should have correct Type=dbus"):
        # Verify service type is dbus
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-kwin-dbus.service -p Type"
        )
        assert "Type=dbus" in output, f"Expected Type=dbus, got: {output}"

    with subtest("Service should load Python modules correctly"):
        # Check service status shows no import errors
        status = machine.succeed(
            "systemctl --user -M alice@ status toshy-kwin-dbus.service"
        )
        assert "ImportError" not in status, "Service has import errors"
        assert "ModuleNotFoundError" not in status, "Service missing modules"

    with subtest("Service should be part of graphical-session"):
        # Verify PartOf relationship
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-kwin-dbus.service -p PartOf"
        )
        assert "graphical-session.target" in output

    with subtest("Service should have correct After dependencies"):
        # Verify After= includes graphical-session.target
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-kwin-dbus.service -p After"
        )
        assert "graphical-session.target" in output

    with subtest("Service journal should show successful startup"):
        # Check journal for startup confirmation
        journal = machine.succeed(
            "journalctl --user -M alice@ -u toshy-kwin-dbus.service --no-pager"
        )
        # Should not have fatal errors
        assert "Fatal" not in journal or "fatal" not in journal.lower()
  '';
}

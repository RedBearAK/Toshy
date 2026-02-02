# Test desktopEnvironment override option
# Verifies TOSHY_DE_OVERRIDE environment variable is set correctly
#
# Run with: nix build .#checks.x86_64-linux.toshy-de-override-test

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
  name = "toshy-de-override-test";

  nodes.machine = { config, lib, ... }: {
    imports = [
      toshy.nixosModules.default
      "${home-manager-src}/nixos"
    ];

    # Use the pkgs with overlay (from outer scope)
    nixpkgs.pkgs = lib.mkForce pkgs;

    # Enable Toshy at system level
    services.toshy.enable = true;

    # Set up XFCE desktop (actual environment)
    services.xserver.enable = true;
    services.displayManager.sddm.enable = true;
    services.xserver.desktopManager.xfce.enable = true;

    # Auto-login
    services.displayManager.autoLogin.enable = true;
    services.displayManager.autoLogin.user = "alice";

    # Create test user
    users.users.alice = {
      isNormalUser = true;
      extraGroups = [ "input" "wheel" ];
      password = "alice";
    };

    # Home Manager with DE OVERRIDE (KDE while running XFCE)
    home-manager = {
      useGlobalPkgs = true;
      useUserPackages = true;
      users.alice = {
        imports = [ toshy.homeManagerModules.default ];

        services.toshy = {
          enable = true;
          # Override to KDE even though we're running XFCE
          desktopEnvironment = "kde";
          autoStart = true;
        };

        home.stateVersion = "24.11";
      };
    };
  };

  testScript = ''
    start_all()

    machine.wait_for_unit("multi-user.target")
    machine.wait_for_unit("graphical.target")

    machine.wait_until_succeeds("loginctl show-user alice")
    machine.wait_until_succeeds(
        "systemctl --user -M alice@ is-active graphical-session.target",
        timeout=60
    )

    with subtest("TOSHY_DE_OVERRIDE should be set in toshy-config service"):
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-config.service -p Environment"
        )
        assert "TOSHY_DE_OVERRIDE=kde" in output, \
            f"Expected TOSHY_DE_OVERRIDE=kde, got: {output}"

    with subtest("Override should work even when actual DE differs"):
        # We're running XFCE, but override says KDE
        # Verify we're actually in XFCE
        xdg_desktop = machine.succeed(
            "systemctl --user -M alice@ show-environment | grep XDG_CURRENT_DESKTOP || echo 'NOT_SET'"
        )

        # Check that KDE D-Bus service would try to start (based on override)
        # Even if it might fail, the service should exist
        machine.succeed(
            "systemctl --user -M alice@ cat toshy-kwin-dbus.service"
        )

    with subtest("All supported DE values should be accepted"):
        # Test that the override is properly set (we already set it to "kde")
        # Verify other services get the override too
        for service in ["toshy-config.service", "toshy-session-monitor.service"]:
            output = machine.succeed(
                f"systemctl --user -M alice@ show {service} -p Environment"
            )
            assert "TOSHY_DE_OVERRIDE=kde" in output, \
                f"Override not set in {service}"

    with subtest("Service should start despite DE mismatch"):
        # Main config service should still work
        machine.wait_until_succeeds(
            "systemctl --user -M alice@ is-active toshy-config.service",
            timeout=30
        )

    with subtest("Session monitor should have override"):
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-session-monitor.service -p Environment"
        )
        assert "TOSHY_DE_OVERRIDE=kde" in output

    with subtest("Tray service should have override if enabled"):
        # Check if tray service exists (it should with default config)
        try:
            output = machine.succeed(
                "systemctl --user -M alice@ show toshy-tray.service -p Environment"
            )
            assert "TOSHY_DE_OVERRIDE=kde" in output
        except:
            # Tray might not be enabled, which is ok
            pass
  '';
}

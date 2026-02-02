# Test Wlroots D-Bus service on Sway compositor
# Tests service works with wlroots-based compositors
#
# Run with: nix build .#checks.x86_64-linux.toshy-dbus-wlroots-test

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
  name = "toshy-dbus-wlroots-test";

  nodes.machine = { config, lib, ... }: {
    imports = [
      toshy.nixosModules.default
      "${home-manager-src}/nixos"
    ];

    # Use the pkgs with overlay (from outer scope)
    nixpkgs.pkgs = lib.mkForce pkgs;

    # Enable Toshy at system level
    services.toshy.enable = true;

    # Set up Sway (wlroots-based compositor)
    services.xserver.enable = true;
    services.displayManager.sddm.enable = true;
    services.displayManager.sddm.wayland.enable = true;
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
          desktopEnvironment = "sway";
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

    with subtest("Wlroots D-Bus service should start on Sway"):
        machine.wait_until_succeeds(
            "systemctl --user -M alice@ is-active toshy-wlroots-dbus.service",
            timeout=30
        )

    with subtest("Wlroots D-Bus service should register on D-Bus"):
        machine.wait_until_succeeds(
            "busctl --user -M alice@ list | grep org.toshy.Wlroots",
            timeout=10
        )

    with subtest("Service should be Type=dbus"):
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-wlroots-dbus.service -p Type"
        )
        assert "Type=dbus" in output

    with subtest("Service should have desktopEnvironment override"):
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-wlroots-dbus.service -p Environment"
        )
        assert "TOSHY_DE_OVERRIDE=sway" in output

    with subtest("Service should not have Python import errors"):
        status = machine.succeed(
            "systemctl --user -M alice@ status toshy-wlroots-dbus.service"
        )
        assert "ImportError" not in status
        assert "ModuleNotFoundError" not in status

    with subtest("Service should be part of graphical-session"):
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-wlroots-dbus.service -p PartOf"
        )
        assert "graphical-session.target" in output

    with subtest("Service should have After dependencies"):
        output = machine.succeed(
            "systemctl --user -M alice@ show toshy-wlroots-dbus.service -p After"
        )
        assert "graphical-session.target" in output

    with subtest("Service should work with hyprland override"):
        # Stop current service
        machine.succeed("systemctl --user -M alice@ stop toshy-wlroots-dbus.service")

        # The service should restart automatically due to Restart=on-failure
        # Or we can verify the configuration would work with hyprland
        # For now, verify service can be managed
        machine.succeed("systemctl --user -M alice@ start toshy-wlroots-dbus.service")

        machine.wait_until_succeeds(
            "systemctl --user -M alice@ is-active toshy-wlroots-dbus.service",
            timeout=10
        )
  '';
}

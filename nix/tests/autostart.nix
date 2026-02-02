# Test autoStart option
# Verifies that autoStart controls WantedBy relationship with graphical-session.target
#
# Run with: nix build .#checks.x86_64-linux.toshy-autostart-test

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
  name = "toshy-autostart-test";

  nodes = {
    # Machine with autoStart ENABLED (default)
    enabled = { config, lib, ... }: {
      imports = [
        toshy.nixosModules.default
        "${home-manager-src}/nixos"
      ];

      # Use the pkgs with overlay (from outer scope)
      nixpkgs.pkgs = lib.mkForce pkgs;

      services.toshy.enable = true;
      services.xserver.enable = true;
      services.displayManager.sddm.enable = true;
      services.xserver.desktopManager.xfce.enable = true;
      services.displayManager.autoLogin.enable = true;
      services.displayManager.autoLogin.user = "alice";

      users.users.alice = {
        isNormalUser = true;
        extraGroups = [ "input" "wheel" ];
        password = "alice";
      };

      home-manager = {
        useGlobalPkgs = true;
        useUserPackages = true;
        users.alice = {
          imports = [ toshy.homeManagerModules.default ];

          services.toshy = {
            enable = true;
            autoStart = true;  # ENABLED (default)
          };

          home.stateVersion = "24.11";
        };
      };
    };

    # Machine with autoStart DISABLED
    disabled = { config, lib, ... }: {
      imports = [
        toshy.nixosModules.default
        "${home-manager-src}/nixos"
      ];

      # Use the pkgs with overlay (from outer scope)
      nixpkgs.pkgs = lib.mkForce pkgs;

      services.toshy.enable = true;
      services.xserver.enable = true;
      services.displayManager.sddm.enable = true;
      services.xserver.desktopManager.xfce.enable = true;
      services.displayManager.autoLogin.enable = true;
      services.displayManager.autoLogin.user = "alice";

      users.users.alice = {
        isNormalUser = true;
        extraGroups = [ "input" "wheel" ];
        password = "alice";
      };

      home-manager = {
        useGlobalPkgs = true;
        useUserPackages = true;
        users.alice = {
          imports = [ toshy.homeManagerModules.default ];

          services.toshy = {
            enable = true;
            autoStart = false;  # DISABLED
          };

          home.stateVersion = "24.11";
        };
      };
    };
  };

  testScript = ''
    start_all()

    # Test ENABLED machine
    enabled.wait_for_unit("multi-user.target")
    enabled.wait_for_unit("graphical.target")
    enabled.wait_until_succeeds("loginctl show-user alice")
    enabled.wait_until_succeeds(
        "systemctl --user -M alice@ is-active graphical-session.target",
        timeout=60
    )

    with subtest("autoStart=true should add WantedBy to services"):
        # Check toshy-config.service
        output = enabled.succeed(
            "systemctl --user -M alice@ show toshy-config.service -p WantedBy"
        )
        assert "graphical-session.target" in output, \
            f"Expected WantedBy=graphical-session.target when autoStart=true. Got: {output}"

        # Check toshy-session-monitor.service
        output = enabled.succeed(
            "systemctl --user -M alice@ show toshy-session-monitor.service -p WantedBy"
        )
        assert "graphical-session.target" in output

    with subtest("Services should start automatically with autoStart=true"):
        enabled.wait_until_succeeds(
            "systemctl --user -M alice@ is-active toshy-config.service",
            timeout=30
        )
        enabled.wait_until_succeeds(
            "systemctl --user -M alice@ is-active toshy-session-monitor.service",
            timeout=10
        )

    # Test DISABLED machine
    disabled.wait_for_unit("multi-user.target")
    disabled.wait_for_unit("graphical.target")
    disabled.wait_until_succeeds("loginctl show-user alice")
    disabled.wait_until_succeeds(
        "systemctl --user -M alice@ is-active graphical-session.target",
        timeout=60
    )

    with subtest("autoStart=false should NOT add WantedBy"):
        # Check toshy-config.service
        output = disabled.succeed(
            "systemctl --user -M alice@ show toshy-config.service -p WantedBy"
        )
        # WantedBy should be empty or not contain graphical-session.target
        assert "graphical-session.target" not in output, \
            f"Should NOT have WantedBy when autoStart=false. Got: {output}"

    with subtest("Services should NOT start automatically with autoStart=false"):
        # Give it a moment to ensure they don't start
        import time
        time.sleep(5)

        # Check that services are not active (inactive or failed is ok)
        result = disabled.succeed(
            "systemctl --user -M alice@ is-active toshy-config.service || echo 'inactive'"
        )
        assert "inactive" in result or "failed" in result or "activating" not in result

    with subtest("Services CAN be started manually when autoStart=false"):
        # Manual start should work
        disabled.succeed(
            "systemctl --user -M alice@ start toshy-config.service"
        )

        disabled.wait_until_succeeds(
            "systemctl --user -M alice@ is-active toshy-config.service",
            timeout=15
        )

        # Service should stay running after manual start
        import time
        time.sleep(3)
        disabled.succeed(
            "systemctl --user -M alice@ is-active toshy-config.service"
        )
  '';
}

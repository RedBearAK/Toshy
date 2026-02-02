# Test custom config path option
# Verifies that services.toshy.config = ./custom_config.py is respected
#
# Run with: nix build .#checks.x86_64-linux.toshy-config-custom-test

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
  name = "toshy-config-custom-test";

  nodes.machine = { config, lib, ... }: {
    imports = [
      toshy.nixosModules.default
      "${home-manager-src}/nixos"
    ];

    # Use the pkgs with overlay (from outer scope)
    nixpkgs.pkgs = lib.mkForce pkgs;

    # Enable Toshy at system level
    services.toshy.enable = true;

    # Set up minimal X11 environment for testing
    services.xserver.enable = true;
    services.displayManager.sddm.enable = true;
    services.xserver.desktopManager.xfce.enable = true;

    # Auto-login for testing
    services.displayManager.autoLogin.enable = true;
    services.displayManager.autoLogin.user = "alice";

    # Create test user
    users.users.alice = {
      isNormalUser = true;
      extraGroups = [ "input" "wheel" ];
      password = "alice";
    };

    # Home Manager configuration with CUSTOM config
    home-manager = {
      useGlobalPkgs = true;
      useUserPackages = true;
      users.alice = {
        imports = [ toshy.homeManagerModules.default ];

        services.toshy = {
          enable = true;
          # Use custom config file
          config = ./fixtures/test-config.py;
          autoStart = true;
        };

        home.stateVersion = "24.11";
      };
    };
  };

  testScript = ''
    start_all()

    # Wait for system
    machine.wait_for_unit("multi-user.target")
    machine.wait_for_unit("graphical.target")

    # Wait for user session
    machine.wait_until_succeeds("loginctl show-user alice")
    machine.wait_until_succeeds(
        "systemctl --user -M alice@ is-active graphical-session.target",
        timeout=60
    )

    with subtest("Custom config should be passed to xwaykeyz"):
        # Get the ExecStart command from the service
        output = machine.succeed(
            "systemctl --user -M alice@ cat toshy-config.service"
        )

        # Should NOT contain the default config path
        assert "toshy_config.py" not in output or "test-config.py" in output, \
            "Service should use custom config, not default"

        # Should contain reference to custom config
        # The exact path will be in /nix/store, but should have test-config.py
        assert "test-config.py" in output, \
            f"Custom config path not found in service. Output:\n{output}"

    with subtest("Service should start with custom config"):
        machine.wait_until_succeeds(
            "systemctl --user -M alice@ is-active toshy-config.service",
            timeout=30
        )

    with subtest("Custom config should actually be loaded"):
        # Check journal for our marker print statement
        journal = machine.succeed(
            "journalctl --user -M alice@ -u toshy-config.service --no-pager"
        )

        # Our test config prints a marker message
        assert "TEST CONFIG: Custom Toshy test config loaded" in journal or \
               "CUSTOM_TEST_CONFIG_LOADED" in journal, \
            f"Custom config marker not found in journal. Journal:\n{journal}"

    with subtest("Service should not have import errors with custom config"):
        status = machine.succeed(
            "systemctl --user -M alice@ status toshy-config.service"
        )
        assert "ImportError" not in status
        assert "ModuleNotFoundError" not in status
        # Should be active (running)
        assert "active (running)" in status or "Active: active" in status
  '';
}

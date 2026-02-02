# Test verboseLogging option
# Verifies that verboseLogging = true adds "-v" flag to xwaykeyz
#
# Run with: nix build .#checks.x86_64-linux.toshy-verbose-logging-test

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
  name = "toshy-verbose-logging-test";

  nodes = {
    # Machine with verbose logging ENABLED
    verbose = { config, lib, ... }: {
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
            verboseLogging = true;  # ENABLED
            autoStart = true;
          };

          home.stateVersion = "24.11";
        };
      };
    };

    # Machine with verbose logging DISABLED (default)
    quiet = { config, lib, ... }: {
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
            verboseLogging = false;  # DISABLED (default)
            autoStart = true;
          };

          home.stateVersion = "24.11";
        };
      };
    };
  };

  testScript = ''
    start_all()

    # Test VERBOSE machine
    verbose.wait_for_unit("multi-user.target")
    verbose.wait_for_unit("graphical.target")
    verbose.wait_until_succeeds("loginctl show-user alice")
    verbose.wait_until_succeeds(
        "systemctl --user -M alice@ is-active graphical-session.target",
        timeout=60
    )

    with subtest("Verbose logging should add -v flag to ExecStart"):
        output = verbose.succeed(
            "systemctl --user -M alice@ cat toshy-config.service"
        )
        # Should contain -v flag in the xwaykeyz command
        assert " -v " in output or " -v" in output, \
            f"Expected -v flag in ExecStart when verboseLogging=true. Output:\n{output}"

    with subtest("Service should start successfully with verbose flag"):
        verbose.wait_until_succeeds(
            "systemctl --user -M alice@ is-active toshy-config.service",
            timeout=30
        )

    with subtest("Journal should show increased verbosity"):
        journal = verbose.succeed(
            "journalctl --user -M alice@ -u toshy-config.service --no-pager"
        )
        # Verbose mode should produce more output
        assert len(journal) > 100, "Verbose logging should produce output"

    # Test QUIET machine
    quiet.wait_for_unit("multi-user.target")
    quiet.wait_for_unit("graphical.target")
    quiet.wait_until_succeeds("loginctl show-user alice")
    quiet.wait_until_succeeds(
        "systemctl --user -M alice@ is-active graphical-session.target",
        timeout=60
    )

    with subtest("Default (no verbose) should NOT have -v flag"):
        output = quiet.succeed(
            "systemctl --user -M alice@ cat toshy-config.service"
        )
        # Should NOT contain -v flag
        # Need to be careful: file paths might contain 'v'
        # Check that there's no standalone -v flag
        lines = output.split('\n')
        exec_start_lines = [l for l in lines if 'ExecStart' in l]
        assert len(exec_start_lines) > 0, "No ExecStart found"

        # Check the actual command doesn't have -v as an argument
        for line in exec_start_lines:
            # Extract the command part after '='
            if 'ExecStart=' in line:
                cmd = line.split('ExecStart=', 1)[1]
                # Split into args and check for -v
                args = cmd.split()
                assert '-v' not in args, \
                    f"Should not have -v flag when verboseLogging=false. Found in: {line}"

    with subtest("Service should start successfully without verbose flag"):
        quiet.wait_until_succeeds(
            "systemctl --user -M alice@ is-active toshy-config.service",
            timeout=30
        )
  '';
}

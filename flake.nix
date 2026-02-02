{
  description = "Toshy - macOS-to-Linux keyboard remapping for X11 and Wayland";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, home-manager }:
    let
      # Overlay at top level (not per-system)
      overlay = final: prev: {
        xwaykeyz = final.python3Packages.callPackage ./nix/packages/xwaykeyz.nix { };
        toshy = final.callPackage ./nix/packages/toshy.nix {
          inherit (final) xwaykeyz;
          src = self;  # Use flake's local source instead of fetching from GitHub
        };
        gnome-shell-extension-focused-window-dbus = final.callPackage ./nix/packages/gnome-shell-extension-focused-window-dbus.nix { };
      };
    in
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ overlay ];
        };

        python = pkgs.python3;
        pythonPackages = python.pkgs;

      in
      {
        packages = {
          inherit (pkgs) xwaykeyz toshy gnome-shell-extension-focused-window-dbus;
          default = pkgs.toshy;
        };

        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python
            git
            nix-prefetch-git
            toshy
            xwaykeyz
          ];
        };

        # Integration tests
        checks = {
          # Basic system-level test
          toshy-basic-test = import ./nix/tests/basic.nix {
            inherit pkgs;
            self = null;
          };

          # Home-manager integration test
          toshy-home-manager-test = import ./nix/tests/home-manager.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          # Multi-DE test
          toshy-multi-de-test = import ./nix/tests/multi-de.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          # Legacy integration test (keeping for compatibility)
          toshy-integration-test = import ./nix/tests/integration.nix {
            inherit pkgs system;
            self = null;
          };

          # D-Bus service tests (Phase 1 - Priority 1)
          toshy-dbus-kwin-test = import ./nix/tests/dbus-kwin.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          toshy-dbus-cosmic-test = import ./nix/tests/dbus-cosmic.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          toshy-dbus-wlroots-test = import ./nix/tests/dbus-wlroots.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          # Configuration option tests (Phase 2 - Priority 1)
          toshy-config-custom-test = import ./nix/tests/config-custom.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          toshy-de-override-test = import ./nix/tests/de-override.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          toshy-verbose-logging-test = import ./nix/tests/verbose-logging.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          toshy-autostart-test = import ./nix/tests/autostart.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          # Production-readiness tests (Priority 1 - Critical for "seamless like Ubuntu")
          toshy-e2e-installation-test = import ./nix/tests/e2e-installation.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          toshy-error-handling-test = import ./nix/tests/error-handling.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          toshy-multi-user-test = import ./nix/tests/multi-user.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          toshy-rollback-test = import ./nix/tests/rollback.nix {
            inherit pkgs;
            self = null;
            home-manager = null;
          };

          # Setup script CLI integration (tests what was being skipped in unit tests)
          toshy-setup-cli-integration-test = import ./nix/tests/setup-cli-integration.nix {
            inherit pkgs;
            self = null;
          };
        };
      }
    ) // {
      # Overlay at top level
      overlays.default = overlay;

      # Home Manager module (available on all systems)
      homeManagerModules.default = import ./nix/modules/home-manager.nix;
      homeManagerModules.toshy = import ./nix/modules/home-manager.nix;

      # NixOS module (optional, for system-wide installation)
      nixosModules.default = import ./nix/modules/nixos.nix;
      nixosModules.toshy = import ./nix/modules/nixos.nix;
    };
}

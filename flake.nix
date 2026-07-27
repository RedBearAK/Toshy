# Repo location: toshy/flake.nix
#
# EXPERIMENTAL Nix flake for Toshy. See nix/README.md before using.
#
# Provides:
#   - packages.<system>.toshy-runtime            (wrapped Python env, vendored
#                                                 keymapper from the "main" copy)
#   - packages.<system>.toshy-runtime-dev-beta   (same, "dev_beta" vendored copy)
#   - nixosModules.toshy                         (udev rules, uinput, group)
#   - homeManagerModules.toshy                   (runtime link in the state dir)
#
# The user-level files (config, launchers, services) are NOT installed by this
# flake. After applying the modules, run from a checkout of this repo:
#
#   ~/.local/state/toshy/runtime/bin/python ./setup_toshy.py install-user-files

{
  description = "Toshy - Mac-style keyboard remapping for Linux (EXPERIMENTAL Nix support)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems
        (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAllSystems (pkgs: rec {
        toshy-runtime = pkgs.callPackage ./nix/toshy-runtime.nix {
          toshySrc = self;
          keymapperBranch = "main";
        };

        toshy-runtime-dev-beta = pkgs.callPackage ./nix/toshy-runtime.nix {
          toshySrc = self;
          keymapperBranch = "dev_beta";
        };

        default = toshy-runtime;
      });

      nixosModules = rec {
        toshy = import ./nix/nixos-module.nix;
        default = toshy;
      };

      homeManagerModules = rec {
        toshy = { pkgs, lib, ... }: {
          imports = [ ./nix/hm-module.nix ];
          # Default runtime is the "main" vendored keymapper variant. Override
          # services.toshy.runtimePackage to use toshy-runtime-dev-beta.
          services.toshy.runtimePackage = lib.mkDefault
            self.packages.${pkgs.stdenv.hostPlatform.system}.toshy-runtime;
        };
        default = toshy;
      };
    };
}

# End of file #

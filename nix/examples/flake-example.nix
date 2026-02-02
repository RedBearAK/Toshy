# Complete flake.nix example showing how to use Toshy with home-manager
#
# This is a complete, standalone flake that you can use as a template
# for your own NixOS or home-manager configuration.

{
  description = "My NixOS configuration with Toshy";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Add Toshy as an input
    toshy = {
      url = "github:RedBearAK/toshy";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, home-manager, toshy, ... }: {
    # NixOS configuration
    nixosConfigurations.my-machine = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        # Your hardware configuration
        # ./hardware-configuration.nix

        # Apply Toshy overlay (REQUIRED - makes pkgs.toshy and pkgs.xwaykeyz available)
        ({ config, pkgs, ... }: {
          nixpkgs.overlays = [ toshy.overlays.default ];
        })

        # Optional: Enable Toshy system-wide (udev rules, kernel modules)
        toshy.nixosModules.default
        {
          services.toshy.enable = true;
        }

        # Home-manager integration
        home-manager.nixosModules.home-manager
        {
          home-manager.useGlobalPkgs = true;
          home-manager.useUserPackages = true;

          # Make Toshy home-manager module available to all users
          home-manager.sharedModules = [
            toshy.homeManagerModules.default
          ];

          home-manager.users.myuser = { config, pkgs, ... }: {
            # Enable Toshy for this user
            services.toshy = {
              enable = true;
              autoStart = true;
              enableGui = true;
            };

            home.stateVersion = "24.05";
          };
        }
      ];
    };

    # Standalone home-manager configuration (without NixOS)
    homeConfigurations.myuser = home-manager.lib.homeManagerConfiguration {
      # Apply overlay to make pkgs.toshy available
      pkgs = import nixpkgs {
        system = "x86_64-linux";
        overlays = [ toshy.overlays.default ];
      };

      modules = [
        toshy.homeManagerModules.default
        {
          services.toshy = {
            enable = true;
            autoStart = true;
            enableGui = true;
          };

          home = {
            username = "myuser";
            homeDirectory = "/home/myuser";
            stateVersion = "24.05";
          };
        }
      ];
    };
  };
}

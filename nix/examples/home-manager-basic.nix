# Basic Toshy configuration using home-manager
# Add this to your home.nix or home-manager configuration

{ config, pkgs, ... }:

{
  # IMPORTANT: Add Toshy to your flake.nix inputs:
  #
  # inputs.toshy.url = "github:RedBearAK/toshy";
  #
  # Apply the overlay (REQUIRED):
  # nixpkgs.overlays = [ toshy.overlays.default ];
  #
  # Import the home-manager module:
  # home-manager.sharedModules = [ toshy.homeManagerModules.default ];
  #
  # See nix/examples/flake-example.nix for complete setup

  services.toshy = {
    enable = true;

    # Auto-start on login (default: true)
    autoStart = true;

    # Enable GUI components (tray icon and preferences app)
    enableGui = true;
    enableTray = true;

    # Use custom config (optional)
    # config = ./my-toshy-config.py;

    # Verbose logging for debugging (default: false)
    verboseLogging = false;
  };
}

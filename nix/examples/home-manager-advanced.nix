# Advanced Toshy configuration using home-manager
# This example shows all available options

{ config, pkgs, ... }:

{
  services.toshy = {
    enable = true;

    # Use a specific version of Toshy (optional)
    # package = pkgs.toshy.override { ... };

    # Custom configuration file
    # Option 1: Copy default config to home directory and customize it
    config = "${config.home.homeDirectory}/.config/toshy/toshy_config.py";

    # Auto-start configuration
    autoStart = true;

    # GUI options
    enableGui = true;    # Enable preferences app (adds toshy-gui command)
    enableTray = false;  # Disable tray icon (useful for headless or minimal setups)

    # Override desktop environment detection
    # Useful if auto-detection doesn't work correctly
    # Options: "kde", "gnome", "cosmic", "sway", "hyprland", "xfce", "cinnamon"
    desktopEnvironment = "gnome";

    # Enable verbose logging (useful for debugging)
    verboseLogging = true;
  };

  # Copy default config to home directory so you can customize it
  # This makes it easy to edit your config while keeping it declarative
  home.file.".config/toshy/toshy_config.py".source =
    "${pkgs.toshy}/share/toshy/default-toshy-config/toshy_config.py";

  # Alternative: Use a config file from your repo
  # home.file.".config/toshy/toshy_config.py".source = ./my-toshy-config.py;

  # Optional: Install additional tools
  home.packages = with pkgs; [
    evtest  # For debugging input devices
  ];
}

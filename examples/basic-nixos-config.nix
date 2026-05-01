# Example NixOS flake configuration with Toshy
#
# This shows how to add the Toshy flake to a NixOS system configuration
# and enable Mac-style keybindings.
{
  description = "Example NixOS configuration with Toshy";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    toshy = {
      url = "github:celesrenata/toshy";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, toshy }: {
    nixosConfigurations.example = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        # Import the Toshy NixOS module
        toshy.nixosModules.toshy

        # Your system configuration
        ({ config, pkgs, ... }: {

          # ── Minimal Toshy setup ───────────────────────────────────
          # Just enable and set the user — everything else has sensible
          # defaults. Toshy auto-detects your compositor (X11, Wayland,
          # KDE, GNOME, Sway, Hyprland, COSMIC, etc.) at runtime.
          services.toshy = {
            enable = true;
            user   = "alice";  # Replace with your username
          };

          # ── Optional: override the Toshy package ──────────────────
          # services.toshy.package = pkgs.toshy;

          # ── Optional: use a custom config file ────────────────────
          # Provide your own toshy_config.py instead of the upstream
          # default. This is a full replacement — extraConfig is ignored
          # when configFile is set.
          # services.toshy.configFile = /etc/toshy/my_config.py;

          # ── Optional: append extra Python code to the config ──────
          # This is appended to the end of the upstream default config.
          # Useful for adding custom keymaps without replacing the
          # entire 5700-line config file.
          # services.toshy.extraConfig = ''
          #   # Add a custom keymap
          #   keymap("MyApp", {
          #       C("c"): C("ctrl-c"),
          #   })
          # '';

          # ── Optional: install GUI desktop files ───────────────────
          # Adds the Toshy tray icon and preferences app to your
          # application menu. Off by default.
          # services.toshy.gui.enable = true;

          # ── Optional: install KWin script (KDE Plasma only) ───────
          # Installs the KWin script that sends window-focus events to
          # the Toshy KWin D-Bus service. Only needed on KDE Plasma.
          # services.toshy.kwinScript.enable = true;

          # ── Your user account ─────────────────────────────────────
          # The module automatically adds this user to the `input`
          # group and installs udev rules for evdev device access.
          users.users.alice = {
            isNormalUser = true;
            extraGroups  = [ "wheel" ];
          };

          system.stateVersion = "24.11";
        })
      ];
    };
  };
}

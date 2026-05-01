# Example Home Manager configuration with Toshy
#
# This shows how to enable Toshy at the user level using Home Manager.
# No system-level NixOS configuration is required (though the user must
# be in the `input` group for evdev access — see note at the bottom).
#
# In your flake.nix, add the Toshy input and pass the module:
#
#   inputs.toshy = {
#     url = "github:celesrenata/toshy";
#     inputs.nixpkgs.follows = "nixpkgs";
#   };
#
# Then in your Home Manager configuration:
#
#   imports = [ inputs.toshy.homeManagerModules.toshy ];
#
{ config, pkgs, ... }:

{
  # ── Minimal Toshy setup ─────────────────────────────────────────
  # Just enable — Toshy auto-detects your compositor at runtime.
  services.toshy = {
    enable = true;
  };

  # ── Optional: override the Toshy package ────────────────────────
  # services.toshy.package = pkgs.toshy;

  # ── Optional: use a custom config file ──────────────────────────
  # Provide your own toshy_config.py. When set, the file is symlinked
  # into ~/.config/toshy/ and extraConfig is ignored.
  # services.toshy.configFile = ./my_toshy_config.py;

  # ── Optional: append extra Python code to the config ────────────
  # Appended to the end of the upstream default config. Useful for
  # adding custom keymaps without replacing the entire file.
  # services.toshy.extraConfig = ''
  #   # Add a custom keymap
  #   keymap("MyApp", {
  #       C("c"): C("ctrl-c"),
  #   })
  # '';

  # ── Optional: install GUI desktop files ─────────────────────────
  # Adds the Toshy tray icon and preferences app to your application
  # menu. Off by default.
  # services.toshy.gui.enable = true;

  # ── Optional: install KWin script (KDE Plasma only) ─────────────
  # Installs the KWin script for window-focus notifications.
  # services.toshy.kwinScript.enable = true;

  # NOTE: Toshy requires the user to be in the `input` group for
  # evdev device access. With Home Manager standalone (no NixOS
  # module), you need to ensure this at the system level:
  #
  #   users.users.alice.extraGroups = [ "input" ];
  #
  # The NixOS module handles this automatically, but Home Manager
  # cannot modify system-level group membership.
}

# NixOS Quick Start (3 Steps)

**As seamless as Ubuntu.** 🎉

This is the **recommended installation method** for NixOS. Just add to your configuration and rebuild - no manual editing required!

---

## Prerequisites

- NixOS with flakes enabled
- home-manager configured
- User in the `input` group (done automatically by the module)

---

## 1. Add to flake.nix

Add Toshy as an input and import the modules:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    toshy.url = "github:RedBearAK/toshy";
    # For local development: toshy.url = "path:/path/to/toshy";

    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, toshy, home-manager, ... }: {
    nixosConfigurations.my-machine = nixpkgs.lib.nixosSystem {
      modules = [
        # Apply Toshy overlay (REQUIRED - makes pkgs.toshy available)
        ({ config, pkgs, ... }: {
          nixpkgs.overlays = [ toshy.overlays.default ];
        })

        # Enable Toshy system-wide (udev rules, kernel modules, user groups)
        toshy.nixosModules.default
        {
          services.toshy.enable = true;
        }

        # Home Manager configuration
        home-manager.nixosModules.home-manager
        {
          home-manager.useGlobalPkgs = true;
          home-manager.useUserPackages = true;

          # Make Toshy home-manager module available to all users
          home-manager.sharedModules = [
            toshy.homeManagerModules.default
          ];

          # Configure for your user
          home-manager.users.YOUR_USERNAME = {
            services.toshy = {
              enable = true;
              autoStart = true;
            };
          };
        }
      ];
    };
  };
}
```

**Replace `YOUR_USERNAME`** with your actual username.

---

## 2. Rebuild

Apply the configuration:

```bash
sudo nixos-rebuild switch --flake .#
```

---

## 3. Log out and log in

Log out and log back in to start the Toshy services.

**Done!** 🎉 Toshy is now active.

---

## Verification

Check that services are running:

```bash
systemctl --user status toshy-config.service
systemctl --user status toshy-session-monitor.service
```

You should see both services as `active (running)`.

---

## Customization (Optional)

### Complete Example with All Options

```nix
home-manager.users.YOUR_USERNAME = {
  services.toshy = {
    enable = true;
    autoStart = true;           # Auto-start on login (default: true)
    enableGui = true;            # Enable toshy-gui preferences app (default: true)
    enableTray = false;          # Disable tray icon (default: true)
    desktopEnvironment = "gnome"; # Override auto-detection
    verboseLogging = true;       # Enable debug output (default: false)

    # Use custom config file
    config = "${config.home.homeDirectory}/.config/toshy/toshy_config.py";
  };

  # Copy default config to customize it
  home.file.".config/toshy/toshy_config.py".source =
    "${pkgs.toshy}/share/toshy/default-toshy-config/toshy_config.py";
};
```

### Minimal Setup (Just the Essentials)

```nix
home-manager.users.YOUR_USERNAME = {
  services.toshy = {
    enable = true;
    # All other options use sensible defaults
  };
};
```

### Desktop Environment Override

If auto-detection doesn't work correctly:

```nix
services.toshy = {
  enable = true;
  desktopEnvironment = "kde";  # Options: "kde", "gnome", "cosmic", "sway", "hyprland", "xfce", "cinnamon"
};
```

### Custom Configuration File

```nix
services.toshy = {
  enable = true;
  config = ./my-toshy-config.py;  # Path to your custom config
};
```

### Headless/Server Setup (No GUI)

```nix
services.toshy = {
  enable = true;
  enableGui = false;   # Disable GUI components
  enableTray = false;  # Disable tray icon
};
```

---

## Why This is Seamless

| Ubuntu                      | NixOS Flake                  |
|-----------------------------|------------------------------|
| `./setup_toshy.py install`  | `nixos-rebuild switch`       |
| Packages auto-install       | Packages auto-install        |
| Services auto-start         | Services auto-start          |
| One command setup           | One command setup            |
| ✅ Seamless                 | ✅ Seamless                  |

Plus NixOS benefits:
- **Instant rollback** if something breaks
- **Reproducible** across all your machines
- **Declarative** - your entire config in one place
- **No manual steps** - everything automated

---

## Troubleshooting

### Services not starting?

Check logs:
```bash
journalctl --user -u toshy-config.service -f
```

### Wrong desktop environment detected?

Override it:
```nix
services.toshy.desktopEnvironment = "kde";  # or "gnome", "sway", "hyprland", etc.
```

### Need more help?

See the full documentation:
- [NIX_FLAKE_INSTALLATION.md](NIX_FLAKE_INSTALLATION.md) - Complete guide
- [README.md](README.md) - Main documentation
- [GitHub Issues](https://github.com/RedBearAK/toshy/issues) - Report issues

---

**Enjoy your macOS-style keyboard shortcuts on Linux!** 🚀

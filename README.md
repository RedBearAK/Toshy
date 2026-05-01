# Toshy for NixOS

Nix flake for [Toshy](https://github.com/RedBearAK/toshy) — Mac-style keybindings for Linux.

This flake packages Toshy and its keymapper engine [xwaykeyz](https://github.com/RedBearAK/xwaykeyz) for NixOS, providing a NixOS module, a Home Manager module, and standalone packages. The Toshy source is fetched directly from the upstream repository.

## Quick start

Add the flake input to your `flake.nix`:

```nix
{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    toshy = {
      url = "github:celesrenata/toshy/flake-rewrite";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };
}
```

### NixOS module

Import the module and enable the service:

```nix
# In your NixOS configuration
{
  imports = [ toshy.nixosModules.toshy ];

  services.toshy = {
    enable = true;
    user = "alice";       # required — the user who runs Toshy
    gui.enable = true;    # optional — installs tray icon and preferences app
  };
}
```

The module handles everything automatically:
- Installs the Toshy package and xwaykeyz
- Creates five systemd user services (config, session-monitor, kwin-dbus, wlroots-dbus, cosmic-dbus)
- Optionally creates a tray icon service when `gui.enable = true`
- Installs udev rules and adds the user to the `input` group
- Seeds `~/.config/toshy/` with the default config and helper scripts
- Symlinks helper scripts into `~/.local/bin/` for the preferences app

### Home Manager module

```nix
{
  imports = [ toshy.homeManagerModules.toshy ];

  services.toshy = {
    enable = true;
    gui.enable = true;
  };
}
```

The Home Manager module provides the same services but manages the config file via `xdg.configFile` and does not handle udev rules (those require system-level access).

> **Note:** With Home Manager standalone (no NixOS module), you need to add your user to the `input` group at the system level: `users.users.alice.extraGroups = [ "input" ];`

## Options

### NixOS module

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `services.toshy.enable` | bool | `false` | Enable Toshy services |
| `services.toshy.user` | string | (required) | User to run Toshy as |
| `services.toshy.package` | package | flake default | Override the Toshy package |
| `services.toshy.configFile` | path or null | `null` | Custom `toshy_config.py` |
| `services.toshy.extraConfig` | lines | `""` | Python code appended to the default config |
| `services.toshy.gui.enable` | bool | `false` | Install tray icon and preferences desktop files |
| `services.toshy.kwinScript.enable` | bool | `false` | Install KWin script for KDE Plasma |

### Home Manager module

Same options minus `user` (implicit) and udev rules (system-level).

## Keyboard type

Toshy auto-detects your keyboard type. If your keyboard is misidentified, edit `~/.config/toshy/toshy_config.py` and add your device to the `keyboards_UserCustom_dct` dictionary:

```python
keyboards_UserCustom_dct = {
    'Logitech USB Receiver': 'Apple',
    'My Keyboard Name': 'Apple',  # or 'Windows', 'IBM', 'Chromebook'
}
```

Then restart the config service: `systemctl --user restart toshy-config`

## Packages

The flake exposes standalone packages for use without the module:

```bash
# Build Toshy
nix build github:celesrenata/toshy/flake-rewrite#toshy

# Build xwaykeyz
nix build github:celesrenata/toshy/flake-rewrite#xwaykeyz

# Run xwaykeyz directly
nix run github:celesrenata/toshy/flake-rewrite#xwaykeyz -- --version
```

## Overlay

Add Toshy and xwaykeyz to your nixpkgs:

```nix
nixpkgs.overlays = [ toshy.overlays.default ];
```

This adds `pkgs.toshy` and `pkgs.xwaykeyz` to your package set.

## Development

```bash
nix develop  # enters a shell with Python, setuptools, and dev tools
```

## Architecture

The flake fetches the Toshy source from the upstream [RedBearAK/toshy](https://github.com/RedBearAK/toshy) repository (pinned to a release tag) and overlays a `pyproject.toml` for `buildPythonApplication`. The `pyproject.toml` is designed for upstream contribution.

Key components:
- **`nix/python-overlay.nix`** — Pins `python-xlib` to 0.31 and `xkbcommon` to <1.1 (upstream requirements), adds `hyprpy` from PyPI
- **`nix/xwaykeyz.nix`** — Packages xwaykeyz from GitHub with hatchling
- **`nix/hyprpy.nix`** — Packages hyprpy from PyPI (not yet in nixpkgs)
- **`modules/toshy.nix`** — NixOS module with systemd services and activation script
- **`home-manager/toshy.nix`** — Home Manager module

## Upstream

This flake tracks [RedBearAK/toshy](https://github.com/RedBearAK/toshy). To update to a new upstream release, change the `rev` and `hash` in `flake.nix`:

```nix
toshySrc = pkgs.fetchFromGitHub {
  owner = "RedBearAK";
  repo = "toshy";
  rev = "Toshy_v26.03.0";  # ← update tag
  hash = "sha256-...";      # ← update hash
};
```

## License

GPL-3.0-or-later, matching upstream Toshy.

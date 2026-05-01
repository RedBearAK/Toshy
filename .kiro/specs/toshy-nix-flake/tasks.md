# Implementation Plan: toshy-nix-flake

## Overview

This plan implements the official Nix flake for Toshy as a clean rewrite, replacing the existing port. The work is ordered for incremental buildability: first the Python overlay and dependency packages (xwaykeyz, hyprpy), then the pyproject.toml and main Toshy package, then the NixOS and Home Manager modules, then cleanup of old files. Each task produces a verifiable artifact before moving to the next.

All code is Nix (flake.nix, module definitions, package derivations) and Python (pyproject.toml), matching the design document.

## Tasks

- [x] 1. Create Python overlay for version pinning
  - [x] 1.1 Create `nix/python-overlay.nix` with python-xlib 0.31 override
    - Override `python-xlib` to version 0.31 using `overridePythonAttrs` with `fetchPypi`
    - Include comment explaining the `BadRRModeError` bug and link to upstream issue
    - _Requirements: 8.1, 8.2_
  - [x] 1.2 Add xkbcommon <1.1 override to the Python overlay
    - Override `xkbcommon` to a version below 1.1 (e.g., 0.8) using `overridePythonAttrs` with `fetchPypi`
    - Include comment explaining the breaking API changes in 1.5+
    - _Requirements: 8.3_
  - [x] 1.3 Add hyprpy package definition to the Python overlay
    - Create `nix/hyprpy.nix` as a standalone `buildPythonPackage` fetching from PyPI
    - Import and add hyprpy to the overlay in `nix/python-overlay.nix`
    - _Requirements: 9.1, 9.2_

- [x] 2. Package xwaykeyz from GitHub
  - [x] 2.1 Create `nix/xwaykeyz.nix` package definition
    - Use `buildPythonPackage` with `format = "pyproject"` and `hatchling` build system
    - Fetch source from GitHub using `fetchFromGitHub` pinned to a specific release tag (NOT `main` branch)
    - Declare all propagated dependencies: appdirs, dbus-python, evdev, i3ipc, inotify-simple, ordered-set, pywayland, python-xlib (from overlay), hyprpy (from overlay)
    - Ensure `$out/bin/xwaykeyz` binary is produced
    - Do NOT use `catchConflicts = false` or `dontCheckRuntimeDeps = true`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 3. Checkpoint — Verify dependency packages build
  - Ensure `nix build .#xwaykeyz` succeeds without `catchConflicts = false` or `dontCheckRuntimeDeps = true`. Ask the user if questions arise.

- [x] 4. Create pyproject.toml for upstream contribution
  - [x] 4.1 Rewrite `pyproject.toml` for upstream Toshy repo structure
    - Use `setuptools` as build backend with `[build-system] requires = ["setuptools>=61.0", "wheel"]`
    - Declare `toshy_common*` and `toshy_gui*` in `[tool.setuptools.packages.find]` include list
    - Declare `toshy_tray` and `toshy_layout_selector` as `py-modules`
    - Declare console script entry points: `toshy-tray = "toshy_tray:main"`, `toshy-gui = "toshy_gui.__main__:main"`, `toshy-layout-selector = "toshy_layout_selector:main"`
    - Declare all runtime dependencies matching upstream requirements.txt
    - Declare package-data with glob patterns for `default-toshy-config/`, `assets/`, `desktop/`, `systemd-user-service-units/`, `scripts/`, `kwin-dbus-service/`, `wlroots-dbus-service/`, `cosmic-dbus-service/`, `kwin-script/`
    - Design for upstream contribution — not a Nix-only artifact
    - Remove all references to the old `toshy/` wrapper package (no `toshy.tray`, `toshy.daemon`, etc.)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.9_

- [x] 5. Rewrite flake.nix with Toshy package and all outputs
  - [x] 5.1 Write the main `flake.nix` structure with inputs and system iteration
    - Declare `nixpkgs` and `flake-utils` inputs
    - Use `eachSystem` for `x86_64-linux` and `aarch64-linux`
    - Apply the Python overlay from `nix/python-overlay.nix` to the Python package set
    - Import xwaykeyz from `nix/xwaykeyz.nix`
    - _Requirements: 10.1, 10.2, 10.3, 11.1, 11.2_
  - [x] 5.2 Define the Toshy package using `buildPythonApplication`
    - Use `format = "pyproject"` with the new `pyproject.toml`
    - Source from local `./.` (the flake source)
    - Add native build inputs: `setuptools`, `wheel`, `wrapGAppsHook`, `gobject-introspection`
    - Add build inputs: `gtk3`, `gtk4`, `gobject-introspection`, `libappindicator-gtk3`, `libayatana-appindicator`, `libnotify`, `libadwaita`, `gsettings-desktop-schemas`
    - Add all propagated build inputs (Python runtime deps + xwaykeyz)
    - Do NOT use `catchConflicts = false` or `dontCheckRuntimeDeps = true`
    - _Requirements: 2.7, 2.8, 14.1, 14.4_
  - [x] 5.3 Add shell script wrapping in the Toshy package's `postInstall` phase
    - Wrap `tshysvc-config` with PATH including xwaykeyz/bin, coreutils, procps, xorg.xhost, xorg.xset, bash
    - Wrap `tshysvc-sessmon` with PATH including coreutils, systemd, procps, bash
    - Create Python wrapper scripts for D-Bus services (toshy-kwin-dbus-service, toshy-wlroots-dbus-service, toshy-cosmic-dbus-service) with correct PYTHONPATH
    - Ensure wrapped scripts replace venv activation with PATH/PYTHONPATH setup
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [x] 5.4 Add desktop files and icons installation to the Toshy package
    - Install `.desktop` files from `desktop/` to `$out/share/applications/`
    - Install icons from `assets/` to `$out/share/icons/` following XDG icon theme spec
    - Install Toshy icon theme from `assets/Toshy-Icon-Theme/` to `$out/share/icons/Toshy-Icon-Theme/`
    - Patch desktop file `Exec=` lines to use Nix store paths
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  - [x] 5.5 Define all flake outputs
    - Expose `packages.<system>.toshy`, `packages.<system>.xwaykeyz`, `packages.<system>.default`
    - Expose `nixosModules.toshy`, `nixosModules.default`
    - Expose `homeManagerModules.toshy`, `homeManagerModules.default`
    - Expose `overlays.default` that adds toshy and xwaykeyz to the package set
    - Expose `devShells.<system>.default` for development
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

- [x] 6. Checkpoint — Verify Toshy package builds
  - Ensure `nix build .#toshy` succeeds without `catchConflicts = false` or `dontCheckRuntimeDeps = true`. Verify that `$out/bin/tshysvc-config`, `$out/bin/tshysvc-sessmon`, and D-Bus service wrappers exist. Ask the user if questions arise.

- [x] 7. Rewrite NixOS module
  - [x] 7.1 Rewrite `modules/toshy.nix` with minimal correct options
    - Define exactly 7 options: `enable`, `package`, `user`, `configFile`, `extraConfig`, `gui.enable`, `kwinScript.enable`
    - Remove ALL old options: `keybindings.*`, `wayland.*`, `x11.*`, `logging.*`, `security.*`, `performance.*`, `gui.tray`, `gui.theme`, `gui.autostart`, `gui.fileManager`, `gui.terminal`
    - Add assertion that `services.toshy.user` must be non-empty
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_
  - [x] 7.2 Create the five systemd user services in the NixOS module
    - `toshy-config.service`: ExecStart = `${pkg}/bin/tshysvc-config`, WantedBy = `default.target`, Restart = always
    - `toshy-session-monitor.service`: ExecStart = `${pkg}/bin/tshysvc-sessmon`, WantedBy = `default.target`, Restart = always
    - `toshy-kwin-dbus.service`: ExecStart = `${pkg}/bin/toshy-kwin-dbus-service`, WantedBy = `default.target`, Restart = on-failure
    - `toshy-wlroots-dbus.service`: ExecStart = `${pkg}/bin/toshy-wlroots-dbus-service`, WantedBy = `default.target`, Restart = on-failure
    - `toshy-cosmic-dbus.service`: ExecStart = `${pkg}/bin/toshy-cosmic-dbus-service`, WantedBy = `default.target`, Restart = on-failure
    - Do NOT hardcode DISPLAY, WAYLAND_DISPLAY, XDG_RUNTIME_DIR, or user IDs
    - Do NOT force-enable compositors or display managers
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_
  - [x] 7.3 Add udev rules and input group configuration
    - Install udev rule: `KERNEL=="event*", GROUP="input", MODE="0660"`
    - Ensure `input` group exists
    - Add configured user to `input` group
    - _Requirements: 12.1, 12.2, 12.3, 4.10_
  - [x] 7.4 Implement config file resolution logic
    - If `configFile` is set, use that file path in the config service environment
    - If `extraConfig` is non-empty, copy default config and append extraConfig
    - If neither is set, use the default config from the package data
    - Pass the resolved config path to `tshysvc-config` via environment variable
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  - [x] 7.5 Add GUI and KWin script optional features
    - When `gui.enable` is true, install GUI-related desktop files
    - When `kwinScript.enable` is true, install KWin script to appropriate KDE directory
    - Wrap GUI scripts with GTK3/GTK4 library paths, GObject introspection typelib paths, and GSettings schema paths
    - _Requirements: 14.2, 14.3, 14.5, 15.1, 15.2, 15.3_

- [x] 8. Rewrite Home Manager module
  - [x] 8.1 Rewrite `home-manager/toshy.nix` with minimal correct options
    - Define options matching NixOS module minus `user` (implicit from Home Manager) and minus udev rules
    - Options: `enable`, `package`, `configFile`, `extraConfig`, `gui.enable`, `kwinScript.enable`
    - Remove ALL old options: `settings.*`, `gui.tray`, `extraConfig` that generates Python keymaps
    - _Requirements: 6.1, 6.4, 6.5, 6.6_
  - [x] 8.2 Create the five systemd user services in the Home Manager module
    - Same five services as NixOS module: config, session-monitor, kwin-dbus, wlroots-dbus, cosmic-dbus
    - Use Home Manager's `systemd.user.services` format (Unit/Service/Install sections)
    - Use `WantedBy = ["default.target"]` matching upstream
    - Do NOT hardcode XDG_RUNTIME_DIR or user IDs
    - _Requirements: 6.2, 6.5_
  - [x] 8.3 Implement config file management for Home Manager
    - Copy default `toshy_config.py` to `~/.config/toshy/toshy_config.py` via `xdg.configFile` if no custom config specified
    - If `configFile` is set, symlink that file instead
    - If `extraConfig` is non-empty, append to the default config
    - _Requirements: 6.3, 6.4, 7.1, 7.2_

- [x] 9. Checkpoint — Verify modules evaluate correctly
  - Ensure the NixOS module evaluates without errors with `services.toshy.enable = true` and `services.toshy.user = "test"`. Verify the Home Manager module evaluates correctly. Check that no hardcoded DISPLAY, WAYLAND_DISPLAY, XDG_RUNTIME_DIR, or user IDs exist in service definitions. Ask the user if questions arise.

- [x] 10. Update example configurations
  - [x] 10.1 Rewrite `examples/basic-nixos-config.nix` to match new module options
    - Show minimal NixOS configuration with `services.toshy.enable = true` and `services.toshy.user`
    - Only reference the 7 actual options from the new module
    - _Requirements: 5.1, 5.2, 5.3_
  - [x] 10.2 Rewrite `examples/home-manager-config.nix` to match new module options
    - Show minimal Home Manager configuration with `services.toshy.enable = true`
    - Only reference actual options from the new Home Manager module
    - _Requirements: 6.1, 6.3, 6.4_

- [x] 11. Clean up old files from previous port
  - [x] 11.1 Delete the `toshy/` wrapper package directory
    - Remove `toshy/` and all its contents (daemon.py, tray.py, config.py, etc.)
    - This wrapper package does not exist upstream and is replaced by direct use of upstream modules
  - [x] 11.2 Delete old planning and documentation files
    - Remove: `FLAKE_ARCHITECTURE.md`, `NIXOS_MODULE_DESIGN.md`, `DEPENDENCY_ANALYSIS.md`, `PACKAGING_ISSUES.md`, `MODERNIZATION_CONTEXT.md`, `DEVELOPMENT_PLAN.md`, `MIGRATION_GUIDE.md`, `PHASE2_COMPLETION.md`, `PHASE3_COMPLETION.md`, `PHASE4_COMPLETION.md`
    - These are replaced by the spec documents in `.kiro/specs/toshy-nix-flake/`
  - [x] 11.3 Delete old tests, docs, and overly complex examples
    - Remove `tests/` directory (old tests from previous port)
    - Remove `docs/` directory (old docs from previous port)
    - Remove `examples/advanced-nixos-config.nix` (overly complex, replaced by simpler examples)

- [x] 12. Final checkpoint — Verify complete flake
  - Run `nix flake check` to verify the entire flake. Ensure `nix build .#toshy` and `nix build .#xwaykeyz` both succeed. Verify all expected binaries exist in the built packages. Ask the user if questions arise.

## Notes

- All code is Nix and Python — no pseudocode translation needed
- Property-based testing does not apply (this is declarative Nix packaging, not parameterized logic)
- The pyproject.toml is designed for upstream contribution to RedBearAK/toshy
- The upstream source at ~/sources/celesrenata/ReadBearAK-Toshy/ should be referenced during implementation to verify file paths and module names
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- The `toshy/` wrapper package from the previous port is deleted — the new design uses upstream's actual module names directly

# Requirements Document

## Introduction

This document specifies the requirements for the official Nix flake for Toshy, a Mac-style keybinding application for Linux. The flake will package Toshy and its custom dependency xwaykeyz for NixOS, providing both a NixOS module and a Home Manager module. The goal is to produce an upstream-quality flake that faithfully reproduces Toshy's runtime architecture (five systemd user services, a 5700-line Python config file, D-Bus services for compositor integration) using proper Nix conventions — no `catchConflicts = false` hacks, no hardcoded UIDs, no venv activation.

The upstream Toshy repository (RedBearAK/toshy) currently has no Python packaging metadata (no pyproject.toml, setup.py, or setup.cfg). Its installer (`setup_toshy.py`) copies the entire repo to `~/.config/toshy/` and creates a venv. As part of this effort, we will create a `pyproject.toml` to be contributed upstream, making Toshy a proper Python package. This enables `buildPythonApplication` in Nix, standard entry points, and benefits the upstream developer with modern Python tooling. The flake will then install Toshy into the Nix store, wrap Python scripts with the correct dependencies, and generate systemd service units that point to store paths instead of venv paths.

## Glossary

- **Flake**: A Nix flake providing packages, NixOS modules, and Home Manager modules for Toshy
- **Toshy**: The main Mac-style keybinding application for Linux (RedBearAK/toshy)
- **xwaykeyz**: A fork of keyszer; the keymapper engine that Toshy depends on (RedBearAK/xwaykeyz). Not in nixpkgs. Uses hatchling build system. Requires version >=1.12.0
- **Config_Service**: The primary systemd user service (`toshy-config.service`) that runs `xwaykeyz -w -c toshy_config.py`
- **Session_Monitor**: The systemd user service (`toshy-session-monitor.service`) that monitors loginctl session state and stops/starts the Config_Service when the user switches sessions
- **KWin_DBus_Service**: The optional systemd user service (`toshy-kwin-dbus.service`) providing D-Bus window context for KDE Plasma/KWin
- **Wlroots_DBus_Service**: The systemd user service (`toshy-wlroots-dbus.service`) providing D-Bus window context for wlroots-based compositors (Sway, Hyprland, etc.)
- **Cosmic_DBus_Service**: The systemd user service (`toshy-cosmic-dbus.service`) providing D-Bus window context for the COSMIC desktop
- **Toshy_Config**: The main Python configuration file (`toshy_config.py`, ~5700 lines) that imports from `xwaykeyz.config_api` and defines all keymaps
- **toshy_common**: A shared Python utility package in the upstream repo providing `env_context`, `logger`, `machine_context`, `settings_class`, and other modules used by all services
- **NixOS_Module**: A NixOS module (`nixosModules.toshy`) that declares systemd user services and system-level configuration
- **Home_Manager_Module**: A Home Manager module (`homeManagerModules.toshy`) for user-level Toshy installation
- **Wrapper**: A Nix wrapper script (via `makeWrapper` or `wrapProgram`) that sets `PYTHONPATH`, `PATH`, and other environment variables so Python scripts can find their dependencies without a venv
- **installPhase**: The Nix build phase where files are copied into `$out` in the Nix store; with a proper `pyproject.toml`, `buildPythonApplication` handles most of this automatically
- **python-xlib**: Python X11 library; must be pinned to version 0.31 to work around an upstream bug (`BadRRModeError`)
- **xkbcommon**: Python xkbcommon bindings; must be pinned to <1.1 due to breaking API changes in 1.5+
- **hyprpy**: Python bindings for Hyprland IPC; available on PyPI but not in nixpkgs
- **sv_ttk**: Sun Valley TTK theme for the optional tkinter GUI; not in nixpkgs

## Requirements

### Requirement 1: Package xwaykeyz from Source

**User Story:** As a NixOS user, I want xwaykeyz packaged as a proper Nix Python package, so that Toshy's keymapper engine is available in the Nix store with all its dependencies resolved.

#### Acceptance Criteria

1. THE Flake SHALL build xwaykeyz using `buildPythonPackage` with `format = "pyproject"` and `hatchling` as the build system
2. THE Flake SHALL fetch the xwaykeyz source from GitHub using `fetchFromGitHub` pinned to a specific release tag or commit hash (not `main` branch)
3. THE Flake SHALL declare xwaykeyz's propagated dependencies: appdirs, dbus-python, evdev, i3ipc, inotify-simple, ordered-set, pywayland, and python-xlib (pinned to 0.31)
4. THE Flake SHALL produce a working `xwaykeyz` command-line binary in `$out/bin/xwaykeyz`
5. THE Flake SHALL NOT use `catchConflicts = false` or `dontCheckRuntimeDeps = true` for the xwaykeyz package

### Requirement 2: Create pyproject.toml and Package Toshy as a Python Application

**User Story:** As a NixOS user and upstream contributor, I want a `pyproject.toml` added to the Toshy repo so that Toshy can be built as a proper Python package using `buildPythonApplication`, benefiting both Nix packaging and the broader Python ecosystem.

#### Acceptance Criteria

1. THE Flake SHALL include a `pyproject.toml` in the Toshy source tree that declares the package metadata, dependencies, and entry points for upstream contribution
2. THE `pyproject.toml` SHALL use `setuptools` as the build backend (matching the existing `setup_toshy.py` ecosystem) with `[build-system] requires = ["setuptools>=61.0", "wheel"]`
3. THE `pyproject.toml` SHALL declare `toshy_common`, `toshy_gui`, and top-level scripts (`toshy_tray`, `toshy_layout_selector`) as included packages
4. THE `pyproject.toml` SHALL declare console script entry points for: `toshy-tray`, `toshy-gui`, `toshy-layout-selector`, and any other user-facing commands
5. THE `pyproject.toml` SHALL declare all runtime dependencies matching the upstream `requirements.txt`: appdirs, dbus-python, evdev, hyprpy, i3ipc, inotify-simple, lockfile, ordered-set, pillow, psutil, pygobject, pywayland, six, systemd-python, watchdog, python-xlib==0.31, xkbcommon<1.1, and xwaykeyz>=1.12.0
6. THE `pyproject.toml` SHALL declare `package-data` to include `default-toshy-config/`, `assets/`, `desktop/`, `systemd-user-service-units/`, `scripts/`, `kwin-dbus-service/`, `wlroots-dbus-service/`, `cosmic-dbus-service/`, and `kwin-script/` so these are installed alongside the Python packages
7. THE Flake SHALL build Toshy using `buildPythonApplication` with `format = "pyproject"`
8. THE Flake SHALL NOT use `catchConflicts = false` or `dontCheckRuntimeDeps = true` for the Toshy package
9. THE `pyproject.toml` SHALL be designed for upstream contribution to RedBearAK/toshy, not as a Nix-only artifact

### Requirement 3: Wrap Scripts with Correct Runtime Environment

**User Story:** As a NixOS user, I want all Toshy scripts to find their dependencies and runtime tools without a venv, so that the services work in the Nix store-based environment.

#### Acceptance Criteria

1. THE Flake SHALL use `wrapGAppsHook` or `makeWrapper` to ensure GUI scripts (toshy-tray, toshy-gui) have GTK3/GTK4 libraries, GObject introspection typelibs, and GSettings schemas available
2. THE Flake SHALL wrap shell scripts (`tshysvc-config`, `tshysvc-sessmon`, D-Bus service launchers) to include runtime tools (pkill, loginctl, systemctl, xhost, xset, notify-send, bash, python3) on `PATH`
3. THE Flake SHALL ensure that the wrapped `tshysvc-config` script can find `xwaykeyz` on `PATH` without venv activation
4. THE Flake SHALL ensure that D-Bus service scripts invoke Python from the Nix store with the correct `PYTHONPATH` (including `toshy_common` and the protocol modules) instead of activating a venv
5. THE Flake SHALL ensure that `toshy_config.py` can import `toshy_common` modules at runtime by including the Toshy package's data directory on `PYTHONPATH` in the config service environment

### Requirement 4: NixOS Module with Systemd User Services

**User Story:** As a NixOS administrator, I want a NixOS module that sets up Toshy's five systemd user services matching upstream's architecture, so that Toshy runs correctly as a system-managed service.

#### Acceptance Criteria

1. WHEN `services.toshy.enable` is set to true, THE NixOS_Module SHALL create a `toshy-config.service` systemd user service that runs `xwaykeyz -w -c <config_path>`
2. WHEN `services.toshy.enable` is set to true, THE NixOS_Module SHALL create a `toshy-session-monitor.service` systemd user service that runs the session monitor script
3. WHEN `services.toshy.enable` is set to true, THE NixOS_Module SHALL create a `toshy-kwin-dbus.service` systemd user service for KDE Plasma window context
4. WHEN `services.toshy.enable` is set to true, THE NixOS_Module SHALL create a `toshy-wlroots-dbus.service` systemd user service for wlroots compositor window context
5. WHEN `services.toshy.enable` is set to true, THE NixOS_Module SHALL create a `toshy-cosmic-dbus.service` systemd user service for COSMIC desktop window context
6. THE NixOS_Module SHALL set service ordering so that D-Bus services start before the Config_Service, and the Session_Monitor starts after the Config_Service, matching upstream's `toshy-services-start.sh` ordering
7. THE NixOS_Module SHALL use `default.target` as the WantedBy target for all services, matching upstream's service unit files (not `graphical-session.target`, since some distros fail to activate it)
8. THE NixOS_Module SHALL NOT hardcode `DISPLAY`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, or user IDs — these are inherited from the user session
9. THE NixOS_Module SHALL NOT force-enable display managers, compositors, or window managers (no `programs.hyprland.enable`, `services.xserver.displayManager.gdm.enable`, etc.)
10. THE NixOS_Module SHALL add the configured user to the `input` group for evdev device access

### Requirement 5: NixOS Module Configuration Options

**User Story:** As a NixOS administrator, I want minimal, correct configuration options for Toshy, so that I can customize the installation without the module trying to control my entire desktop environment.

#### Acceptance Criteria

1. THE NixOS_Module SHALL provide a `services.toshy.enable` option (boolean, default false)
2. THE NixOS_Module SHALL provide a `services.toshy.package` option to override the Toshy package
3. THE NixOS_Module SHALL provide a `services.toshy.user` option (string, required) specifying which user runs Toshy
4. THE NixOS_Module SHALL provide a `services.toshy.configFile` option (path or null) to specify a custom `toshy_config.py`, defaulting to the upstream default config
5. THE NixOS_Module SHALL provide a `services.toshy.extraConfig` option (lines, default empty) for appending Python code to the end of the config file
6. THE NixOS_Module SHALL NOT provide options that reimplement Toshy's keymap logic in Nix (no `keybindings.macStyle`, no `keybindings.applications` attribute sets that generate Python code)
7. THE NixOS_Module SHALL NOT provide options for `wayland.compositor`, `x11.windowManager`, or `x11.displayManager` — Toshy auto-detects these at runtime

### Requirement 6: Home Manager Module

**User Story:** As a Home Manager user, I want a module that installs Toshy at the user level with systemd user services, so that I can use Toshy without system-level NixOS configuration.

#### Acceptance Criteria

1. WHEN `services.toshy.enable` is set to true, THE Home_Manager_Module SHALL install the Toshy package into the user's profile
2. WHEN `services.toshy.enable` is set to true, THE Home_Manager_Module SHALL create the same five systemd user services as the NixOS_Module (config, session-monitor, kwin-dbus, wlroots-dbus, cosmic-dbus)
3. THE Home_Manager_Module SHALL copy the default `toshy_config.py` to `~/.config/toshy/toshy_config.py` if no custom config is specified
4. THE Home_Manager_Module SHALL provide a `services.toshy.configFile` option to use a custom config file
5. THE Home_Manager_Module SHALL NOT hardcode `XDG_RUNTIME_DIR` or user IDs
6. THE Home_Manager_Module SHALL NOT generate Python keymap code from Nix attribute sets

### Requirement 7: Handle the Toshy Config File

**User Story:** As a Toshy user, I want the default 5700-line config file installed and usable out of the box, with the option to provide my own, so that I get the full Toshy experience without manual setup.

#### Acceptance Criteria

1. THE Flake SHALL install the upstream `default-toshy-config/toshy_config.py` as the default configuration
2. WHEN a user provides a custom config via `services.toshy.configFile`, THE NixOS_Module SHALL use that file instead of the default
3. THE Flake SHALL ensure that `toshy_config.py` can import from `xwaykeyz.config_api`, `xwaykeyz.lib.key_context`, `xwaykeyz.lib.logger`, and `xwaykeyz.models.modifier` at runtime
4. THE Flake SHALL ensure that `toshy_config.py` can import from `toshy_common` modules (env_context, logger, machine_context, settings_class, etc.) at runtime
5. THE Flake SHALL ensure that the `default-toshy-config/toshy_config_barebones.py` is also installed as an alternative config option

### Requirement 8: Pin Critical Dependency Versions

**User Story:** As a NixOS user, I want python-xlib pinned to 0.31 and xkbcommon pinned to <1.1, so that I don't hit known upstream bugs.

#### Acceptance Criteria

1. THE Flake SHALL use python-xlib version 0.31 (not newer) to avoid the `BadRRModeError` bug
2. THE Flake SHALL pin python-xlib using a proper nixpkgs override mechanism that propagates through the entire dependency graph (not just `overrideAttrs` on the top-level package)
3. THE Flake SHALL use xkbcommon version less than 1.1 to avoid breaking API changes introduced in version 1.5
4. IF a dependency version conflict is detected at build time, THEN THE Flake SHALL fail with a clear error message rather than silently disabling conflict checks

### Requirement 9: Package hyprpy from PyPI

**User Story:** As a Hyprland user on NixOS, I want hyprpy available as a dependency, so that Toshy can communicate with Hyprland via IPC for window context.

#### Acceptance Criteria

1. THE Flake SHALL package hyprpy using `buildPythonPackage` with source fetched from PyPI
2. THE Flake SHALL include hyprpy as a propagated dependency of the xwaykeyz package
3. IF hyprpy becomes available in nixpkgs, THEN THE Flake SHALL prefer the nixpkgs version over a custom build

### Requirement 10: Support x86_64-linux and aarch64-linux

**User Story:** As a NixOS user on ARM64 hardware, I want the Toshy flake to build on both x86_64-linux and aarch64-linux, so that I can use Toshy on any Linux architecture.

#### Acceptance Criteria

1. THE Flake SHALL declare support for both `x86_64-linux` and `aarch64-linux` in its system list
2. THE Flake SHALL NOT include architecture-specific code paths or conditional dependencies unless genuinely required by a native dependency
3. THE Flake SHALL produce identical package structures on both architectures

### Requirement 11: Flake Outputs Structure

**User Story:** As a NixOS user, I want the flake to expose standard outputs (packages, modules, overlays), so that I can integrate Toshy into my system using any common Nix pattern.

#### Acceptance Criteria

1. THE Flake SHALL expose `packages.<system>.toshy` as the main Toshy package
2. THE Flake SHALL expose `packages.<system>.xwaykeyz` as the xwaykeyz package
3. THE Flake SHALL expose `packages.<system>.default` as an alias to the Toshy package
4. THE Flake SHALL expose `nixosModules.toshy` and `nixosModules.default` for the NixOS module
5. THE Flake SHALL expose `homeManagerModules.toshy` and `homeManagerModules.default` for the Home Manager module
6. THE Flake SHALL expose `overlays.default` that adds `toshy` and `xwaykeyz` to the package set
7. THE Flake SHALL expose a `devShells.<system>.default` for development

### Requirement 12: Udev Rules for Input Device Access

**User Story:** As a NixOS administrator, I want proper udev rules installed, so that users in the input group can access evdev input devices for keymapping.

#### Acceptance Criteria

1. WHEN `services.toshy.enable` is set to true, THE NixOS_Module SHALL install udev rules that grant the `input` group read/write access to `/dev/input/event*` devices
2. THE NixOS_Module SHALL ensure the `input` group exists
3. THE NixOS_Module SHALL add the configured user to the `input` group

### Requirement 13: Desktop Files and Icons

**User Story:** As a desktop Linux user, I want Toshy's desktop entries and icons installed, so that I can find and launch Toshy from my application menu.

#### Acceptance Criteria

1. THE Flake SHALL install `.desktop` files from the `desktop/` directory into `$out/share/applications/`
2. THE Flake SHALL install icon files from `assets/` into `$out/share/icons/` following the XDG icon theme specification
3. THE Flake SHALL install the Toshy icon theme from `assets/Toshy-Icon-Theme/` into `$out/share/icons/Toshy-Icon-Theme/`
4. WHEN desktop files reference executable paths, THE Flake SHALL patch them to use Nix store paths

### Requirement 14: GUI Components (Optional)

**User Story:** As a Toshy user, I want the optional GUI preferences app and system tray available, so that I can manage Toshy visually.

#### Acceptance Criteria

1. THE Flake SHALL include the GTK-based GUI components (`toshy_gui/`, `toshy_tray.py`) in the package
2. THE Flake SHALL wrap GUI scripts with GTK3/GTK4 library paths, GObject introspection typelib paths, and GSettings schema paths
3. THE NixOS_Module SHALL provide a `services.toshy.gui.enable` option (boolean, default false) to control whether GUI-related desktop files are installed
4. THE Flake SHALL include `libappindicator-gtk3` or `libayatana-appindicator` for system tray support
5. IF GTK libraries are not available at runtime, THEN the GUI scripts SHALL print a clear error message and exit with a non-zero status

### Requirement 15: KWin Script Installation (Optional)

**User Story:** As a KDE Plasma user, I want the Toshy KWin script installed, so that the KWin D-Bus service can receive window focus notifications.

#### Acceptance Criteria

1. THE Flake SHALL include the KWin script files from `kwin-script/` in the package
2. THE NixOS_Module SHALL provide an option to install the KWin script to the appropriate KDE directory
3. THE Flake SHALL include the `toshy_kwin_script_setup.py` script that the KWin D-Bus service launches at startup

{ config, lib, pkgs, ... }:

let
  cfg = config.services.toshy;
  pkg = cfg.package;

  # ── Config file resolution (Task 7.4) ───────────────────────────
  # Priority:
  #   1. configFile (user-provided path)        → use that file directly
  #   2. extraConfig non-empty                  → default config + appended code
  #   3. neither set                            → default config from package
  defaultConfigPath =
    "${pkg}/lib/${pkg.python.libPrefix}/site-packages/default-toshy-config/toshy_config.py";

  mergedConfig = pkgs.runCommand "toshy-config-merged.py" { } ''
    cp ${defaultConfigPath} $out
    chmod +w $out
    cat >> $out <<'NIXOS_EXTRA_CONFIG'

# ── Extra configuration appended by NixOS module ──
${cfg.extraConfig}
NIXOS_EXTRA_CONFIG
  '';

  resolvedConfigPath =
    if cfg.configFile != null then cfg.configFile
    else if cfg.extraConfig != "" then mergedConfig
    else defaultConfigPath;

  # ── GUI desktop files derivation (Task 7.5) ─────────────────────
  guiDesktopFiles = pkgs.runCommand "toshy-desktop-files" { } ''
    mkdir -p $out/share/applications
    cp ${pkg}/share/applications/Toshy_Tray.desktop            $out/share/applications/
    cp ${pkg}/share/applications/app.toshy.preferences.desktop $out/share/applications/
  '';

  # ── KWin script derivation (Task 7.5) ───────────────────────────
  kwinScriptPkg = pkgs.runCommand "toshy-kwin-script" { } ''
    mkdir -p $out/share/kwin/scripts
    cp -r ${pkg}/lib/${pkg.python.libPrefix}/site-packages/kwin-script/kde6/toshy-dbus-notifyactivewindow \
      $out/share/kwin/scripts/toshy-dbus-notifyactivewindow
  '';

in {

  # ════════════════════════════════════════════════════════════════
  # Options — exactly 7 options (Task 7.1)
  # ════════════════════════════════════════════════════════════════

  options.services.toshy = {

    enable = lib.mkEnableOption "Toshy keybinding service";

    package = lib.mkOption {
      type = lib.types.package;
      description = "The Toshy package to use.";
      # No default — must be set by the flake or the user.
      # mkPackageOption would look for pkgs.toshy which doesn't exist in nixpkgs.
    };

    user = lib.mkOption {
      type        = lib.types.str;
      description = "User to run Toshy services as.";
      example     = "alice";
    };

    configFile = lib.mkOption {
      type        = lib.types.nullOr lib.types.path;
      default     = null;
      description = ''
        Path to a custom toshy_config.py file.
        When null, the upstream default config is used
        (possibly with extraConfig appended).
      '';
      example     = "/etc/toshy/my_config.py";
    };

    extraConfig = lib.mkOption {
      type        = lib.types.lines;
      default     = "";
      description = ''
        Python code appended to the end of the default toshy_config.py.
        Ignored when configFile is set.
      '';
      example = ''
        # Add a custom keymap
        keymap("MyApp", {
            C("c"): C("ctrl-c"),
        })
      '';
    };

    gui = {
      enable = lib.mkOption {
        type        = lib.types.bool;
        default     = false;
        description = "Install GUI-related desktop files (tray, preferences).";
      };
    };

    kwinScript = {
      enable = lib.mkOption {
        type        = lib.types.bool;
        default     = false;
        description = "Install the KWin script for KDE Plasma window-focus notifications.";
      };
    };

  };

  # ════════════════════════════════════════════════════════════════
  # Implementation
  # ════════════════════════════════════════════════════════════════

  config = lib.mkIf cfg.enable {

    # ── Assertions (Task 7.1) ─────────────────────────────────────
    assertions = [
      {
        assertion = cfg.user != "";
        message   = "services.toshy.user must be set to a non-empty string.";
      }
    ];

    # ── System packages (Tasks 7.1, 7.5) ──────────────────────────
    # Always install the main Toshy package.
    # Conditionally add GUI desktop files and KWin script.
    environment.systemPackages =
      [ pkg ]
      ++ lib.optional cfg.gui.enable guiDesktopFiles
      ++ lib.optional cfg.kwinScript.enable kwinScriptPkg;

    # ── Seed ~/.config/toshy on activation ────────────────────────
    # Toshy expects its config, scripts, and data files at
    # ~/.config/toshy/. This activation script seeds the directory
    # from the Nix store on every nixos-rebuild switch, keeping
    # scripts and default config up to date. The user's custom
    # toshy_config.py is NOT overwritten if it already exists.
    system.activationScripts.toshy-seed-config = let
      site = "${pkg}/lib/${pkg.python.libPrefix}/site-packages";
    in ''
      TOSHY_DIR="/home/${cfg.user}/.config/toshy"
      mkdir -p "$TOSHY_DIR"

      # Always update scripts from the package (they're not user-editable)
      rm -rf "$TOSHY_DIR/scripts"
      cp -r "${site}/scripts" "$TOSHY_DIR/scripts"
      chmod -R u+w "$TOSHY_DIR/scripts"

      # Fix shebangs — NixOS doesn't have /usr/bin/env
      for f in "$TOSHY_DIR"/scripts/*.sh "$TOSHY_DIR"/scripts/bin/*.sh; do
        if [ -f "$f" ]; then
          ${pkgs.gnused}/bin/sed -i 's|#!/usr/bin/env bash|#!${pkgs.bash}/bin/bash|g' "$f"
          ${pkgs.gnused}/bin/sed -i 's|#!/bin/bash|#!${pkgs.bash}/bin/bash|g' "$f"
          ${pkgs.gnused}/bin/sed -i 's|#!/usr/bin/bash|#!${pkgs.bash}/bin/bash|g' "$f"
          # Also fix internal 'exec bash' calls that rely on bare 'bash' being on PATH
          ${pkgs.gnused}/bin/sed -i 's|exec bash -c|exec ${pkgs.bash}/bin/bash -c|g' "$f"
        fi
      done

      # Seed the default config only if one doesn't exist yet
      if [ ! -f "$TOSHY_DIR/toshy_config.py" ]; then
        cp "${resolvedConfigPath}" "$TOSHY_DIR/toshy_config.py"
        chmod u+w "$TOSHY_DIR/toshy_config.py"
      fi

      # Seed the barebones config as a reference
      if [ -f "${site}/default-toshy-config/toshy_config_barebones.py" ]; then
        cp "${site}/default-toshy-config/toshy_config_barebones.py" \
           "$TOSHY_DIR/toshy_config_barebones.py"
        chmod u+w "$TOSHY_DIR/toshy_config_barebones.py"
      fi

      # Fix ownership
      chown -R ${cfg.user}: "$TOSHY_DIR"

      # Symlink scripts/bin/* into ~/.local/bin/ so the GUI preferences
      # app and tray can find them (service_manager.py looks there).
      LOCAL_BIN="/home/${cfg.user}/.local/bin"
      mkdir -p "$LOCAL_BIN"
      for script in "$TOSHY_DIR"/scripts/bin/toshy-*; do
        name="$(basename "$script" .sh)"
        ln -sf "$script" "$LOCAL_BIN/$name"
      done
      # Also link the full .sh names for scripts that call them directly
      for script in "$TOSHY_DIR"/scripts/bin/toshy-*.sh; do
        ln -sf "$script" "$LOCAL_BIN/$(basename "$script")"
      done
      # Override: point toshy-gui and toshy-tray to the Nix-wrapped binaries
      # (the shell scripts expect a venv which doesn't exist on NixOS)
      ln -sf "${pkg}/bin/toshy-gui" "$LOCAL_BIN/toshy-gui"
      ln -sf "${pkg}/bin/toshy-tray" "$LOCAL_BIN/toshy-tray"
      ln -sf "${pkg}/bin/toshy-layout-selector" "$LOCAL_BIN/toshy-layout-selector"

      # Override config-start/stop/restart with systemctl-based versions
      # (upstream scripts use venv activation which doesn't exist on NixOS)
      cat > "$TOSHY_DIR/scripts/bin/toshy-config-start.sh" << EOF
#!${pkgs.bash}/bin/bash
export PATH="${pkgs.systemd}/bin:\$PATH"
systemctl --user start toshy-config.service
EOF
      cat > "$TOSHY_DIR/scripts/bin/toshy-config-stop.sh" << EOF
#!${pkgs.bash}/bin/bash
export PATH="${pkgs.systemd}/bin:\$PATH"
systemctl --user stop toshy-config.service
EOF
      cat > "$TOSHY_DIR/scripts/bin/toshy-config-restart.sh" << EOF
#!${pkgs.bash}/bin/bash
export PATH="${pkgs.systemd}/bin:\$PATH"
systemctl --user restart toshy-config.service
EOF

      # Override services log viewer — needs journalctl on PATH and must
      # keep the terminal open with -f (follow)
      cat > "$TOSHY_DIR/scripts/bin/toshy-services-log.sh" << EOF
#!${pkgs.bash}/bin/bash
export PATH="${pkgs.systemd}/bin:${pkgs.coreutils}/bin:${pkgs.procps}/bin:${pkgs.gnugrep}/bin:\$PATH"
echo "Showing Toshy service logs (Ctrl+C to exit)..."
echo
exec journalctl --user -b -f \\
  --user-unit toshy-config.service \\
  --user-unit toshy-session-monitor.service \\
  --user-unit toshy-kwin-dbus.service \\
  --user-unit toshy-wlroots-dbus.service \\
  --user-unit toshy-cosmic-dbus.service \\
  --user-unit toshy-tray.service
EOF

      chmod +x "$TOSHY_DIR"/scripts/bin/toshy-config-{start,stop,restart}.sh
      chmod +x "$TOSHY_DIR"/scripts/bin/toshy-services-log.sh

      chown -h ${cfg.user}: "$LOCAL_BIN"/toshy-* 2>/dev/null || true
    '';

    # ── Udev rules (Task 7.3) ────────────────────────────────────
    # Grant input group access to evdev devices.
    services.udev.extraRules = ''
      KERNEL=="event*", GROUP="input", MODE="0660"
    '';

    # ── Ensure the input group exists (Task 7.3) ──────────────────
    users.groups.input = { };

    # ── Add the configured user to the input group (Task 7.3) ─────
    users.users.${cfg.user} = {
      extraGroups = [ "input" ];
    };

    # ── Systemd user services (Task 7.2) ──────────────────────────
    # All five services use systemd.user.services (user-level units
    # managed system-wide). They match upstream's WantedBy=default.target
    # and do NOT hardcode DISPLAY, WAYLAND_DISPLAY, XDG_RUNTIME_DIR,
    # or UIDs. Environment variables are inherited from the user session.

    systemd.user.services.toshy-config = {
      description = "Toshy Config Service";

      wantedBy = [ "default.target" ];
      after    = [ "default.target" ];

      serviceConfig = {
        Type             = "simple";
        ExecStart        = "${pkg}/bin/tshysvc-config";
        Restart          = "always";
        RestartSec       = 5;
        SyslogIdentifier = "toshy-config";
      };

      # Task 7.4: pass resolved config path via environment variable
      environment = {
        TERM              = "xterm";
        TOSHY_CONFIG_FILE = toString resolvedConfigPath;
      };
    };

    systemd.user.services.toshy-session-monitor = {
      description = "Toshy Session Monitor";

      wantedBy = [ "default.target" ];
      after    = [ "default.target" ];

      serviceConfig = {
        Type             = "simple";
        ExecStart        = "${pkg}/bin/tshysvc-sessmon";
        Restart          = "always";
        RestartSec       = 5;
        SyslogIdentifier = "toshy-sessmon";
      };

      environment = {
        TERM = "xterm";
      };
    };

    systemd.user.services.toshy-kwin-dbus = {
      description = "Toshy KWin D-Bus Service";

      wantedBy = [ "default.target" ];

      unitConfig = {
        StartLimitBurst       = 5;
        StartLimitIntervalSec = 60;
      };

      serviceConfig = {
        Type                  = "simple";
        ExecStart             = "${pkg}/bin/toshy-kwin-dbus-service";
        Restart               = "on-failure";
        RestartSec            = 5;
        SyslogIdentifier      = "toshy-kwin-dbus";
      };

      environment = {
        TERM = "xterm";
      };
    };

    systemd.user.services.toshy-wlroots-dbus = {
      description = "Toshy Wlroots D-Bus Service";

      wantedBy = [ "default.target" ];

      unitConfig = {
        StartLimitBurst       = 5;
        StartLimitIntervalSec = 60;
      };

      serviceConfig = {
        Type                  = "simple";
        ExecStart             = "${pkg}/bin/toshy-wlroots-dbus-service";
        Restart               = "on-failure";
        RestartSec            = 5;
        SyslogIdentifier      = "toshy-wlroots-dbus";
      };

      environment = {
        TERM = "xterm";
      };
    };

    systemd.user.services.toshy-cosmic-dbus = {
      description = "Toshy COSMIC D-Bus Service";

      wantedBy = [ "default.target" ];

      unitConfig = {
        StartLimitBurst       = 5;
        StartLimitIntervalSec = 60;
      };

      serviceConfig = {
        Type                  = "simple";
        ExecStart             = "${pkg}/bin/toshy-cosmic-dbus-service";
        Restart               = "on-failure";
        RestartSec            = 5;
        SyslogIdentifier      = "toshy-cosmic-dbus";
      };

      environment = {
        TERM = "xterm";
      };
    };

    # ── Tray icon service (optional, when gui.enable is true) ─────
    systemd.user.services.toshy-tray = lib.mkIf cfg.gui.enable {
      description = "Toshy Tray Icon";

      wantedBy = [ "default.target" ];
      after    = [ "default.target" "toshy-config.service" ];

      serviceConfig = {
        Type             = "simple";
        ExecStart        = "${pkg}/bin/toshy-tray";
        Restart          = "on-failure";
        RestartSec       = 5;
        SyslogIdentifier = "toshy-tray";
      };

      environment = {
        TERM              = "xterm";
        TOSHY_CONFIG_DIR  = "/home/${cfg.user}/.config/toshy";
      };
    };

  };
}

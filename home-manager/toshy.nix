{ config, lib, pkgs, ... }:

let
  cfg = config.services.toshy;
  pkg = cfg.package;

  # ── Config file resolution ──────────────────────────────────────
  # Priority:
  #   1. configFile (user-provided path)        → symlink that file
  #   2. extraConfig non-empty                  → default config + appended code
  #   3. neither set                            → copy default config from package
  defaultConfigPath =
    "${pkg}/lib/${pkg.python.libPrefix}/site-packages/default-toshy-config/toshy_config.py";

  mergedConfig = pkgs.runCommand "toshy-config-merged.py" { } ''
    cp ${defaultConfigPath} $out
    chmod +w $out
    cat >> $out <<'HM_EXTRA_CONFIG'

# ── Extra configuration appended by Home Manager module ──
${cfg.extraConfig}
HM_EXTRA_CONFIG
  '';

  # The path used by the config service's environment variable.
  # For xdg.configFile-managed configs, this points to the XDG location
  # that Home Manager will populate. For custom configFile, it points
  # directly to the user-specified path.
  resolvedConfigPath =
    if cfg.configFile != null then cfg.configFile
    else if cfg.extraConfig != "" then mergedConfig
    else defaultConfigPath;

  # ── GUI desktop files derivation ────────────────────────────────
  guiDesktopFiles = pkgs.runCommand "toshy-desktop-files" { } ''
    mkdir -p $out/share/applications
    cp ${pkg}/share/applications/Toshy_Tray.desktop            $out/share/applications/
    cp ${pkg}/share/applications/app.toshy.preferences.desktop $out/share/applications/
  '';

  # ── KWin script derivation ─────────────────────────────────────
  kwinScriptPkg = pkgs.runCommand "toshy-kwin-script" { } ''
    mkdir -p $out/share/kwin/scripts
    cp -r ${pkg}/lib/${pkg.python.libPrefix}/site-packages/kwin-script/kde6/toshy-dbus-notifyactivewindow \
      $out/share/kwin/scripts/toshy-dbus-notifyactivewindow
  '';

in {

  # ════════════════════════════════════════════════════════════════
  # Options — NixOS module options minus `user` and udev rules
  # ════════════════════════════════════════════════════════════════

  options.services.toshy = {

    enable = lib.mkEnableOption "Toshy keybinding service";

    package = lib.mkOption {
      type = lib.types.package;
      description = "The Toshy package to use.";
    };

    configFile = lib.mkOption {
      type        = lib.types.nullOr lib.types.path;
      default     = null;
      description = ''
        Path to a custom toshy_config.py file.
        When null, the upstream default config is used
        (possibly with extraConfig appended).
      '';
      example     = ./my_toshy_config.py;
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

    # ── User profile packages ─────────────────────────────────────
    home.packages =
      [ pkg ]
      ++ lib.optional cfg.gui.enable guiDesktopFiles
      ++ lib.optional cfg.kwinScript.enable kwinScriptPkg;

    # ── Config file management ────────────────────────────────────
    # Install toshy_config.py into ~/.config/toshy/ via xdg.configFile.
    #   - configFile set       → symlink the user-provided file
    #   - extraConfig non-empty → merged default + extra config
    #   - neither              → copy the upstream default config
    xdg.configFile."toshy/toshy_config.py" =
      if cfg.configFile != null then {
        source = cfg.configFile;
      }
      else if cfg.extraConfig != "" then {
        source = mergedConfig;
      }
      else {
        source = defaultConfigPath;
      };

    # Install scripts directory — always kept in sync with the package
    xdg.configFile."toshy/scripts" = {
      source = "${pkg}/lib/${pkg.python.libPrefix}/site-packages/scripts";
      recursive = true;
    };

    # Install barebones config as a reference
    xdg.configFile."toshy/toshy_config_barebones.py" = {
      source = "${pkg}/lib/${pkg.python.libPrefix}/site-packages/default-toshy-config/toshy_config_barebones.py";
    };

    # ── Systemd user services ─────────────────────────────────────
    # Same five services as the NixOS module, adapted to Home Manager's
    # systemd.user.services format (capitalized Unit/Service/Install).
    # All use WantedBy = default.target matching upstream.
    # No hardcoded DISPLAY, WAYLAND_DISPLAY, XDG_RUNTIME_DIR, or UIDs.

    systemd.user.services.toshy-config = {
      Unit = {
        Description = "Toshy Config Service";
        After       = [ "default.target" ];
      };

      Service = {
        Type             = "simple";
        ExecStart        = "${pkg}/bin/tshysvc-config";
        Restart          = "always";
        RestartSec       = 5;
        SyslogIdentifier = "toshy-config";
        Environment      = [
          "TERM=xterm"
          "TOSHY_CONFIG_FILE=${toString resolvedConfigPath}"
        ];
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

    systemd.user.services.toshy-session-monitor = {
      Unit = {
        Description = "Toshy Session Monitor";
        After       = [ "default.target" ];
      };

      Service = {
        Type             = "simple";
        ExecStart        = "${pkg}/bin/tshysvc-sessmon";
        Restart          = "always";
        RestartSec       = 5;
        SyslogIdentifier = "toshy-sessmon";
        Environment      = [ "TERM=xterm" ];
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

    systemd.user.services.toshy-kwin-dbus = {
      Unit = {
        Description = "Toshy KWin D-Bus Service";
        StartLimitBurst = 5;
        StartLimitIntervalSec = 60;
      };

      Service = {
        Type                  = "simple";
        ExecStart             = "${pkg}/bin/toshy-kwin-dbus-service";
        Restart               = "on-failure";
        RestartSec            = 5;
        SyslogIdentifier      = "toshy-kwin-dbus";
        Environment           = [ "TERM=xterm" ];
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

    systemd.user.services.toshy-wlroots-dbus = {
      Unit = {
        Description = "Toshy Wlroots D-Bus Service";
        StartLimitBurst = 5;
        StartLimitIntervalSec = 60;
      };

      Service = {
        Type                  = "simple";
        ExecStart             = "${pkg}/bin/toshy-wlroots-dbus-service";
        Restart               = "on-failure";
        RestartSec            = 5;
        SyslogIdentifier      = "toshy-wlroots-dbus";
        Environment           = [ "TERM=xterm" ];
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

    systemd.user.services.toshy-cosmic-dbus = {
      Unit = {
        Description = "Toshy COSMIC D-Bus Service";
        StartLimitBurst = 5;
        StartLimitIntervalSec = 60;
      };

      Service = {
        Type                  = "simple";
        ExecStart             = "${pkg}/bin/toshy-cosmic-dbus-service";
        Restart               = "on-failure";
        RestartSec            = 5;
        SyslogIdentifier      = "toshy-cosmic-dbus";
        Environment           = [ "TERM=xterm" ];
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

  };
}

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

  # ── D-Bus service helper ────────────────────────────────────────
  # Home Manager uses capitalized Unit/Service/Install attrset format.
  mkDbusService = { description, execStart, syslogId }:
    {
      Unit = {
        Description           = description;
        StartLimitBurst       = 5;
        StartLimitIntervalSec = 60;
      };

      Service = {
        Type             = "simple";
        ExecStart        = execStart;
        Restart          = "on-failure";
        RestartSec       = 5;
        SyslogIdentifier = syslogId;
        Environment      = [ "TERM=xterm" ];
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

in {

  # ════════════════════════════════════════════════════════════════
  # Options
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

    xdg.configFile."toshy/scripts" = {
      source = "${pkg}/lib/${pkg.python.libPrefix}/site-packages/scripts";
      recursive = true;
    };

    xdg.configFile."toshy/toshy_config_barebones.py" = {
      source = "${pkg}/lib/${pkg.python.libPrefix}/site-packages/default-toshy-config/toshy_config_barebones.py";
    };

    # ── Systemd user services ─────────────────────────────────────

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

    # D-Bus services — generated from shared helper
    systemd.user.services.toshy-kwin-dbus = mkDbusService {
      description = "Toshy KWin D-Bus Service";
      execStart   = "${pkg}/bin/toshy-kwin-dbus-service";
      syslogId    = "toshy-kwin-dbus";
    };

    systemd.user.services.toshy-wlroots-dbus = mkDbusService {
      description = "Toshy Wlroots D-Bus Service";
      execStart   = "${pkg}/bin/toshy-wlroots-dbus-service";
      syslogId    = "toshy-wlroots-dbus";
    };

    systemd.user.services.toshy-cosmic-dbus = mkDbusService {
      description = "Toshy COSMIC D-Bus Service";
      execStart   = "${pkg}/bin/toshy-cosmic-dbus-service";
      syslogId    = "toshy-cosmic-dbus";
    };

  };
}

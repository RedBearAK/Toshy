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

      serviceConfig = {
        Type                  = "simple";
        ExecStart             = "${pkg}/bin/toshy-kwin-dbus-service";
        Restart               = "on-failure";
        RestartSec            = 5;
        StartLimitBurst       = 5;
        StartLimitIntervalSec = 60;
        SyslogIdentifier      = "toshy-kwin-dbus";
      };

      environment = {
        TERM = "xterm";
      };
    };

    systemd.user.services.toshy-wlroots-dbus = {
      description = "Toshy Wlroots D-Bus Service";

      wantedBy = [ "default.target" ];

      serviceConfig = {
        Type                  = "simple";
        ExecStart             = "${pkg}/bin/toshy-wlroots-dbus-service";
        Restart               = "on-failure";
        RestartSec            = 5;
        StartLimitBurst       = 5;
        StartLimitIntervalSec = 60;
        SyslogIdentifier      = "toshy-wlroots-dbus";
      };

      environment = {
        TERM = "xterm";
      };
    };

    systemd.user.services.toshy-cosmic-dbus = {
      description = "Toshy COSMIC D-Bus Service";

      wantedBy = [ "default.target" ];

      serviceConfig = {
        Type                  = "simple";
        ExecStart             = "${pkg}/bin/toshy-cosmic-dbus-service";
        Restart               = "on-failure";
        RestartSec            = 5;
        StartLimitBurst       = 5;
        StartLimitIntervalSec = 60;
        SyslogIdentifier      = "toshy-cosmic-dbus";
      };

      environment = {
        TERM = "xterm";
      };
    };

  };
}

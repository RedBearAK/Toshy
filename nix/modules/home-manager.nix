{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.toshy;

  # Python environment with all dependencies needed by toshy config
  # xwaykeyz comes from the toshy overlay and is added to python packages
  toshyPython = pkgs.python3.withPackages (ps: [
    ps.dbus-python
    ps.pygobject3
    ps.watchdog
    ps.psutil
    ps.evdev
    pkgs.xwaykeyz  # From toshy overlay
  ]);

  # Default configuration file
  defaultConfig = "${pkgs.toshy}/share/toshy/default-toshy-config/toshy_config.py";

  # Configuration file to use (user's custom or default)
  configFile = if cfg.config != null then cfg.config else defaultConfig;

in
{
  options.services.toshy = {
    enable = mkEnableOption "Toshy keyboard remapper";

    package = mkOption {
      type = types.package;
      default = pkgs.toshy;
      defaultText = literalExpression "pkgs.toshy";
      description = "The Toshy package to use.";
    };

    config = mkOption {
      type = types.nullOr types.path;
      default = null;
      example = literalExpression "./toshy_config.py";
      description = ''
        Path to custom Toshy configuration file.
        If null, uses the default configuration from the package.

        You can copy the default config to customize it:
        ```
        cp ${defaultConfig} ~/.config/toshy/toshy_config.py
        ```
      '';
    };

    autoStart = mkOption {
      type = types.bool;
      default = true;
      description = "Whether to auto-start Toshy on login.";
    };

    enableGui = mkOption {
      type = types.bool;
      default = true;
      description = ''
        Whether to enable GUI components (preferences app and tray icon).
        Disable this for headless systems or if you don't need the GUI.
      '';
    };

    enableTray = mkOption {
      type = types.bool;
      default = true;
      description = "Whether to enable the system tray icon.";
    };

    desktopEnvironment = mkOption {
      type = types.nullOr (types.enum [ "kde" "gnome" "cosmic" "sway" "hyprland" "xfce" "cinnamon" ]);
      default = null;
      example = "kde";
      description = ''
        Override desktop environment detection.
        If null, Toshy will auto-detect the DE.
        Set this if auto-detection doesn't work correctly.
      '';
    };

    verboseLogging = mkOption {
      type = types.bool;
      default = false;
      description = "Enable verbose logging for debugging.";
    };
  };

  config = mkIf cfg.enable {
    # Ensure required packages are available
    home.packages = with pkgs; [
      cfg.package
      pkgs.xwaykeyz
    ] ++ optionals cfg.enableGui [
      gtk3
      libappindicator-gtk3
    ];

    # Main keymapper service
    systemd.user.services.toshy-config = {
      Unit = {
        Description = "Toshy Keyboard Config";
        Documentation = "https://github.com/RedBearAK/toshy";
        After = [ "graphical-session.target" ]
          ++ optional (cfg.desktopEnvironment == "gnome") "org.gnome.Shell.target";
        PartOf = [ "graphical-session.target" ];
        ConditionEnvironment = "WAYLAND_DISPLAY";  # Adjust based on session type
      };

      Service = {
        Type = "simple";
        # Use Python environment with all dependencies (watchdog, psutil, evdev, xwaykeyz, etc.)
        ExecStart = "${toshyPython}/bin/xwaykeyz -c ${configFile}" + optionalString cfg.verboseLogging " -v";
        Restart = "on-failure";
        RestartSec = 3;

        # Environment variables - critical for finding toshy Python modules
        Environment = [
          "PYTHONPATH=${cfg.package}/share/toshy"
        ] ++ optional (cfg.desktopEnvironment != null) "TOSHY_DE_OVERRIDE=${cfg.desktopEnvironment}";
      };

      Install = mkIf cfg.autoStart {
        WantedBy = [ "graphical-session.target" ];
      };
    };

    # Session monitor service
    systemd.user.services.toshy-session-monitor = {
      Unit = {
        Description = "Toshy Session Monitor";
        Documentation = "https://github.com/RedBearAK/toshy";
        After = [ "graphical-session.target" ];
        PartOf = [ "graphical-session.target" ];
      };

      Service = {
        Type = "simple";
        ExecStart = "${cfg.package}/share/toshy/scripts/toshy-service-session-monitor-dbus.sh";
        Restart = "on-failure";
        RestartSec = 3;
      };

      Install = mkIf cfg.autoStart {
        WantedBy = [ "graphical-session.target" ];
      };
    };

    # KDE Plasma D-Bus service (only for KDE)
    systemd.user.services.toshy-kwin-dbus = mkIf (cfg.desktopEnvironment == "kde") {
      Unit = {
        Description = "Toshy KWin D-Bus Service";
        Documentation = "https://github.com/RedBearAK/toshy";
        After = [ "graphical-session.target" ];
        PartOf = [ "graphical-session.target" ];
        ConditionEnvironment = "WAYLAND_DISPLAY";
      };

      Service = {
        Type = "dbus";
        BusName = "org.toshy.Kwin";
        ExecStart = "${cfg.package}/bin/toshy-kwin-dbus-service";
        Restart = "on-failure";
        RestartSec = 3;
      };

      Install = mkIf cfg.autoStart {
        WantedBy = [ "graphical-session.target" ];
      };
    };

    # COSMIC D-Bus service (only for COSMIC)
    systemd.user.services.toshy-cosmic-dbus = mkIf (cfg.desktopEnvironment == "cosmic") {
      Unit = {
        Description = "Toshy COSMIC D-Bus Service";
        Documentation = "https://github.com/RedBearAK/toshy";
        After = [ "graphical-session.target" ];
        PartOf = [ "graphical-session.target" ];
        ConditionEnvironment = "WAYLAND_DISPLAY";
      };

      Service = {
        Type = "dbus";
        BusName = "org.toshy.Cosmic";
        ExecStart = "${cfg.package}/bin/toshy-cosmic-dbus-service";
        Restart = "on-failure";
        RestartSec = 3;
      };

      Install = mkIf cfg.autoStart {
        WantedBy = [ "graphical-session.target" ];
      };
    };

    # Wlroots D-Bus service (for Sway, Hyprland, etc.)
    systemd.user.services.toshy-wlroots-dbus = mkIf (elem cfg.desktopEnvironment [ "sway" "hyprland" ]) {
      Unit = {
        Description = "Toshy Wlroots D-Bus Service";
        Documentation = "https://github.com/RedBearAK/toshy";
        After = [ "graphical-session.target" ];
        PartOf = [ "graphical-session.target" ];
        ConditionEnvironment = "WAYLAND_DISPLAY";
      };

      Service = {
        Type = "dbus";
        BusName = "org.toshy.Wlroots";
        ExecStart = "${cfg.package}/bin/toshy-wlroots-dbus-service";
        Restart = "on-failure";
        RestartSec = 3;
      };

      Install = mkIf cfg.autoStart {
        WantedBy = [ "graphical-session.target" ];
      };
    };

    # Tray icon service
    systemd.user.services.toshy-tray = mkIf (cfg.enableGui && cfg.enableTray) {
      Unit = {
        Description = "Toshy System Tray Icon";
        Documentation = "https://github.com/RedBearAK/toshy";
        After = [ "graphical-session.target" "toshy-config.service" ];
        PartOf = [ "graphical-session.target" ];
      };

      Service = {
        Type = "simple";
        ExecStart = "${cfg.package}/bin/toshy-tray";
        Restart = "on-failure";
        RestartSec = 3;
      };

      Install = mkIf cfg.autoStart {
        WantedBy = [ "graphical-session.target" ];
      };
    };

    # Create config directory and copy default config if using custom config
    home.activation.toshySetup = mkIf (cfg.config != null) (
      lib.hm.dag.entryAfter ["writeBoundary"] ''
        $DRY_RUN_CMD mkdir -p $HOME/.config/toshy
        if [ ! -f "$HOME/.config/toshy/toshy_config.py" ]; then
          $DRY_RUN_CMD cp ${defaultConfig} $HOME/.config/toshy/toshy_config.py
          $VERBOSE_ECHO "Created default Toshy config at ~/.config/toshy/toshy_config.py"
        fi
      ''
    );
  };
}

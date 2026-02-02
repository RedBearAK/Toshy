{ lib
, stdenv
, fetchFromGitHub
, makeWrapper
, python3
, xwaykeyz
, git
, systemd
, dbus
, libnotify
, zenity
, cairo
, gobject-introspection
, libappindicator-gtk3
, libadwaita
, libxkbcommon
, wayland
, gcc
, libjpeg
, evtest
, xorg
, pkg-config
, wrapGAppsHook3
, bash
, coreutils
, procps
, src ? null  # Allow flake to override with local source
}:

let
  pythonEnv = python3.withPackages (ps: with ps; [
    dbus-python
    pygobject3
    watchdog
    psutil
    evdev
    xwaykeyz
  ]);

  # Source handling: flake overrides with local src, otherwise fetch from GitHub
  # When building from flake: src = self (passed from flake.nix)
  # When building standalone: fetches from GitHub (requires real hash)
  # Placeholder hash is acceptable because flake ALWAYS overrides src
  finalSrc = if src != null then src else fetchFromGitHub {
    owner = "RedBearAK";
    repo = "toshy";
    rev = "ff0646b04f354b4665e1246bee8f69f338d04925";  # Pin to specific commit
    # Get hash with: nix-prefetch-url --unpack https://github.com/RedBearAK/toshy/archive/REV.tar.gz
    hash = "sha256-0000000000000000000000000000000000000000000=";  # Placeholder - Update when publishing to nixpkgs
  };

in stdenv.mkDerivation rec {
  pname = "toshy";
  version = "20260202";

  src = finalSrc;

  nativeBuildInputs = [
    makeWrapper
    wrapGAppsHook3
    pkg-config
  ];

  buildInputs = [
    pythonEnv
    systemd
    dbus
    libnotify
    zenity
    cairo
    gobject-introspection
    libappindicator-gtk3
    libadwaita
    libxkbcommon
    wayland
    gcc
    libjpeg
    evtest
    xorg.xset
  ];

  # Don't strip Python bytecode
  dontStrip = true;

  installPhase = ''
    runHook preInstall

    # Create directory structure
    mkdir -p $out/{bin,share/toshy,libexec/toshy,share/applications,share/systemd/user}

    # Install Python modules
    cp -r toshy_common $out/share/toshy/
    cp -r toshy_gui $out/share/toshy/
    cp -r default-toshy-config $out/share/toshy/

    # Install D-Bus services
    cp -r kwin-dbus-service $out/libexec/toshy/
    cp -r cosmic-dbus-service $out/libexec/toshy/
    cp -r wlroots-dbus-service $out/libexec/toshy/

    # Install main programs
    cp toshy_tray.py $out/share/toshy/
    cp toshy_layout_selector.py $out/share/toshy/

    # Install systemd service units
    cp systemd-user-service-units/*.service $out/share/systemd/user/

    # Install desktop files
    cp desktop/*.desktop $out/share/applications/

    # Hide internal/service desktop files from app launcher
    # Only the Preferences app should be visible
    for desktop in $out/share/applications/Toshy_*.desktop; do
      substituteInPlace "$desktop" --replace-warn "NoDisplay=false" "NoDisplay=true"
    done

    # Fix Preferences desktop file to use Nix store path
    substituteInPlace $out/share/applications/app.toshy.preferences.desktop \
      --replace-warn '$HOME/.local/bin/toshy-gui' "$out/bin/toshy-gui"

    # Install scripts
    mkdir -p $out/share/toshy/scripts
    cp scripts/*.sh $out/share/toshy/scripts/
    cp scripts/*.py $out/share/toshy/scripts/

    # Create wrapper scripts for bin commands
    # These replace the venv-based commands from toshy-bincommands-setup.sh

    # Main config command
    makeWrapper ${pythonEnv}/bin/python $out/bin/toshy-config-start \
      --add-flags "$out/share/toshy/default-toshy-config/toshy_config.py" \
      --prefix PATH : ${lib.makeBinPath [ xwaykeyz ]} \
      --set PYTHONPATH "$out/share/toshy"

    # GUI commands
    makeWrapper ${pythonEnv}/bin/python $out/bin/toshy-gui \
      --add-flags "$out/share/toshy/toshy_gui/main_gtk4.py" \
      --set PYTHONPATH "$out/share/toshy"

    makeWrapper ${pythonEnv}/bin/python $out/bin/toshy-tray \
      --add-flags "$out/share/toshy/toshy_tray.py" \
      --set PYTHONPATH "$out/share/toshy"

    makeWrapper ${pythonEnv}/bin/python $out/bin/toshy-layout-selector \
      --add-flags "$out/share/toshy/toshy_layout_selector.py" \
      --set PYTHONPATH "$out/share/toshy"

    # D-Bus service commands
    makeWrapper ${pythonEnv}/bin/python $out/bin/toshy-kwin-dbus-service \
      --add-flags "$out/libexec/toshy/kwin-dbus-service/toshy_kwin_dbus_service.py" \
      --set PYTHONPATH "$out/share/toshy"

    makeWrapper ${pythonEnv}/bin/python $out/bin/toshy-cosmic-dbus-service \
      --add-flags "$out/libexec/toshy/cosmic-dbus-service/toshy_cosmic_dbus_service.py" \
      --set PYTHONPATH "$out/share/toshy"

    makeWrapper ${pythonEnv}/bin/python $out/bin/toshy-wlroots-dbus-service \
      --add-flags "$out/libexec/toshy/wlroots-dbus-service/toshy_wlroots_dbus_service.py" \
      --set PYTHONPATH "$out/share/toshy"

    # Helper scripts
    makeWrapper $out/share/toshy/scripts/toshy-env-dump.sh $out/bin/toshy-env \
      --prefix PATH : ${lib.makeBinPath [ systemd dbus ]}

    # Copy service control scripts to libexec and create wrappers
    # These scripts are used by both GUI and CLI
    mkdir -p $out/libexec/toshy/bin
    cp scripts/bin/*.sh $out/libexec/toshy/bin/

    # Service control script wrappers
    makeWrapper $out/libexec/toshy/bin/toshy-config-stop.sh $out/bin/toshy-config-stop \
      --prefix PATH : ${lib.makeBinPath [ coreutils procps ]}

    makeWrapper $out/libexec/toshy/bin/toshy-config-restart.sh $out/bin/toshy-config-restart \
      --prefix PATH : ${lib.makeBinPath [ systemd coreutils procps ]}

    makeWrapper $out/libexec/toshy/bin/toshy-services-start.sh $out/bin/toshy-services-start \
      --prefix PATH : ${lib.makeBinPath [ systemd coreutils ]}

    makeWrapper $out/libexec/toshy/bin/toshy-services-stop.sh $out/bin/toshy-services-stop \
      --prefix PATH : ${lib.makeBinPath [ systemd coreutils ]}

    makeWrapper $out/libexec/toshy/bin/toshy-services-restart.sh $out/bin/toshy-services-restart \
      --prefix PATH : ${lib.makeBinPath [ systemd coreutils ]}

    makeWrapper $out/libexec/toshy/bin/toshy-services-status.sh $out/bin/toshy-services-status \
      --prefix PATH : ${lib.makeBinPath [ systemd coreutils ]}

    makeWrapper $out/libexec/toshy/bin/toshy-services-log.sh $out/bin/toshy-services-log \
      --prefix PATH : ${lib.makeBinPath [ systemd coreutils ]}

    makeWrapper $out/libexec/toshy/bin/toshy-devices.sh $out/bin/toshy-devices \
      --prefix PATH : ${lib.makeBinPath [ pythonEnv coreutils ]} \
      --set PYTHONPATH "$out/share/toshy"

    # Patch systemd service files to use Nix store paths
    for service in $out/share/systemd/user/*.service; do
      substituteInPlace $service \
        --replace-warn "%h/.config/toshy/.venv/bin/python" "${pythonEnv}/bin/python" \
        --replace-warn "%h/.config/toshy" "$out/share/toshy" \
        --replace-warn "\$HOME/.config/toshy" "$out/share/toshy"
    done

    runHook postInstall
  '';

  meta = with lib; {
    description = "Keyboard remapper for Linux with macOS-style shortcuts";
    longDescription = ''
      Toshy is a config file for the xwaykeyz keymapper that makes your Linux
      keyboard behave like a Mac keyboard, with support for both X11 and Wayland.
    '';
    homepage = "https://github.com/RedBearAK/toshy";
    license = licenses.gpl3Plus;
    maintainers = [ ];
    platforms = platforms.linux;
    mainProgram = "toshy-config-start";
  };
}

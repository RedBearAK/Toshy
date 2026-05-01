{
  description = "Toshy - Mac-style keybindings for Linux";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    # ── Per-system outputs (packages, devShells) ──────────────────
    flake-utils.lib.eachSystem [
      "x86_64-linux"
      "aarch64-linux"
    ] (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        lib  = nixpkgs.lib;

        # ── Python overlay ────────────────────────────────────────
        # Apply version pinning (python-xlib 0.31, xkbcommon <1.1, hyprpy)
        # to the Python package set.
        pythonOverlay = import ./nix/python-overlay.nix;
        python = pkgs.python3.override {
          packageOverrides = pythonOverlay;
          self = python;
        };

        # Handle nixpkgs renames for compatibility across versions
        systemdPython    = python.pkgs.systemd-python or python.pkgs.systemd;
        xhostPkg         = pkgs.xhost or pkgs.xorg.xhost;
        xsetPkg          = pkgs.xset or pkgs.xorg.xset;
        wrapGAppsHookPkg = pkgs.wrapGAppsHook3 or pkgs.wrapGAppsHook;

        # ── xwaykeyz ─────────────────────────────────────────────
        xwaykeyz = python.pkgs.callPackage ./nix/xwaykeyz.nix {};

        # ── Python runtime dependencies ──────────────────────────
        # Single source of truth for all Python packages needed at runtime.
        # Referenced by propagatedBuildInputs, makeWrapperArgs PYTHONPATH,
        # and postInstall D-Bus service wrappers.
        runtimePythonDeps = [
          xwaykeyz
        ] ++ (with python.pkgs; [
          appdirs
          dbus-python
          evdev
          hyprpy
          i3ipc
          inotify-simple
          lockfile
          ordered-set
          pillow
          psutil
          pygobject3
          pywayland
          six
          watchdog
          xlib
          xkbcommon
        ]) ++ [ systemdPython ];

        # ── Upstream Toshy source ────────────────────────────────
        toshySrc = pkgs.fetchFromGitHub {
          owner = "RedBearAK";
          repo = "toshy";
          rev = "Toshy_v26.03.0";
          hash = "sha256-doY9BBwKQ7/XLjOPW54AtREXIAx6l1G/X/jyF3X7Ktw=";
        };

        # Overlay our pyproject.toml onto the upstream source
        toshySrcWithPyproject = pkgs.runCommand "toshy-src" {} ''
          cp -r ${toshySrc} $out
          chmod -R u+w $out
          cp ${./pyproject.toml} $out/pyproject.toml

          # Patch tray to start with active icon (on NixOS, services are
          # already running when the tray starts) and force a periodic
          # icon refresh to work around quickshell caching.
          ${pkgs.gnused}/bin/sed -i 's|icon_name=icon_file_grayscale,|icon_name=icon_file_active,|' \
            $out/toshy_tray.py

          # Patch terminal_utils to include foot (common on Wayland/Hyprland)
          ${pkgs.gnused}/bin/sed -i "/('kitty',/i\\    ('foot',                    ['-e'],     []                                 )," \
            $out/toshy_common/terminal_utils.py
        '';

        # ── Toshy package ────────────────────────────────────────
        toshy = python.pkgs.buildPythonApplication rec {
          pname   = "toshy";
          version = "26.03.0";
          format  = "pyproject";

          src = toshySrcWithPyproject;

          nativeBuildInputs = with python.pkgs; [
            setuptools
            wheel
          ] ++ (with pkgs; [
            wrapGAppsHookPkg
            gobject-introspection
          ]);

          buildInputs = with pkgs; [
            gtk3
            gtk4
            gobject-introspection
            libappindicator-gtk3
            libayatana-appindicator
            libnotify
            libadwaita
            gsettings-desktop-schemas
          ];

          propagatedBuildInputs = runtimePythonDeps;

          doCheck = false;

          # Add runtime tools to PATH for all wrapped binaries.
          # wrapGAppsHook3 applies these to every binary it wraps.
          makeWrapperArgs = [
            "--prefix" "PATH" ":" (lib.makeBinPath [
              pkgs.procps
              pkgs.coreutils
              pkgs.systemd
              pkgs.gnugrep
              pkgs.glib
              pkgs.libnotify
              pkgs.zenity
              pkgs.foot
              pkgs.xdg-utils
            ])
            "--suffix" "PATH" ":" "/run/current-system/sw/bin:/run/wrappers/bin"
            "--suffix" "XDG_DATA_DIRS" ":" "/run/current-system/sw/share"
            "--prefix" "PYTHONPATH" ":" (python.pkgs.makePythonPath runtimePythonDeps)
          ];

          postInstall = let
            runtimePythonPath = python.pkgs.makePythonPath runtimePythonDeps;
          in ''
            SITE="$out/lib/${python.libPrefix}/site-packages"
            FULL_PYTHONPATH="$SITE:${runtimePythonPath}"

            # ── 1. Install upstream shell scripts ───────────────────
            install -Dm755 scripts/tshysvc-config  "$out/libexec/toshy/tshysvc-config"
            install -Dm755 scripts/tshysvc-sessmon "$out/libexec/toshy/tshysvc-sessmon"

            substituteInPlace "$out/libexec/toshy/tshysvc-config" \
              --replace-fail '#!/usr/bin/bash' '#!${pkgs.bash}/bin/bash'
            substituteInPlace "$out/libexec/toshy/tshysvc-sessmon" \
              --replace-fail '#!/usr/bin/bash' '#!${pkgs.bash}/bin/bash'

            # ── 2. Install D-Bus service scripts and data ───────────
            cp -r kwin-dbus-service    "$SITE/kwin-dbus-service"
            cp -r wlroots-dbus-service "$SITE/wlroots-dbus-service"
            cp -r cosmic-dbus-service  "$SITE/cosmic-dbus-service"
            cp -r default-toshy-config "$SITE/default-toshy-config"
            cp -r kwin-script          "$SITE/kwin-script"
            cp -r scripts              "$SITE/scripts"
            cp -r systemd-user-service-units "$SITE/systemd-user-service-units" || true

            # ── 3. Wrap tshysvc-config ──────────────────────────────
            # makeWrapperArgs already provides procps, coreutils, systemd,
            # gnugrep, etc. to all wrapped binaries. This wrapper only adds
            # tools specific to tshysvc-config: xwaykeyz, xhost, xset.
            makeWrapper "$out/libexec/toshy/tshysvc-config" "$out/bin/tshysvc-config" \
              --prefix PATH : "${lib.makeBinPath [
                xwaykeyz
                xhostPkg
                xsetPkg
                pkgs.bash
              ]}" \
              --prefix PYTHONPATH : "$FULL_PYTHONPATH"

            # Remove venv activation — not needed in Nix
            substituteInPlace "$out/libexec/toshy/tshysvc-config" \
              --replace-quiet 'source "$HOME/.config/toshy/.venv/bin/activate"' \
                              '# venv activation removed — Nix handles PATH/PYTHONPATH'

            # ── 4. Wrap tshysvc-sessmon ─────────────────────────────
            makeWrapper "$out/libexec/toshy/tshysvc-sessmon" "$out/bin/tshysvc-sessmon" \
              --prefix PATH : "${lib.makeBinPath [
                pkgs.coreutils
                pkgs.systemd
                pkgs.procps
                pkgs.bash
                pkgs.gnugrep
              ]}"

            # ── 5. D-Bus service Python wrappers ────────────────────
            # Each D-Bus service needs PYTHONPATH with toshy site-packages
            # and its own directory (for relative protocol imports).
            makeWrapper "${python}/bin/python" "$out/bin/toshy-kwin-dbus-service" \
              --add-flags "$SITE/kwin-dbus-service/toshy_kwin_dbus_service.py" \
              --prefix PYTHONPATH : "$FULL_PYTHONPATH:$SITE/kwin-dbus-service" \
              --prefix PATH : "${lib.makeBinPath [ pkgs.procps ]}"

            makeWrapper "${python}/bin/python" "$out/bin/toshy-wlroots-dbus-service" \
              --add-flags "$SITE/wlroots-dbus-service/toshy_wlroots_dbus_service.py" \
              --prefix PYTHONPATH : "$FULL_PYTHONPATH:$SITE/wlroots-dbus-service" \
              --prefix PATH : "${lib.makeBinPath [ pkgs.procps ]}"

            makeWrapper "${python}/bin/python" "$out/bin/toshy-cosmic-dbus-service" \
              --add-flags "$SITE/cosmic-dbus-service/toshy_cosmic_dbus_service.py" \
              --prefix PYTHONPATH : "$FULL_PYTHONPATH:$SITE/cosmic-dbus-service" \
              --prefix PATH : "${lib.makeBinPath [ pkgs.procps ]}"

            # ── 6. Desktop files ────────────────────────────────────
            mkdir -p "$out/share/applications"
            for f in desktop/*.desktop; do
              install -Dm644 "$f" "$out/share/applications/$(basename "$f")"
            done

            substituteInPlace "$out/share/applications/Toshy_Tray.desktop" \
              --replace-quiet 'Exec=$HOME/.local/bin/toshy-tray' \
                              "Exec=$out/bin/toshy-tray"
            substituteInPlace "$out/share/applications/app.toshy.preferences.desktop" \
              --replace-quiet 'Exec=$HOME/.local/bin/toshy-gui' \
                              "Exec=$out/bin/toshy-gui"
            substituteInPlace "$out/share/applications/Toshy_KWin_DBus_Service.desktop" \
              --replace-quiet "Exec=/bin/sh -c 'exec env \$HOME/.local/bin/toshy-kwin-dbus-service'" \
                              "Exec=$out/bin/toshy-kwin-dbus-service"

            # ── 7. Icons ────────────────────────────────────────────
            mkdir -p "$out/share/icons/hicolor/scalable/apps"
            mkdir -p "$out/share/icons/hicolor/36x36/apps"
            mkdir -p "$out/share/icons/hicolor/512x512/apps"

            install -Dm644 assets/toshy_app_icon_rainbow.svg \
              "$out/share/icons/hicolor/scalable/apps/toshy_app_icon_rainbow.svg"
            install -Dm644 assets/toshy_app_icon_rainbow_inverse.svg \
              "$out/share/icons/hicolor/scalable/apps/toshy_app_icon_rainbow_inverse.svg"
            install -Dm644 assets/toshy_app_icon_rainbow_inverse_grayscale.svg \
              "$out/share/icons/hicolor/scalable/apps/toshy_app_icon_rainbow_inverse_grayscale.svg"
            install -Dm644 assets/toshy_app_icon_rainbow_36px.png \
              "$out/share/icons/hicolor/36x36/apps/toshy_app_icon_rainbow.png"
            install -Dm644 assets/toshy_app_icon_rainbow_512px.png \
              "$out/share/icons/hicolor/512x512/apps/toshy_app_icon_rainbow.png"

            cp -r assets/Toshy-Icon-Theme "$out/share/icons/Toshy-Icon-Theme"

            # ── 8. Verify critical outputs ──────────────────────────
            for bin in tshysvc-config tshysvc-sessmon \
                       toshy-kwin-dbus-service toshy-wlroots-dbus-service \
                       toshy-cosmic-dbus-service; do
              test -x "$out/bin/$bin" || {
                echo "ERROR: $out/bin/$bin was not produced"
                exit 1
              }
            done
          '';

          pythonImportsCheck = [
            "toshy_common"
            "toshy_gui"
          ];

          passthru = {
            inherit python;
          };

          meta = {
            description     = "Mac-style keyboard remapping for Linux";
            homepage        = "https://github.com/RedBearAK/toshy";
            license         = lib.licenses.gpl3Plus;
            maintainers     = [];
            platforms       = lib.platforms.linux;
            mainProgram     = "toshy-tray";
          };
        };

      in {
        packages = {
          inherit toshy xwaykeyz;
          default = toshy;
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            python
            python.pkgs.setuptools
            python.pkgs.wheel
            pkgs.nixpkgs-fmt
            pkgs.git
          ];

          shellHook = ''
            echo "Toshy development environment (${system})"
            echo "Python: $(python3 --version)"
          '';
        };

        formatter = pkgs.nixpkgs-fmt;
      }

    # ── System-independent outputs ──────────────────────────────────
    ) // {
      nixosModules.toshy = { pkgs, lib, ... }: {
        imports = [ ./modules/toshy.nix ];
        services.toshy.package = lib.mkDefault self.packages.${pkgs.stdenv.hostPlatform.system}.toshy;
      };
      nixosModules.default = self.nixosModules.toshy;

      homeManagerModules.toshy = { pkgs, lib, ... }: {
        imports = [ ./home-manager/toshy.nix ];
        services.toshy.package = lib.mkDefault self.packages.${pkgs.stdenv.hostPlatform.system}.toshy;
      };
      homeManagerModules.default = self.homeManagerModules.toshy;

      overlays.default = final: prev: {
        toshy    = self.packages.${prev.system}.toshy;
        xwaykeyz = self.packages.${prev.system}.xwaykeyz;
      };
    };
}

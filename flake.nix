{
  description = "Toshy - Mac-style keybindings for Linux";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    # ── Per-system outputs (packages, devShells) ──────────────────────
    flake-utils.lib.eachSystem [
      "x86_64-linux"
      "aarch64-linux"
    ] (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        lib  = nixpkgs.lib;

        # ── Python overlay ────────────────────────────────────────────
        # Apply version pinning (python-xlib 0.31, xkbcommon <1.1, hyprpy)
        # to the Python package set. This ensures version consistency across
        # the entire dependency graph without catchConflicts = false.
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

        # ── xwaykeyz ─────────────────────────────────────────────────
        # Built from the overlaid Python package set so it picks up the
        # pinned python-xlib and hyprpy automatically.
        xwaykeyz = python.pkgs.callPackage ./nix/xwaykeyz.nix {};

        # ── Site-packages path helper ────────────────────────────────
        # Used by D-Bus service wrappers to set PYTHONPATH.
        pythonSitePackages = "${python.sitePackages}";

        # ── Upstream Toshy source ────────────────────────────────────
        # Fetch directly from RedBearAK/toshy upstream. The pyproject.toml
        # is overlaid from this flake since upstream doesn't have one yet.
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

        # ── Toshy package ────────────────────────────────────────────
        toshy = python.pkgs.buildPythonApplication rec {
          pname   = "toshy";
          version = "26.03.0";
          format  = "pyproject";

          src = toshySrcWithPyproject;

          # ── Build-time tools ──────────────────────────────────────
          nativeBuildInputs = with python.pkgs; [
            setuptools
            wheel
          ] ++ (with pkgs; [
            wrapGAppsHookPkg
            gobject-introspection
            # makeWrapper is provided implicitly by wrapGAppsHook3
          ]);

          # ── Native libraries (C/GTK) ─────────────────────────────
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

          # ── Python runtime dependencies ───────────────────────────
          # These propagate into the wrapper environment so that all
          # Python imports work at runtime.
          propagatedBuildInputs = [
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
            xlib        # pinned to 0.31 by overlay
            xkbcommon   # pinned to 0.8 by overlay
          ]) ++ [ systemdPython ];

          # Don't run the test suite (requires evdev/uinput access).
          doCheck = false;

          # Add runtime tools to PATH for all wrapped binaries.
          # wrapGAppsHook3 will include these when wrapping.
          makeWrapperArgs = [
            "--prefix" "PATH" ":" (lib.makeBinPath [
              pkgs.procps        # pgrep, pkill (used by env_context.py)
              pkgs.coreutils     # whoami, etc.
              pkgs.systemd       # systemctl, loginctl
              pkgs.gnugrep       # grep
              pkgs.glib          # gdbus
              pkgs.libnotify     # notify-send
              pkgs.zenity        # zenity dialogs
              pkgs.foot          # terminal emulator for log viewing
              pkgs.xdg-utils    # xdg-open for opening files/URLs
            ])
            # Append system PATH so xdg-open can find file managers, browsers, etc.
            "--suffix" "PATH" ":" "/run/current-system/sw/bin:/run/wrappers/bin"
            "--prefix" "PYTHONPATH" ":" (python.pkgs.makePythonPath [
              xwaykeyz
              python.pkgs.appdirs
              python.pkgs.dbus-python
              python.pkgs.evdev
              python.pkgs.hyprpy
              python.pkgs.i3ipc
              python.pkgs.inotify-simple
              python.pkgs.lockfile
              python.pkgs.ordered-set
              python.pkgs.pillow
              python.pkgs.psutil
              python.pkgs.pygobject3
              python.pkgs.pywayland
              python.pkgs.six
              systemdPython
              python.pkgs.watchdog
              python.pkgs.xlib
              python.pkgs.xkbcommon
            ])
          ];

          # ── postInstall ───────────────────────────────────────────
          # Install shell scripts, D-Bus service wrappers, desktop
          # files, and icons that setuptools cannot handle (they live
          # outside Python packages).
          postInstall = let
            # All Python runtime deps needed on PYTHONPATH for child processes
            # (xwaykeyz loading toshy_config.py which imports toshy_common).
            runtimePythonPath = python.pkgs.makePythonPath [
              xwaykeyz
              python.pkgs.appdirs
              python.pkgs.dbus-python
              python.pkgs.evdev
              python.pkgs.hyprpy
              python.pkgs.i3ipc
              python.pkgs.inotify-simple
              python.pkgs.lockfile
              python.pkgs.ordered-set
              python.pkgs.pillow
              python.pkgs.psutil
              python.pkgs.pygobject3
              python.pkgs.pywayland
              python.pkgs.six
              systemdPython
              python.pkgs.watchdog
              python.pkgs.xlib
              python.pkgs.xkbcommon
            ];
          in ''
            # ── Helper: site-packages directory ─────────────────────
            SITE="$out/lib/${python.libPrefix}/site-packages"
            FULL_PYTHONPATH="$SITE:${runtimePythonPath}"

            # ────────────────────────────────────────────────────────
            # 1. Install upstream shell scripts
            # ────────────────────────────────────────────────────────
            install -Dm755 scripts/tshysvc-config  "$out/libexec/toshy/tshysvc-config"
            install -Dm755 scripts/tshysvc-sessmon "$out/libexec/toshy/tshysvc-sessmon"

            # Fix shebangs — upstream uses #!/usr/bin/bash which doesn't exist on NixOS
            substituteInPlace "$out/libexec/toshy/tshysvc-config" \
              --replace-fail '#!/usr/bin/bash' '#!${pkgs.bash}/bin/bash'
            substituteInPlace "$out/libexec/toshy/tshysvc-sessmon" \
              --replace-fail '#!/usr/bin/bash' '#!${pkgs.bash}/bin/bash'

            # ────────────────────────────────────────────────────────
            # 1b. Install D-Bus service scripts and data directories
            #     into site-packages (setuptools can't install these
            #     because they're not Python packages).
            # ────────────────────────────────────────────────────────
            cp -r kwin-dbus-service    "$SITE/kwin-dbus-service"
            cp -r wlroots-dbus-service "$SITE/wlroots-dbus-service"
            cp -r cosmic-dbus-service  "$SITE/cosmic-dbus-service"
            cp -r default-toshy-config "$SITE/default-toshy-config"
            cp -r kwin-script          "$SITE/kwin-script"
            cp -r scripts              "$SITE/scripts"
            cp -r systemd-user-service-units "$SITE/systemd-user-service-units" || true

            # ────────────────────────────────────────────────────────
            # 2. Wrap tshysvc-config
            #    Replaces venv activation with Nix store PATH.
            #    Needs: xwaykeyz, pkill, xhost, xset, bash, coreutils
            # ────────────────────────────────────────────────────────
            makeWrapper "$out/libexec/toshy/tshysvc-config" "$out/bin/tshysvc-config" \
              --prefix PATH : "${lib.makeBinPath [
                xwaykeyz
                pkgs.coreutils
                pkgs.procps
                xhostPkg
                xsetPkg
                pkgs.bash
                pkgs.gnugrep
                pkgs.zenity
                pkgs.libnotify
                pkgs.glib
              ]}" \
              --prefix PYTHONPATH : "$FULL_PYTHONPATH" \

            # Patch out the venv activation line — it is not needed in Nix.
            substituteInPlace "$out/libexec/toshy/tshysvc-config" \
              --replace-quiet 'source "$HOME/.config/toshy/.venv/bin/activate"' \
                              '# venv activation removed — Nix handles PATH/PYTHONPATH'

            # ────────────────────────────────────────────────────────
            # 3. Wrap tshysvc-sessmon
            #    Pure shell script. Needs: loginctl, systemctl, pkill,
            #    whoami, sleep, grep, head, cut, bash
            # ────────────────────────────────────────────────────────
            makeWrapper "$out/libexec/toshy/tshysvc-sessmon" "$out/bin/tshysvc-sessmon" \
              --prefix PATH : "${lib.makeBinPath [
                pkgs.coreutils
                pkgs.systemd
                pkgs.procps
                pkgs.bash
                pkgs.gnugrep
              ]}"

            # ────────────────────────────────────────────────────────
            # 4. D-Bus service Python wrappers
            #    Each D-Bus service is a Python script that needs:
            #      - PYTHONPATH with toshy site-packages (toshy_common,
            #        xwaykeyz, protocols modules)
            #      - The script's own directory on PYTHONPATH (for
            #        relative protocol imports)
            # ────────────────────────────────────────────────────────

            # -- KWin D-Bus service --
            makeWrapper "${python}/bin/python" "$out/bin/toshy-kwin-dbus-service" \
              --add-flags "$SITE/kwin-dbus-service/toshy_kwin_dbus_service.py" \
              --prefix PYTHONPATH : "$FULL_PYTHONPATH:$SITE/kwin-dbus-service" \
              --prefix PATH : "${lib.makeBinPath [ pkgs.procps ]}"

            # -- Wlroots D-Bus service --
            makeWrapper "${python}/bin/python" "$out/bin/toshy-wlroots-dbus-service" \
              --add-flags "$SITE/wlroots-dbus-service/toshy_wlroots_dbus_service.py" \
              --prefix PYTHONPATH : "$FULL_PYTHONPATH:$SITE/wlroots-dbus-service" \
              --prefix PATH : "${lib.makeBinPath [ pkgs.procps ]}"

            # -- COSMIC D-Bus service --
            makeWrapper "${python}/bin/python" "$out/bin/toshy-cosmic-dbus-service" \
              --add-flags "$SITE/cosmic-dbus-service/toshy_cosmic_dbus_service.py" \
              --prefix PYTHONPATH : "$FULL_PYTHONPATH:$SITE/cosmic-dbus-service" \
              --prefix PATH : "${lib.makeBinPath [ pkgs.procps ]}"

            # ────────────────────────────────────────────────────────
            # 5. Desktop files
            #    Install .desktop files and patch Exec= lines to use
            #    Nix store paths.
            # ────────────────────────────────────────────────────────
            mkdir -p "$out/share/applications"
            for f in desktop/*.desktop; do
              install -Dm644 "$f" "$out/share/applications/$(basename "$f")"
            done

            # Patch Exec= lines to reference $out/bin instead of $HOME/.local/bin
            substituteInPlace "$out/share/applications/Toshy_Tray.desktop" \
              --replace-quiet 'Exec=$HOME/.local/bin/toshy-tray' \
                              "Exec=$out/bin/toshy-tray"
            substituteInPlace "$out/share/applications/app.toshy.preferences.desktop" \
              --replace-quiet 'Exec=$HOME/.local/bin/toshy-gui' \
                              "Exec=$out/bin/toshy-gui"
            substituteInPlace "$out/share/applications/Toshy_KWin_DBus_Service.desktop" \
              --replace-quiet "Exec=/bin/sh -c 'exec env \$HOME/.local/bin/toshy-kwin-dbus-service'" \
                              "Exec=$out/bin/toshy-kwin-dbus-service"

            # ────────────────────────────────────────────────────────
            # 7. Icons
            #    Install icons following XDG icon theme spec and the
            #    Toshy icon theme.
            # ────────────────────────────────────────────────────────

            # Main icons into hicolor theme (scalable + PNG sizes)
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

            # Toshy Icon Theme (custom theme with index.theme)
            cp -r assets/Toshy-Icon-Theme "$out/share/icons/Toshy-Icon-Theme"

            # ────────────────────────────────────────────────────────
            # 8. Verify critical outputs exist
            # ────────────────────────────────────────────────────────
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
        # ── Per-system outputs ──────────────────────────────────────
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
      # NixOS module — wraps the raw module to inject the default package
      # from this flake so users don't need to set services.toshy.package.
      nixosModules.toshy = { pkgs, lib, ... }: {
        imports = [ ./modules/toshy.nix ];
        services.toshy.package = lib.mkDefault self.packages.${pkgs.stdenv.hostPlatform.system}.toshy;
      };
      nixosModules.default = self.nixosModules.toshy;

      # Home Manager module — wraps the raw module to inject the default package.
      homeManagerModules.toshy = { pkgs, lib, ... }: {
        imports = [ ./home-manager/toshy.nix ];
        services.toshy.package = lib.mkDefault self.packages.${pkgs.stdenv.hostPlatform.system}.toshy;
      };
      homeManagerModules.default = self.homeManagerModules.toshy;

      # Overlay — adds toshy and xwaykeyz to any nixpkgs set
      overlays.default = final: prev: {
        toshy    = self.packages.${prev.system}.toshy;
        xwaykeyz = self.packages.${prev.system}.xwaykeyz;
      };
    };
}

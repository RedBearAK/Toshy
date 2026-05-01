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

        # ── xwaykeyz ─────────────────────────────────────────────────
        # Built from the overlaid Python package set so it picks up the
        # pinned python-xlib and hyprpy automatically.
        xwaykeyz = python.pkgs.callPackage ./nix/xwaykeyz.nix {};

        # ── Site-packages path helper ────────────────────────────────
        # Used by D-Bus service wrappers to set PYTHONPATH.
        pythonSitePackages = "${python.sitePackages}";

        # ── Toshy package ────────────────────────────────────────────
        toshy = python.pkgs.buildPythonApplication rec {
          pname   = "toshy";
          version = "2025.04.16";
          format  = "pyproject";

          # Use the flake source tree (contains pyproject.toml).
          src = lib.cleanSource ./.;

          # ── Build-time tools ──────────────────────────────────────
          nativeBuildInputs = with python.pkgs; [
            setuptools
            wheel
          ] ++ (with pkgs; [
            wrapGAppsHook3
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
            systemd-python
            watchdog
            xlib        # pinned to 0.31 by overlay
            xkbcommon   # pinned to 0.8 by overlay
          ]);

          # Don't run the test suite (requires evdev/uinput access).
          doCheck = false;

          # Prevent wrapGAppsHook3 from double-wrapping console scripts.
          dontWrapGApps = true;

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
              python.pkgs.systemd-python
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
                pkgs.xhost
                pkgs.xset
                pkgs.bash
                pkgs.gnugrep
                pkgs.gnome-zenity
                pkgs.libnotify
                pkgs.glib
              ]}" \
              --prefix PYTHONPATH : "$FULL_PYTHONPATH" \
              "''${gappsWrapperArgs[@]}"

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
              --prefix PATH : "${lib.makeBinPath [ pkgs.procps ]}" \
              "''${gappsWrapperArgs[@]}"

            # -- Wlroots D-Bus service --
            makeWrapper "${python}/bin/python" "$out/bin/toshy-wlroots-dbus-service" \
              --add-flags "$SITE/wlroots-dbus-service/toshy_wlroots_dbus_service.py" \
              --prefix PYTHONPATH : "$FULL_PYTHONPATH:$SITE/wlroots-dbus-service" \
              --prefix PATH : "${lib.makeBinPath [ pkgs.procps ]}" \
              "''${gappsWrapperArgs[@]}"

            # -- COSMIC D-Bus service --
            makeWrapper "${python}/bin/python" "$out/bin/toshy-cosmic-dbus-service" \
              --add-flags "$SITE/cosmic-dbus-service/toshy_cosmic_dbus_service.py" \
              --prefix PYTHONPATH : "$FULL_PYTHONPATH:$SITE/cosmic-dbus-service" \
              --prefix PATH : "${lib.makeBinPath [ pkgs.procps ]}" \
              "''${gappsWrapperArgs[@]}"

            # ────────────────────────────────────────────────────────
            # 5. Wrap the console-script entry points with GTK/GLib
            #    environment (wrapGAppsHook3 was deferred above).
            # ────────────────────────────────────────────────────────
            for prog in toshy-tray toshy-gui toshy-layout-selector; do
              if [ -f "$out/bin/.$prog-wrapped" ] || [ -f "$out/bin/$prog" ]; then
                wrapProgram "$out/bin/$prog" \
                  "''${gappsWrapperArgs[@]}"
              fi
            done

            # ────────────────────────────────────────────────────────
            # 6. Desktop files
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

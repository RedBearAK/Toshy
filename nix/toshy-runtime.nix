# Repo location: toshy/nix/toshy-runtime.nix
#
# EXPERIMENTAL. Builds the externally managed Toshy Python runtime:
# a Python environment holding all Toshy/xwaykeyz dependencies, with
# bin entries wrapped so GTK/AppIndicator gobject-introspection typelibs
# and GSettings schemas are visible (needed by the tray and the GTK4
# preferences app; the keymapper itself does not need them).
#
# The result is meant to be linked (by the home-manager module) at:
#     ${XDG_STATE_HOME:-~/.local/state}/toshy/runtime
# where Toshy's launcher scripts resolve it via toshy-runtime-env.sh.

{ lib
, python3
, fetchPypi
, runCommand
, makeWrapper
, glib
, atk
, gtk3
, gtk4
, graphene
, gdk-pixbuf
, pango
, libadwaita
, libayatana-appindicator
, gobject-introspection
, gsettings-desktop-schemas
, adwaita-icon-theme
, procps
, zenity
, libnotify
, xdg-utils
, toshySrc
, keymapperBranch ? "main"    # "main" or "dev_beta" (vendored copies in repo)
}:

let
  # Version pins are applied as a package-set overlay so that EVERY package
  # in the set resolves to the pinned versions, including transitive
  # dependents (i3ipc depends on python-xlib; without the overlay, the
  # standard 0.33 rides into the environment alongside the pinned 0.31 and
  # shadows it, which is exactly what tester logs showed).
  pythonPinned = python3.override {
    packageOverrides = pyFinal: pyPrev: {

      # python-xlib pinned to 0.31 due to a BadRRModeError attribute bug in
      # newer releases. Built from scratch; its setup.py imports
      # pkg_resources (removed in setuptools 81+) only to assert
      # setuptools >= 30, so it is built with setuptools 80 via the
      # setuptools-scm override, mirroring nixpkgs' own python-xlib.
      python-xlib = pyFinal.buildPythonPackage rec {
        pname = "python-xlib";
        version = "0.31";
        pyproject = true;
        src = fetchPypi {
          inherit pname version;
          hash = "sha256-dNg6CB9TK8B/bXr81kFuw4QD1o9oubncnh8o+/LXmek=";
        };
        build-system = [
          (pyFinal.setuptools-scm.override { setuptools = pyFinal.setuptools_80; })
        ];
        dependencies = [ pyFinal.six ];
        doCheck = false;
        pythonImportsCheck = [ "Xlib" ];
      };

      # xkbcommon pinned below 1.1 (1.5 introduced breaking API changes;
      # pin advised by the python-xkbcommon maintainer).
      xkbcommon = pyPrev.xkbcommon.overridePythonAttrs (old: {
        version = "1.0.1";
        src = fetchPypi {
          pname = "xkbcommon";
          version = "1.0.1";
          hash = "sha256-npdJ1uy6UUFhZipGi6OGiatrbpYq9C4J+6Xuq8t3bJE=";
        };
        doCheck = false;
      });
    };
  };

  pyPkgs = pythonPinned.pkgs;

  kmSrcPath = "${toshySrc}/vendors/xwaykeyz-${keymapperBranch}";

  # The vendored keymapper's hatchling "dynamic" version reads a plain file,
  # so the same file can be parsed here (no VCS metadata needed).
  kmVersionLines = lib.splitString "\n"
    (builtins.readFile "${kmSrcPath}/src/xwaykeyz/version.py");
  kmVersionMatches = lib.concatMap
    (line:
      let m = builtins.match "__version__[[:space:]]*=[[:space:]]*['\"]([^'\"]+)['\"].*" line;
      in if m == null then [ ] else m)
    kmVersionLines;
  kmVersion =
    if kmVersionMatches == [ ] then "unknown" else builtins.head kmVersionMatches;

  # ---- Packages not in nixpkgs ----

  # Not in nixpkgs. Pure Python; xwaykeyz uses it for the Hyprland backend.
  hyprpy = pyPkgs.buildPythonPackage rec {
    pname = "hyprpy";
    version = "0.1.10";
    pyproject = true;
    src = fetchPypi {
      inherit pname version;
      hash = "sha256-OX8iOglHMFAwq0LT1cE4nhpP9BxgWFcgc3potqSNIAg=";
    };
    build-system = [ pyPkgs.setuptools ];
    dependencies = [ pyPkgs.pydantic ];
    doCheck = false;
    pythonImportsCheck = [ "hyprpy" ];
  };

  # ---- The keymapper, built from the vendored source tree ----

  xwaykeyz = pyPkgs.buildPythonPackage {
    pname = "xwaykeyz";
    version = kmVersion;
    pyproject = true;
    src = kmSrcPath;
    build-system = [ pyPkgs.hatchling ];
    dependencies = with pyPkgs; [
      anyascii
      appdirs
      dbus-python
      evdev
      i3ipc
      inotify-simple
      ordered-set
      pywayland
      python-xlib
    ] ++ [
      hyprpy
    ];
    # nixpkgs ships newer versions than the compatible-release pins in the
    # keymapper's pyproject (dbus-python 1.4.x vs ~=1.3.2, inotify-simple
    # 2.x vs ~=1.3). Both are runtime-compatible for xwaykeyz's usage, so
    # those two constraints are relaxed in the wheel metadata. The strict
    # python-xlib==0.31 pin is deliberately NOT relaxed: it exists for a
    # runtime bug in newer python-xlib, the overlay-pinned 0.31 satisfies
    # it, and the check then guards that the overlay actually took effect
    # across the whole set (this is what caught the i3ipc shadowing).
    pythonRelaxDeps = [
      "dbus-python"
      "inotify-simple"
    ];
    doCheck = false;
    pythonImportsCheck = [ "xwaykeyz" ];
  };

  # ---- Full environment: Toshy app deps + the keymapper ----

  pythonEnv = pythonPinned.withPackages (ps: with ps; [
    dbus-python
    lockfile
    pillow
    psutil
    pygobject3
    sv-ttk
    systemd-python
    tkinter
    watchdog
    xkbcommon
  ] ++ [
    xwaykeyz
  ]);

  # ---- GI typelibs and schemas for the tray / GTK4 preferences app ----
  # (The wrapper below also puts required external tools on PATH; Toshy
  # shells out to pgrep/pkill (procps), gdbus/gsettings (glib), zenity,
  # notify-send (libnotify), and xdg-open (xdg-utils), none of which can be
  # assumed present on NixOS in every PATH context, e.g. systemd user
  # services or the sanitized installer environment.)

  giPackages = [
    glib
    atk
    gtk3
    gtk4
    graphene
    gdk-pixbuf
    pango
    libadwaita
    libayatana-appindicator
    gobject-introspection
  ];

  giTypelibPath = lib.makeSearchPath "lib/girepository-1.0" giPackages;

  xdgDataDirs = lib.concatStringsSep ":" [
    "${gsettings-desktop-schemas}/share/gsettings-schemas/${gsettings-desktop-schemas.name}"
    "${gtk4}/share/gsettings-schemas/${gtk4.name}"
    "${gtk3}/share/gsettings-schemas/${gtk3.name}"
    "${adwaita-icon-theme}/share"
  ];

in
runCommand "toshy-runtime-${keymapperBranch}-${kmVersion}"
  {
    nativeBuildInputs = [ makeWrapper ];
    passthru = { inherit pythonEnv xwaykeyz; };
    meta = {
      description = "Toshy externally managed Python runtime (EXPERIMENTAL)";
      platforms = lib.platforms.linux;
    };
  }
  ''
    mkdir -p $out/bin
    for exe_path in ${pythonEnv}/bin/*; do
        exe_name=$(basename "$exe_path")
        makeWrapper "$exe_path" "$out/bin/$exe_name" \
            --prefix GI_TYPELIB_PATH : "${giTypelibPath}" \
            --prefix XDG_DATA_DIRS : "${xdgDataDirs}" \
            --prefix PATH : "${lib.makeBinPath [ procps glib zenity libnotify xdg-utils ]}"
    done
  ''

# End of file #

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
, toshySrc
, keymapperBranch ? "main"    # "main" or "dev_beta" (vendored copies in repo)
}:

let
  pyPkgs = python3.pkgs;

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

  # ---- Pinned overrides (see comments in repo requirements.txt) ----

  # python-xlib pinned to 0.31 due to a BadRRModeError attribute bug in
  # newer releases. nixpkgs attr is "xlib".
  python-xlib-pinned = pyPkgs.xlib.overridePythonAttrs (old: {
    version = "0.31";
    src = fetchPypi {
      pname = "python-xlib";
      version = "0.31";
      hash = "sha256-dNg6CB9TK8B/bXr81kFuw4QD1o9oubncnh8o+/LXmek=";
    };
    doCheck = false;
  });

  # xkbcommon pinned below 1.1 (1.5 introduced breaking API changes;
  # pin advised by the python-xkbcommon maintainer).
  xkbcommon-pinned = pyPkgs.xkbcommon.overridePythonAttrs (old: {
    version = "1.0.1";
    src = fetchPypi {
      pname = "xkbcommon";
      version = "1.0.1";
      hash = "sha256-npdJ1uy6UUFhZipGi6OGiatrbpYq9C4J+6Xuq8t3bJE=";
    };
    doCheck = false;
  });

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
    ] ++ [
      hyprpy
      python-xlib-pinned
    ];
    doCheck = false;
    pythonImportsCheck = [ "xwaykeyz" ];
  };

  # ---- Full environment: Toshy app deps + the keymapper ----

  pythonEnv = python3.withPackages (ps: with ps; [
    dbus-python
    lockfile
    pillow
    psutil
    pygobject3
    sv-ttk
    systemd
    tkinter
    watchdog
  ] ++ [
    xkbcommon-pinned
    xwaykeyz
  ]);

  # ---- GI typelibs and schemas for the tray / GTK4 preferences app ----

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
            --prefix XDG_DATA_DIRS : "${xdgDataDirs}"
    done
  ''

# End of file #

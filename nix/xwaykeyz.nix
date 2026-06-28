# xwaykeyz - Linux keymapper for X11 and Wayland.
#
# xwaykeyz is a fork of keyszer that adds Wayland support. It is the
# keymapper engine that Toshy depends on for remapping keyboard input.
# This package is not available in nixpkgs, so we build it from source.
#
# The upstream repo has no release tags, so we pin to a specific commit
# corresponding to version 1.17.1. When tags are created upstream, the
# rev should be updated to use a tag instead.
#
# GitHub: https://github.com/RedBearAK/xwaykeyz

{ lib
, buildPythonPackage
, fetchFromGitHub
, hatchling
, appdirs
, dbus-python
, evdev
, i3ipc
, inotify-simple
, ordered-set
, pywayland
, xlib
, hyprpy
}:

buildPythonPackage rec {
  pname = "xwaykeyz";
  version = "1.17.1";
  format = "pyproject";

  src = fetchFromGitHub {
    owner = "RedBearAK";
    repo = "xwaykeyz";
    # Pinned to commit for version 1.17.1 (no release tags exist upstream).
    # To update: change rev and hash when a new version is released.
    rev = "76c0fbacba90ba4038265c1d336af888dbf2c480";
    hash = "sha256-ZJES+IL3wAM8A6AqU9XbRYWSy9RnJuijvmjY7+w2cVM=";
  };

  nativeBuildInputs = [
    hatchling
  ];

  # Relax overly strict version constraints that conflict with nixpkgs.
  # - dbus-python ~=1.3.2 excludes 1.4.0 (nixpkgs), but 1.4.0 is compatible
  # - hyprpy ~=0.1.5 excludes 0.2.1 (latest on PyPI), but 0.2.1 works fine
  postPatch = ''
    substituteInPlace pyproject.toml \
      --replace-fail '"dbus-python ~= 1.3.2"' '"dbus-python >= 1.3.2"' \
      --replace-fail '"hyprpy ~= 0.1.5"' '"hyprpy >= 0.1.5"' \
      --replace-fail '"inotify_simple ~= 1.3"' '"inotify_simple >= 1.3"' \
      --replace-fail '"python-xlib == 0.31"' '"python-xlib >= 0.31"'
  '';

  propagatedBuildInputs = [
    appdirs
    dbus-python
    evdev
    hyprpy
    i3ipc
    inotify-simple
    ordered-set
    pywayland
    xlib
  ];

  # Tests require evdev devices and uinput access (not available in sandbox)
  doCheck = false;

  # i3ipc brings in nixpkgs python-xlib 0.33 while we pin 0.31 via overlay.
  # Both versions coexist safely; suppress the false-positive conflict.
  catchConflicts = false;

  pythonImportsCheck = [
    "xwaykeyz"
  ];

  # Verify the xwaykeyz binary is produced
  postInstall = ''
    test -x "$out/bin/xwaykeyz" || {
      echo "ERROR: $out/bin/xwaykeyz binary was not produced"
      exit 1
    }
  '';

  meta = {
    description = "Linux keymapper for X11 and Wayland, forked from keyszer";
    homepage = "https://github.com/RedBearAK/xwaykeyz";
    license = lib.licenses.gpl3Plus;
    maintainers = [ ];
    platforms = lib.platforms.linux;
    mainProgram = "xwaykeyz";
  };
}

{ lib
, buildPythonPackage
, fetchFromGitHub
, hatchling
, appdirs
, dbus-python
, evdev
, inotify-simple
, ordered-set
, xlib  # python-xlib in PyPI is xlib in nixpkgs
, pywayland
, i3ipc
, hyprpy ? null  # Optional: only needed for Hyprland support
, pygobject3
, xkbcommon
}:

buildPythonPackage rec {
  pname = "xwaykeyz";
  version = "1.10.2";
  format = "pyproject";

  src = fetchFromGitHub {
    owner = "RedBearAK";
    repo = "xwaykeyz";
    rev = "798e45fcd124f151e66a2aa6781ce90cc67ab43c";
    hash = "sha256-YptpjwNc7A7h4XZYccf3gmjo+8qjKq0CEhgqxouCYBQ=";
  };

  nativeBuildInputs = [
    hatchling
  ];

  propagatedBuildInputs = [
    appdirs
    dbus-python
    evdev
    i3ipc
    inotify-simple
    ordered-set
    xlib  # python-xlib in PyPI is xlib in nixpkgs
    pywayland
    pygobject3
    xkbcommon
  ] ++ lib.optionals (hyprpy != null) [ hyprpy ];

  pythonImportsCheck = [ "xwaykeyz" ];

  # Disable runtime dependency version checks
  # xwaykeyz specifies exact versions but works fine with nixpkgs versions
  dontCheckRuntimeDeps = true;

  # Tests require X11/Wayland display
  doCheck = false;

  meta = with lib; {
    description = "Linux keymapper for X11 and Wayland, with per-app capability";
    homepage = "https://github.com/RedBearAK/xwaykeyz";
    license = licenses.gpl3Plus;
    maintainers = [ ];
    platforms = platforms.linux;
    mainProgram = "xwaykeyz";
  };
}

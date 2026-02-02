{ lib
, stdenv
, fetchFromGitHub
, gnome
}:

stdenv.mkDerivation rec {
  pname = "gnome-shell-extension-focused-window-dbus";
  version = "unstable-2024-08-08";

  src = fetchFromGitHub {
    owner = "flexagoon";
    repo = "focused-window-dbus";
    rev = "e7917a98fe9d4e7b8e9b16c127adbb17642d0b6e";
    hash = "sha256-oHx7ZlsTGWfbrSqnZB/XdcTsjeiOjZCHmu7stV9686Y=";
  };

  uuid = "focused-window-dbus@flexagoon.com";

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out/share/gnome-shell/extensions/${uuid}
    cp -r * $out/share/gnome-shell/extensions/${uuid}
    runHook postInstall
  '';

  meta = with lib; {
    description = "GNOME Shell extension that exposes focused window information over D-Bus";
    longDescription = ''
      This extension provides window context (application class and title) to
      keyboard remappers like Toshy on GNOME Wayland. It exposes the currently
      focused window information via D-Bus.
    '';
    homepage = "https://github.com/flexagoon/focused-window-dbus";
    license = licenses.gpl3Plus;
    maintainers = [ ];
    platforms = platforms.linux;
  };
}

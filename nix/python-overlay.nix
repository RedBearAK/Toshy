# Python package set overlay for version pinning.
#
# This overlay is applied to the Python package set used by both xwaykeyz and
# toshy, ensuring version consistency across the entire dependency graph without
# resorting to `catchConflicts = false`.
#
# When the upstream bugs are fixed and the maintainer unpins these versions in
# requirements.txt, the corresponding overrides can be removed from this file.

final: prev: {

  # Add hyprpy - Python bindings for the Hyprland compositor.
  #
  # hyprpy is not available in nixpkgs. It is required by xwaykeyz for
  # Hyprland IPC window context. Built from PyPI source.
  #
  # If hyprpy is added to nixpkgs in the future, this entry can be removed.
  # PyPI: https://pypi.org/project/hyprpy/
  hyprpy = final.callPackage ./hyprpy.nix {};

  # Pin python-xlib to 0.31 to work around the BadRRModeError bug.
  #
  # Versions after 0.31 introduced a regression where
  # `BadRRModeError` objects lack a `sequence_number` attribute, causing
  # an unhandled AttributeError in `parse_error_response()`. This makes
  # the next call to `get_input_focus()` hang indefinitely with 100% CPU.
  #
  # Upstream issue: https://github.com/python-xlib/python-xlib/issues/241
  # See also: https://github.com/python-xlib/python-xlib/issues/259
  xlib = prev.xlib.overridePythonAttrs (old: rec {
    version = "0.31";
    src = prev.fetchPypi {
      pname = "python-xlib";
      inherit version;
      hash = "sha256-dNg6CB9TK8B/bXr81kFuw4QD1o9oubncnh8o+/LXmek=";
    };
  });

  # Pin xkbcommon to <1.1 to avoid breaking API changes in 1.5+.
  #
  # The xkbcommon Python bindings introduced breaking API changes starting
  # in version 1.5 that are incompatible with how Toshy uses the library.
  # Upstream's requirements.txt pins xkbcommon<1.1. Version 1.0.1 is the
  # latest release that satisfies this constraint.
  xkbcommon = prev.xkbcommon.overridePythonAttrs (old: rec {
    version = "1.0.1";
    src = prev.fetchPypi {
      pname = "xkbcommon";
      inherit version;
      hash = "sha256-npdJ1uy6UUFhZipGi6OGiatrbpYq9C4J+6Xuq8t3bJE=";
    };
  });

}

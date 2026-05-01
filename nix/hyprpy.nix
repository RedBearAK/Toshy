# hyprpy - Python bindings for the Hyprland compositor.
#
# hyprpy provides IPC communication with Hyprland via unix sockets,
# allowing Toshy (through xwaykeyz) to retrieve window context information
# on Hyprland desktops.
#
# This package is not yet available in nixpkgs, so we build it from PyPI.
# If hyprpy is added to nixpkgs in the future, this custom build can be
# removed in favor of the nixpkgs version.
#
# PyPI: https://pypi.org/project/hyprpy/
# GitHub: https://github.com/ulinja/hyprpy

{ buildPythonPackage
, fetchPypi
, setuptools
, pydantic
, pythonOlder
}:

buildPythonPackage rec {
  pname = "hyprpy";
  version = "0.2.1";
  format = "pyproject";

  disabled = pythonOlder "3.7";

  src = fetchPypi {
    inherit pname version;
    hash = "sha256-iGFdhp0NzFbSn/rWhaZS/9k1NIw9O9ipfmj0qRPrO/A=";
  };

  nativeBuildInputs = [
    setuptools
  ];

  propagatedBuildInputs = [
    pydantic
  ];

  # Tests require a running Hyprland instance (unix socket communication)
  doCheck = false;

  pythonImportsCheck = [
    "hyprpy"
  ];

  meta = {
    description = "Python bindings for the Hyprland compositor";
    homepage = "https://github.com/ulinja/hyprpy";
    license = { spdxId = "MIT"; };
    maintainers = [ ];
    platforms = [ "x86_64-linux" "aarch64-linux" ];
  };
}

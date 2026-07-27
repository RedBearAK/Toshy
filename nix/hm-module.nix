# Repo location: toshy/nix/hm-module.nix
#
# EXPERIMENTAL. Places the Toshy externally-managed-runtime link at:
#     ~/.local/state/toshy/runtime
# pointing at the wrapped Python environment package. Toshy's launcher
# scripts resolve the runtime through this link (via toshy-runtime-env.sh),
# and "setup_toshy.py install-user-files" refuses to run without it.
#
# The link is part of the home-manager generation, which also protects the
# runtime package from Nix garbage collection, and updates the link target
# on every generation switch (including rollbacks).
#
# NOTE: The launcher scripts honor XDG_STATE_HOME when resolving this link,
# but this module currently places it at the default location. If you set a
# non-default XDG_STATE_HOME, adjust accordingly (and report the use case).

{ config, lib, ... }:

let
  cfg = config.services.toshy;
in
{
  options.services.toshy = {
    enable = lib.mkEnableOption
      "the Toshy externally managed Python runtime link";

    runtimePackage = lib.mkOption {
      type = lib.types.package;
      description = ''
        The Toshy runtime environment package (a wrapped Python environment
        containing the xwaykeyz keymapper and all Toshy dependencies). When
        this module is used through the Toshy flake's homeManagerModules
        output, this defaults to the flake's toshy-runtime package (vendored
        keymapper "main" variant). Set it to the toshy-runtime-dev-beta
        package to use the "dev_beta" vendored keymapper instead.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    home.file.".local/state/toshy/runtime".source = cfg.runtimePackage;
  };
}

# End of file #

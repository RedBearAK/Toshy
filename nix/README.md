# Toshy on NixOS (EXPERIMENTAL)

Status: **experimental and untested on real NixOS hardware.** The Nix
expressions in this folder are structurally complete but were written without
access to a NixOS test machine. They are expected to need iteration. Please
report successes and failures on the GitHub issue tracker, ideally with build
logs and the output of `toshy-versions` when you get far enough for that to
work.

## How the pieces fit together

Toshy on NixOS is split into three layers, each with a different owner:

1. **System layer** (NixOS module): udev rules, the uinput kernel module, and
   "input" group membership. Owned by your NixOS configuration.
2. **Runtime layer** (flake package + home-manager module): a Nix-built Python
   environment containing the `xwaykeyz` keymapper and all Toshy dependencies,
   linked at `~/.local/state/toshy/runtime`. Owned by Nix. Toshy's launcher
   scripts detect this link and use it instead of a Python venv.
3. **User-files layer** (Toshy's own installer): the config folder, terminal
   commands, desktop entries, and systemd user services. Owned by Toshy's
   `setup_toshy.py install-user-files` subcommand, which refuses to run until
   the runtime link exists.

## Setup

Add the flake to your system flake inputs, tracking the branch you want:

```nix
{
  inputs.toshy.url = "github:RedBearAK/toshy/main";   # or /dev_beta
}
```

In your NixOS configuration:

```nix
{
  imports = [ inputs.toshy.nixosModules.toshy ];

  services.toshy = {
    enable = true;
    users = [ "yourname" ];
  };
}
```

In your home-manager configuration:

```nix
{
  imports = [ inputs.toshy.homeManagerModules.toshy ];

  services.toshy.enable = true;

  # Optional: use the dev_beta vendored keymapper instead of main:
  # services.toshy.runtimePackage =
  #   inputs.toshy.packages.${pkgs.stdenv.hostPlatform.system}.toshy-runtime-dev-beta;
}
```

Rebuild and switch both. If this is the first time the "input" group was
granted, log out and back in (or reboot) so your session picks it up.

Then install the user-level files from a checkout of this repo, using the
runtime that was just linked:

```
git clone https://github.com/RedBearAK/toshy.git
cd toshy
~/.local/state/toshy/runtime/bin/python ./setup_toshy.py install-user-files
```

The subcommand is interactive and is run manually on purpose. It performs the
same user-level setup as the normal installer: config folder (with backups and
preservation of your prior config edits and preferences database), terminal
commands, desktop entries, systemd user services, tray icon autostart, and
desktop tweaks.

## Upgrading

Two layers can change:

- **Runtime**: `nix flake update` (or update the pinned input) and switch.
  The link target moves to the new environment; restart the Toshy services to
  load it (rerunning `install-user-files` also does this).
- **User files**: pull the repo checkout and rerun
  `install-user-files`. When a Toshy release changes Python requirements or
  the keymapper, update the flake input to the same revision so both layers
  track the same source.

## Known weak points (iteration expected)

- **GI wrapping**: the runtime wraps its `bin` entries with `GI_TYPELIB_PATH`
  and `XDG_DATA_DIRS` so the tray icon (GTK3 + AyatanaAppIndicator3) and the
  GTK4/libadwaita preferences app can find their typelibs and schemas. This is
  the most likely area to need fixes on real systems (missing typelib
  packages, icon themes, schema paths).
- **Pinned overrides**: `python-xlib` 0.31 and `xkbcommon` 1.0.1 override the
  nixpkgs versions with older sdists. If the nixpkgs derivations have drifted
  (build backend changes, patches that no longer apply), these overrides may
  need adjustments.
- **`sv-ttk`**: assumed present in nixpkgs; if your channel lacks it, it is a
  small pure-Python package that can be added the same way `hyprpy` is.
- **`XDG_STATE_HOME`**: the home-manager module places the runtime link at the
  default state location only.

## Troubleshooting

- `install-user-files` refuses with "No externally managed Python runtime":
  the home-manager module did not run or did not create the link. Check
  `ls -l ~/.local/state/toshy/runtime`.
- `install-user-files` refuses with "external runtime is configured but
  broken": the link exists but does not lead to a usable environment, which
  usually means a failed or garbage-collected build. Re-apply the
  home-manager configuration.
- Services start but the keymapper cannot open devices: group membership or
  udev rules are not active yet. Confirm the NixOS module is enabled, your
  user is in `services.toshy.users`, and you have logged out and back in
  since the first activation.

<!-- End of file -->

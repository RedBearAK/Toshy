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

## Starting from a fresh NixOS install (no flake yet)

The Setup section above assumes an existing system flake and Home Manager
configuration. A stock NixOS installation has neither. For that case, a
scaffold script in this folder generates a complete system flake that wraps
the stock `/etc/nixos/configuration.nix` and wires in everything above,
including Home Manager and flakes enablement. It runs unprivileged, writes
only into the current directory, and refuses to touch any existing file
(if `/etc/nixos/flake.nix` already exists, it points you at the Setup
section instead).

```
git clone https://github.com/RedBearAK/toshy.git
cd toshy
bash ./nix/nixos-scaffold.sh
```

Then follow the numbered steps it prints: review the generated file, copy
it into place with the printed `sudo cp` command, run the printed rebuild
command (the first flake-based rebuild enables flakes on the command line;
afterward the setting is baked in), log out and back in, and finish with
`install-user-files` from the same clone.

## Upgrading

The flake pins Toshy in `flake.lock` at the revision it first fetched, and
plain rebuilds never advance that pin (this is standard flake behavior, and
it is also what guarantees the runtime and user files can be kept on the
same revision). Updating is an explicit action.

**The easy way**: once Toshy is installed, run:

```
toshy-reinstall
```

On NixOS this advances the pinned `toshy` input to the current tip of the
branch it tracks, rebuilds the system (rebuilding the runtime), and
reinstalls the user files from the exact locked revision, keeping both
layers coupled.

**Manually**, the equivalent is:

```
sudo nix flake update toshy --flake /etc/nixos
sudo nixos-rebuild switch --flake /etc/nixos#<hostname>
```

(Older Nix versions spell the first command
`sudo nix flake lock --update-input toshy /etc/nixos`.)

Then rerun `install-user-files` from a source checkout of the same revision
the lock now records. If the runtime link is managed by standalone Home
Manager rather than the NixOS module, also run `home-manager switch` after
the flake update.

## Known weak points (iteration expected)

- **GI wrapping**: the runtime wraps its `bin` entries with `GI_TYPELIB_PATH`
  and `XDG_DATA_DIRS` so the tray icon (GTK3 + AyatanaAppIndicator3) and the
  GTK4/libadwaita preferences app can find their typelibs and schemas. This is
  the most likely area to need fixes on real systems (missing typelib
  packages, icon themes, schema paths).
- **Pinned overrides**: `python-xlib` 0.31 and `xkbcommon` 1.0.1 override the
  nixpkgs versions with older sdists. Verified against current nixpkgs: the
  `xkbcommon` 1.0.1 sdist contains the `ffi_build.py` and `pyproject.toml`
  the modern derivation's build steps expect, and `python-xlib`'s
  setuptools-scm build reads its version from sdist metadata. Still the most
  likely place for build failures if nixpkgs drifts again; report build logs.
- **`XDG_STATE_HOME`**: the home-manager module places the runtime link at the
  default state location only.

## Troubleshooting

- For any rebuild (especially the first), `bash ./nix/nixos-rebuild-capture.sh`
  runs it with the experimental features enabled, keeps a full log, and on
  failure offers to upload the log to a public paste service and print a
  short URL, which helps on VMs without working clipboard integration.

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

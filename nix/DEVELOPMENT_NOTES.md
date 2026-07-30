# Toshy NixOS Support: Development Retrospective

Repo location: toshy/nix/DEVELOPMENT_NOTES.md

A running record of the missteps, misunderstandings, and corrections made
while building Toshy's experimental NixOS support. (The initial campaign
concluded successfully: keymapper with per-window context, all services,
tray, GUI preferences app, and terminal commands verified working on NixOS
Plasma 6 Wayland, with the normal-distro install path re-verified intact
on openSUSE Tumbleweed afterward.) Kept so that future
contributors (and future maintainers of this folder) inherit the lessons
without repeating the debugging. Ordered roughly chronologically. Update as
new issues surface.

Development method note: the Nix expressions were written without access to
a Nix evaluator or NixOS hardware, verified only structurally, then debugged
through live testing on a NixOS VM (virt-manager, Plasma 6, Wayland). Many
entries below are the direct product of that gap between "read about it" and
"ran it."

---

## 1. nixpkgs attribute names drift, and aliases eventually become errors

**Symptom:** `error: systemd was removed because it was misnamed; use
systemd-python instead` on first real evaluation.

**Misunderstanding:** The runtime expression was written from memory of
nixpkgs attribute names. The Python systemd bindings had been `systemd` for
years; nixpkgs renamed the attribute to `systemd-python` (matching the PyPI
project name) in late 2025 and turned the old name into a throwing alias.

**Correction and lesson:** Fixed the name. Then audited every attribute
against nixpkgs master directly (probing the actual derivation files) and
found `xlib` on the same conveyor belt: renamed to `python-xlib` mid-2026,
currently a working alias, eventually a hard error. Switched proactively.
Lesson: nixpkgs attribute names are a moving target with a predictable
deprecation lifecycle (real name, rename alias, throwing alias). When
writing expressions blind, verify every attribute against the actual tree,
and prefer the current canonical name even when an alias still works.

## 2. The wheel runtime-deps check enforces the keymapper's own pins

**Symptom:** xwaykeyz wheel build failed:
`dbus-python~=1.3.2 not satisfied by version 1.4.0`,
`inotify-simple~=1.3 not satisfied by version 2.0.1`,
`python-xlib==0.31 not satisfied by version 0.33`.

**Misunderstanding:** nixpkgs' `buildPythonPackage` runs a
`pythonRuntimeDepsCheck` hook that validates the built wheel's declared
requirements against the versions actually present in the environment. This
was not accounted for: nixpkgs ships single versions of each package, and
they had moved past the compatible-release pins in xwaykeyz's pyproject.

**Correction and lesson:** `pythonRelaxDeps` (the official mechanism) strips
the two movable constraints from the wheel metadata; the strict
`python-xlib==0.31` pin was deliberately NOT relaxed, because it exists for
a runtime bug in newer python-xlib — keeping it enforced turned the check
into a free guard that the pin actually took effect (which paid off; see
entry 5). Lesson: on Nix, upstream version pins are promises the environment
must actually keep, and the check hook is an ally when used deliberately.

## 3. setuptools removed pkg_resources; old sdists still import it

**Symptom:** python-xlib 0.31 build failed:
`ModuleNotFoundError: No module named 'pkg_resources'`.

**Misunderstanding:** python-xlib 0.31's setup.py imports pkg_resources
solely to assert setuptools >= 30. setuptools 81+ removed pkg_resources
entirely, so the assertion's tooling died before the (trivially true)
assertion could pass. This trap was visible in advance: nixpkgs' own
python-xlib derivation already contained the workaround, which was read
during the initial audit but not absorbed.

**Correction and lesson:** Build with setuptools 80 (the last release
shipping pkg_resources) via the setuptools-scm override — mirroring nixpkgs'
own solution exactly. Lesson: when nixpkgs packages the same software you
are pinning, their derivation is documentation of the traps; copy their
workarounds, not just their attribute names.

## 4. fetchPypi/override version pins can be shadowed by transitive deps

**Symptom:** With a pinned python-xlib 0.31 in xwaykeyz's dependency list,
the environment still reported 0.33 present.

**Misunderstanding:** The pin was correct but incomplete: i3ipc (one of the
keymapper's own dependencies) declares nixpkgs' python-xlib as *its*
dependency, so the standard 0.33 rode into the environment alongside the
pinned 0.31 and shadowed it. Standalone pinned derivations only bind where
they are referenced; transitive dependents keep pulling the standard one.

**Correction and lesson:** Version pins with reverse-dependencies belong in
a Python package-set overlay (`python3.override { packageOverrides = ... }`)
so the *entire set* — current and future dependents alike — resolves the
name to the pinned version, making conflicts structurally impossible.
Lesson: pin at the set level, not the reference level; and audit pinned
packages for reverse-dependencies among the rest of the dependency tree.

## 5. Flake branch references are resolved through a cached TTL

**Symptom:** A push to dev_beta, followed by deleting flake.lock and
rebuilding, produced a byte-identical build of the OLD revision — same
commit hash, same derivation store paths, same errors.

**Misunderstanding:** `github:owner/repo/branch` references resolve the
branch name to a commit through a fetch cache with roughly a one-hour TTL.
Deleting flake.lock forces re-resolution, but re-resolution can hit the
cache and silently pin the previously seen commit.

**Correction and lesson:** `--refresh` on flake update commands bypasses the
cache (now baked into toshy-reinstall), and the rebuild-capture helper sets
`tarball-ttl = 0` so lock creation always sees true branch tips. Diagnostic
habit: the "Added input 'toshy'" line prints the resolved revision before
anything builds — always check it moved before trusting a test run. Bonus
lesson: identical derivation hashes are proof of identical inputs; Nix's
content addressing turns "did my fix actually get built?" into a one-glance
answer.

## 6. Experimental-features enablement only survives a SUCCESSFUL switch

**Symptom:** After the first (failed) flake rebuild, every later nix command
errored with "experimental Nix feature 'nix-command' is disabled" —
including the log-upload one-liners meant to debug the failure.

**Misunderstanding:** The scaffold bakes flakes enablement into the
generated flake's module block, activated by the first successful switch.
A FAILED switch activates nothing, leaving the system flake-ignorant, while
the instructions assumed enablement was a one-time bootstrap.

**Correction and lesson:** All scripted nix invocations now carry
`--extra-experimental-features 'nix-command flakes'` (harmless when already
enabled); the scaffold warns explicitly that nothing bakes in until one
rebuild succeeds. Lesson: bootstrap instructions must stay valid across
repeated failure, not just the happy path.

## 7. The installer's PATH sanitization empties out on NixOS

**Symptom (two rounds):** First `pgrep` unfindable (crash, later a degraded
warning), then `env: 'bash': No such file or directory` from the
bincommands script — while both commands resolved fine in the user's
interactive shell.

**Misunderstanding:** setup_toshy.py deliberately overwrites PATH at import
time with a fixed FHS list (an old, sound defense against user-writable
directories shadowing system commands). On every FHS distro those
directories contain everything, so the overwrite was invisible for years.
On NixOS they are nearly empty (/usr/bin has only env; /bin only sh), so
every child process of the installer inherited a PATH pointing at nothing.
Note the misdirection pattern: the failure surfaced as "tool missing on
NixOS" twice before the real cause (installer-internal PATH replacement)
was identified — the user's session PATH was checked and was fine, which
was the decisive clue.

**Correction and lesson:** The sanitized PATH now appends the Nix-style
system locations when they exist (/run/wrappers/bin,
/run/current-system/sw/bin) and retains /nix/store entries from the
original PATH — both root-owned and immutable, so the original threat model
is preserved (appended, never preempting the FHS list). Lesson: "sanitize
PATH to a known-good list" silently assumes FHS; the fix is extending the
known-good list, not abandoning the sanitization.

## 8. NixOS base + Plasma does not provide tools every other distro has

**Symptom:** `gdbus` unfindable during the KWin script phase (and it would
have recurred at tray startup).

**Misunderstanding:** Tools like gdbus (glib), zenity, notify-send
(libnotify), and xdg-open (xdg-utils) are effectively universal on FHS
distros and were never treated as dependencies. NixOS installs nothing by
implication.

**Correction and lesson:** A forward audit (grep of every external command
the codebase invokes) closed the whole class at once instead of iterating
per crash: the runtime wrapper now bundles procps, glib, zenity, libnotify,
and xdg-utils on PATH; everything else on the inventory is guaranteed by
NixOS base (systemd tools, curl), by the desktop the code path implies
(KDE tools via Plasma, dconf via GNOME), or confined to paths NixOS does
not take. Lesson: when the first "missing tool" appears on a new platform,
inventory ALL shell-outs immediately — the second and third are already
waiting.

## 9. Absolute /bin/bash in systemd units, and relative paths in commands

**Symptom:** Three D-Bus context services failed with status=203/EXEC
(units' ExecStartPre lines hardcoded /bin/bash, which NixOS lacks); the
Plasma task-switcher fixer failed with FileNotFoundError (the one command
in the installer invoked by cwd-relative path, run from a different cwd).

**Misunderstanding:** The repo-wide shebang normalization to
`#!/usr/bin/env bash` did not cover systemd unit Exec lines, which are unit
syntax rather than shebangs and were hiding the same FHS assumption. The
relative fixer path had always worked because the installer was always run
from the repo top — until a wrapper script made running it from anywhere
natural.

**Correction and lesson:** Unit Exec lines use `/usr/bin/env bash`
(guaranteed everywhere, including NixOS); the fixer invocation builds an
absolute path from the script's own location. Lesson: FHS path assumptions
hide in more file types than shell scripts — audit unit files, desktop
files, and generated commands, not just shebangs; and every subprocess
invocation should be cwd-independent.

## 10. GI typelibs: multi-output packages and the transitive namespace chain

**Symptom (two rounds):** With the tray/GUI launch plumbing proven working,
imports died first on `Typelib file for namespace 'PangoCairo' ... not
found`, then (after the first fix) on `'HarfBuzz', version '0.0'`. A
`Namespace AppIndicator3 not available` error alongside was expected noise:
the tray probes the classic namespace before falling back to Ayatana.

**Misunderstanding, part one:** The wrapper's typelib search path was built
with plain `makeSearchPath`, which interpolates each package's *default*
output — and several GTK-stack packages (pango notably: outputs list is
`[ "bin" "out" "dev" ]`) put "bin" first, which contains no typelibs. The
pango namespaces were silently absent while out-first packages (Gtk itself)
worked, which made the failure look like a missing package instead of a
wrong-output lookup.

**Misunderstanding, part two:** Listing the directly imported namespaces'
packages is not enough — typelibs declare hard dependencies on other
typelibs (Pango requires HarfBuzz-0.0; the AyatanaAppIndicator3 chain
requires Dbusmenu), and the import chain reveals missing transitive nodes
one at a time, in dependency order.

**Correction and lesson:** `lib.makeSearchPathOutput "out"` targets the
typelib-bearing output explicitly for the whole list (closing the class,
not the instance), and harfbuzz plus libdbusmenu-gtk3 joined the bundle for
the transitive requirements. Lesson: for GI wrapping on Nix, (a) always
target outputs explicitly for search paths over multi-output packages, and
(b) expect each "namespace not found" to name the next missing node in the
transitive chain — the error is precise; trust it and add the node.

## 11. Fetch/build ergonomics discovered along the way (not bugs)

- **A failed switch leaves fetched paths in the store.** Failed runs warm
  the store for later ones; a "newcomer-warm" VM snapshot (flake files and
  runtime link removed, plain generation active, store intact) reproduces
  the fresh-install experience minus the downloads. Presence in the store
  changes speed, never behavior.
- **Deleting flake.lock re-resolves EVERYTHING**, moving the whole desktop
  closure when nixos-unstable drifts. Keeping the lock and advancing only
  the toshy input (what toshy-reinstall does) holds the big closure stable
  and shrinks iteration cost to the Python/GTK slice.
- **Piping a rebuild through tee suppresses nix's live progress display**
  (it renders only on a terminal). The build header's declared totals plus
  grep -c on the log serve as a crude progress meter.
- **Session latches can make fixes invisible during development.** The
  bincommands PATH logic uses latch files in XDG_RUNTIME_DIR, which only
  clears at full logout — and a development session that never logs out
  keeps them forever. A "path is good" latch (set the moment any install
  runs from a profile-sourced shell) early-exits the script before its fix
  logic, and the script re-touches the latch itself when the current shell's
  PATH looks correct, so the trap self-renews. Order matters when testing:
  delete the latch first, then run from a terminal that has NOT sourced the
  profile. (Not a bug — the latches behave correctly for real installs —
  but a two-hour lesson for a developer mid-campaign.)
- **VM debugging without clipboard integration** was solved with bash's
  built-in /dev/tcp redirection to a host-side `nc --keep-open` listener
  (Fedora's ncat is one-shot by default; the libvirt zone may need the
  port opened). Public pastebins proved weather-dependent (0x0.st closed
  uploads due to abuse) — toshy-share's private mode exists because of
  this.

---

## Standing principles distilled

1. **Verify against the actual tree, not memory** — for nixpkgs attributes,
   derivation internals, and upstream sdist contents alike.
2. **Close classes, not instances**: after the second same-shaped failure,
   audit forward for the whole category (missing tools, FHS paths,
   attribute drift).
3. **Pin at the level that binds everyone** (package-set overlays), and let
   strict checks guard that pins took effect.
4. **Instructions must survive failure loops**, not just first-try success.
5. **Every friction becomes an artifact**: upgrade pain became
   toshy-reinstall's refresh; the enablement trap became hardened scripts;
   clipboard pain became toshy-share and the capture helper. The first
   real tester inherits cleared stones, not warnings.

<!-- End of file -->

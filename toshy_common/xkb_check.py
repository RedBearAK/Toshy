#!/usr/bin/env python3
"""
Check XKB options for settings that conflict with Toshy's modifier remapping.

toshy_common/xkb_check.py

Detects XKB options like 'compose:rctrl' that reassign modifier keys
Toshy depends on (especially RIGHT_CTRL, the virtual Cmd key).

Can be used as a library from the config file:

    from toshy_common.xkb_check import XKBOptionsCheck
    xkb_checker = XKBOptionsCheck()
    xkb_has_issues = xkb_checker.check_for_issues()

Or run standalone via the 'toshy-xkb-check' command for a detailed report.
"""

__version__ = '20260401'

import os
import shutil
import subprocess

from toshy_common.env_context import EnvironmentInfo

from toshy_common.xkb_check_patterns import (
    cosmic_xkb_options_rgx,
    etc_default_kb_options_rgx,
    gsettings_option_item_rgx,
    gsettings_xkb_options_rgx,
)


# XKB option substrings that indicate a modifier key Toshy depends on
# is being reassigned to an incompatible function.
#
# HIGH severity: RIGHT_CTRL is the virtual Cmd key. Any reassignment
# breaks all GUI shortcut passthroughs (copy, paste, cut, undo, etc.)
#
# MEDIUM severity: LEFT_CTRL is the real Ctrl in terminals. Reassignment
# would break terminal Ctrl shortcuts even without Toshy involved, but
# is worth flagging since the user might not realize the connection.

MODIFIER_ISSUES = {
    'rctrl': {
        'severity':     'HIGH',
        'key_name':     'Right Ctrl',
        'toshy_role':   'virtual Cmd key (modifier passthroughs for GUI shortcuts)',
    },
    'lctrl': {
        'severity':     'MEDIUM',
        'key_name':     'Left Ctrl',
        'toshy_role':   'real Ctrl key (terminal shortcuts and explicit Ctrl combos)',
    },
}


class XKBOptionsCheck:
    """Check the active XKB configuration for options that conflict with Toshy."""

    def __init__(self):
        env_getter              = EnvironmentInfo()
        env_info                = env_getter.get_env_info()

        self.session_type       = env_info.get('SESSION_TYPE', '')
        self.desktop_env        = env_info.get('DESKTOP_ENV', '')
        self.window_mgr         = env_info.get('WINDOW_MGR', '')

        self.findings: 'list[dict]' = []
        self.notes: 'list[str]' = []

    def check_for_issues(self) -> bool:
        """Primary method for config file usage. Returns True if issues found."""
        self.findings.clear()
        self.notes.clear()

        self._check_etc_default_keyboard()

        if self.desktop_env in ['cosmic']:
            self._check_cosmic_xkb_config()
        elif self.desktop_env in ['gnome']:
            self._check_gnome_gsettings()
        elif self.desktop_env in ['kde']:
            self._check_kde_kxkbrc()
        elif shutil.which('setxkbmap'):
            self._check_setxkbmap_query()
        else:
            self.notes.append(
                f"No XKB check available for this environment "
                f"(DE: '{self.desktop_env}', session: '{self.session_type}'). "
                f"Could not find 'setxkbmap' command as fallback."
            )

        return len(self.findings) > 0

    def get_findings(self) -> 'list[dict]':
        """Return the detailed findings list for standalone report usage."""
        return list(self.findings)

    # ── Source-specific checks ──────────────────────────────────────────

    def _check_etc_default_keyboard(self):
        """Check /etc/default/keyboard for problematic XKBOPTIONS."""
        kb_path = '/etc/default/keyboard'
        if not os.path.isfile(kb_path):
            return

        try:
            with open(kb_path, 'r') as f:
                content = f.read()
        except OSError:
            return

        match = etc_default_kb_options_rgx.search(content)
        if not match:
            return

        options_str = match.group(1).strip()
        if options_str:
            self._analyze_options(options_str, kb_path)

    def _check_setxkbmap_query(self):
        """Check live XKB state via setxkbmap -query (X11 only)."""
        setxkbmap_cmd = shutil.which('setxkbmap')
        if not setxkbmap_cmd:
            return

        try:
            result = subprocess.run(
                [setxkbmap_cmd, '-query'],
                capture_output=True, text=True, timeout=5,
            )
        except (subprocess.TimeoutExpired, OSError):
            return

        if result.returncode != 0:
            return

        for line in result.stdout.splitlines():
            if line.strip().startswith('options:'):
                options_str = line.split(':', 1)[1].strip()
                if options_str:
                    self._analyze_options(options_str, 'setxkbmap -query')
                break

    def _check_cosmic_xkb_config(self):
        """Check COSMIC compositor's xkb_config file for problematic options."""
        home = os.path.expanduser('~')
        config_path = os.path.join(
            home, '.config', 'cosmic',
            'com.system76.CosmicComp', 'v1', 'xkb_config',
        )
        if not os.path.isfile(config_path):
            return

        try:
            with open(config_path, 'r') as f:
                content = f.read()
        except OSError:
            return

        match = cosmic_xkb_options_rgx.search(content)
        if not match:
            return

        options_str = match.group(1).strip()
        # COSMIC RON format may have leading/trailing commas or spaces
        options_str = options_str.strip(', ')
        if options_str:
            self._analyze_options(options_str, config_path)

    def _check_gnome_gsettings(self):
        """Check GNOME xkb-options via gsettings (GNOME Wayland sessions)."""
        gsettings_cmd = shutil.which('gsettings')
        if not gsettings_cmd:
            return

        try:
            result = subprocess.run(
                [gsettings_cmd, 'get',
                    'org.gnome.desktop.input-sources', 'xkb-options'],
                capture_output=True, text=True, timeout=5,
            )
        except (subprocess.TimeoutExpired, OSError):
            return

        if result.returncode != 0:
            return

        output = result.stdout.strip()

        # gsettings returns something like: ['compose:rctrl', 'grp:toggle']
        # or @as [] for empty
        if output == '@as []' or output == '[]':
            return

        list_match = gsettings_xkb_options_rgx.search(output)
        if not list_match:
            return

        items = gsettings_option_item_rgx.findall(list_match.group(1))
        if items:
            options_str = ','.join(items)
            self._analyze_options(options_str, 'gsettings (GNOME)')

    def _check_kde_kxkbrc(self):
        """Check KDE Plasma's kxkbrc for problematic XKB options."""
        home = os.path.expanduser('~')
        config_path = os.path.join(home, '.config', 'kxkbrc')
        if not os.path.isfile(config_path):
            return

        try:
            with open(config_path, 'r') as f:
                lines = f.readlines()
        except OSError:
            return

        in_layout_section = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('['):
                in_layout_section = (stripped == '[Layout]')
                continue
            if in_layout_section and stripped.startswith('Options='):
                options_str = stripped.split('=', 1)[1].strip()
                if options_str:
                    self._analyze_options(options_str, config_path)
                break

    # ── Analysis ────────────────────────────────────────────────────────

    def _analyze_options(self, options_str: str, source: str):
        """Parse a comma-separated XKB options string for problematic entries."""
        options = [opt.strip() for opt in options_str.split(',') if opt.strip()]

        for option in options:
            option_lower = option.casefold()
            for modifier_key, info in MODIFIER_ISSUES.items():
                if modifier_key in option_lower:
                    self.findings.append({
                        'option':       option,
                        'source':       source,
                        'severity':     info['severity'],
                        'key_name':     info['key_name'],
                        'toshy_role':   info['toshy_role'],
                    })

    # ── Standalone report ───────────────────────────────────────────────

    def print_report(self):
        """Print a detailed human-readable report for standalone usage."""
        sep = '=' * 72
        thin_sep = '-' * 72

        print()
        print(sep)
        print('  Toshy XKB Options Check')
        print(sep)
        print()
        print(f'  Session type:     {self.session_type}')
        print(f'  Desktop env:      {self.desktop_env}')
        print(f'  Window manager:   {self.window_mgr}')
        print()

        if not self.findings:
            print('  Result: No problematic XKB options detected.')
            print()
            print('  All modifier keys used by Toshy appear to have')
            print('  standard XKB assignments.')

        else:
            print(f'  Result: Found {len(self.findings)} issue(s)!')
            print()
            print(thin_sep)

            for i, finding in enumerate(self.findings, 1):
                print()
                print(f'  Issue #{i}')
                print(f'  Severity:     {finding["severity"]}')
                print(f'  XKB option:   {finding["option"]}')
                print(f'  Found in:     {finding["source"]}')
                print(f'  Affected key: {finding["key_name"]}')
                print(f'  Toshy usage:  {finding["toshy_role"]}')
                print()
                self._print_fix_guidance(finding)
                print()
                print(thin_sep)

            print()
            print('  To resolve these issues, remove or change the problematic')
            print('  XKB option(s) listed above. See the fix guidance for each')
            print('  issue for specific instructions.')

        if self.notes:
            print()
            print('  Notes:')
            print()
            for note in self.notes:
                print(f'    {note}')

        print()
        print(sep)
        print()

    def _print_fix_guidance(self, finding: dict):
        """Print source-specific fix instructions for a finding."""
        source = finding['source']
        option = finding['option']

        if source == '/etc/default/keyboard':
            print(f'  Fix: Edit {source} and remove \'{option}\'')
            print(f'  from the XKBOPTIONS line. Then reboot or run:')
            print(f'    sudo dpkg-reconfigure keyboard-configuration')

        elif source == 'setxkbmap -query':
            print(f'  Fix: The option \'{option}\' is active in the X11 session.')
            print(f'  Check your desktop environment keyboard settings,')
            print(f'  ~/.Xmodmap, ~/.xprofile, or /etc/default/keyboard.')

        elif 'cosmic' in source.casefold() and 'CosmicComp' in source:
            print(f'  Fix: Open COSMIC Settings > Input Devices > Keyboard')
            print(f'  and change or disable the Compose key setting.')
            print(f'  Alternatively, edit the file directly:')
            print(f'    {source}')
            print(f'  Change the options line to: options: None')

        elif source == 'gsettings (GNOME)':
            print(f'  Fix: Open GNOME Settings > Keyboard, or run:')
            print(f'    gsettings reset org.gnome.desktop.input-sources xkb-options')
            print(f'  Or use GNOME Tweaks to change the Compose key setting.')

        elif 'kxkbrc' in source:
            print(f'  Fix: Open System Settings > Keyboard > Advanced')
            print(f'  (or Keybindings) and change or disable the')
            print(f'  Compose key under "Position of Compose Key".')
            print(f'  Alternatively, edit the file directly:')
            print(f'    {source}')
            print(f'  Remove the \'{option}\' from the Options= line')
            print(f'  under the [Layout] section.')

        else:
            print(f'  Fix: Check your desktop environment keyboard settings')
            print(f'  and remove the \'{option}\' XKB option.')


if __name__ == "__main__":
    checker = XKBOptionsCheck()
    checker.check_for_issues()
    checker.print_report()

# End of file #

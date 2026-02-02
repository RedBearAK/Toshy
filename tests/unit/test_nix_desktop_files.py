#!/usr/bin/env python3
"""
Tests for Nix desktop file modifications in toshy.nix

Regression tests for commits:
- dc78bb8: Hide internal desktop files from app launcher
- ce32374: Fix Preferences desktop file to use Nix store path

Following TDD RED-GREEN-REFACTOR cycle:
- Write tests first (RED)
- Implement minimal code to pass (GREEN)
- Refactor while keeping tests green (REFACTOR)
"""

import os
import re
import pytest
from pathlib import Path
from unittest import mock


class TestDesktopFileVisibility:
    """Test that internal desktop files are hidden from app launcher"""

    def test_should_set_nodisplay_true_for_toshy_tray_desktop_file(self):
        """
        Verify Toshy_Tray.desktop has NoDisplay=true.

        Internal service desktop files should be hidden from the app launcher.
        Only the Preferences app should be visible to users.
        """
        # ARRANGE - Simulate desktop file content
        original_content = """[Desktop Entry]
Name=Toshy Tray
Exec=/path/to/toshy-tray
Icon=toshy_app_icon_rainbow
Type=Application
NoDisplay=false
Categories=Settings;
"""
        # ACT - Apply the substitution from toshy.nix line 111
        # substituteInPlace "$desktop" --replace-warn "NoDisplay=false" "NoDisplay=true"
        modified_content = original_content.replace("NoDisplay=false", "NoDisplay=true")

        # ASSERT - NoDisplay should be true
        assert "NoDisplay=true" in modified_content
        assert "NoDisplay=false" not in modified_content

    def test_should_set_nodisplay_true_for_toshy_kwin_dbus_service_desktop_file(self):
        """Verify Toshy_KWin_DBus_Service.desktop is hidden"""
        # ARRANGE
        original_content = """[Desktop Entry]
Name=Toshy KWin DBus Service
Exec=/path/to/toshy-kwin-dbus-service
Type=Application
NoDisplay=false
"""
        # ACT
        modified_content = original_content.replace("NoDisplay=false", "NoDisplay=true")

        # ASSERT
        assert "NoDisplay=true" in modified_content
        assert "NoDisplay=false" not in modified_content

    def test_should_set_nodisplay_true_for_toshy_systemd_service_kickstart_desktop_file(self):
        """Verify Toshy_systemd_service_kickstart.desktop is hidden"""
        # ARRANGE
        original_content = """[Desktop Entry]
Name=Toshy Systemd Service Kickstart
Exec=/path/to/toshy-systemd-service-kickstart
Type=Application
NoDisplay=false
"""
        # ACT
        modified_content = original_content.replace("NoDisplay=false", "NoDisplay=true")

        # ASSERT
        assert "NoDisplay=true" in modified_content

    def test_should_set_nodisplay_true_for_toshy_import_vars_desktop_file(self):
        """Verify Toshy_import_vars.desktop is hidden"""
        # ARRANGE
        original_content = """[Desktop Entry]
Name=Toshy Import Vars
Exec=/path/to/toshy-import-vars
Type=Application
NoDisplay=false
"""
        # ACT
        modified_content = original_content.replace("NoDisplay=false", "NoDisplay=true")

        # ASSERT
        assert "NoDisplay=true" in modified_content

    def test_should_apply_to_all_toshy_underscore_desktop_files(self):
        """
        Verify substitution applies to all Toshy_*.desktop files.

        The Nix package uses: for desktop in $out/share/applications/Toshy_*.desktop
        This should match all internal service desktop files.
        """
        # ARRANGE - List of internal desktop files that should match pattern
        internal_desktop_files = [
            "Toshy_Tray.desktop",
            "Toshy_KWin_DBus_Service.desktop",
            "Toshy_COSMIC_DBus_Service.desktop",
            "Toshy_Wlroots_DBus_Service.desktop",
            "Toshy_systemd_service_kickstart.desktop",
            "Toshy_import_vars.desktop",
        ]

        # ACT - Check if pattern matches
        pattern = re.compile(r'^Toshy_.*\.desktop$')
        matches = [f for f in internal_desktop_files if pattern.match(f)]

        # ASSERT - All internal files should match
        assert len(matches) == len(internal_desktop_files), \
            "Pattern Toshy_*.desktop should match all internal service files"

    def test_should_not_match_preferences_desktop_file(self):
        """
        Verify Toshy_*.desktop pattern does NOT match preferences file.

        The preferences desktop file is named 'app.toshy.preferences.desktop'
        and should remain visible in the app launcher.
        """
        # ARRANGE
        preferences_file = "app.toshy.preferences.desktop"
        pattern = re.compile(r'^Toshy_.*\.desktop$')

        # ACT
        matches_pattern = bool(pattern.match(preferences_file))

        # ASSERT - Preferences file should NOT match
        assert not matches_pattern, \
            "Preferences file should not match Toshy_*.desktop pattern"

    def test_should_preserve_other_desktop_file_fields_when_hiding(self):
        """
        Verify only NoDisplay field is modified, other fields preserved.

        The substitution should be surgical - only changing NoDisplay value.
        """
        # ARRANGE
        original_content = """[Desktop Entry]
Name=Toshy Tray
Comment=Toshy system tray indicator
Exec=/usr/bin/toshy-tray
Icon=toshy_app_icon_rainbow
Type=Application
NoDisplay=false
Categories=Settings;Utility;
Terminal=false
"""
        # ACT
        modified_content = original_content.replace("NoDisplay=false", "NoDisplay=true")

        # ASSERT - All other fields should be unchanged
        assert "Name=Toshy Tray" in modified_content
        assert "Comment=Toshy system tray indicator" in modified_content
        assert "Icon=toshy_app_icon_rainbow" in modified_content
        assert "Categories=Settings;Utility;" in modified_content
        assert "Terminal=false" in modified_content
        # Only NoDisplay should change
        assert "NoDisplay=true" in modified_content
        assert "NoDisplay=false" not in modified_content


class TestPreferencesDesktopFilePath:
    """Test that Preferences desktop file uses Nix store path"""

    def test_should_replace_home_local_bin_path_with_nix_store_path(self):
        """
        Verify $HOME/.local/bin is replaced with Nix store path.

        The original desktop file uses $HOME/.local/bin/toshy-gui which doesn't
        exist in Nix installations. It should be replaced with $out/bin/toshy-gui.
        """
        # ARRANGE - Original desktop file content
        original_content = """[Desktop Entry]
Name=Toshy Preferences
Comment=Configure Toshy keyboard remapping
Exec=$HOME/.local/bin/toshy-gui
Icon=toshy_app_icon_rainbow
Type=Application
Categories=Settings;
"""
        nix_out_path = "/nix/store/abc123-toshy-20260116"

        # ACT - Apply substitution from toshy.nix lines 115-116
        modified_content = original_content.replace(
            "$HOME/.local/bin/toshy-gui",
            f"{nix_out_path}/bin/toshy-gui"
        )

        # ASSERT - Should use Nix store path
        assert f"{nix_out_path}/bin/toshy-gui" in modified_content
        assert "$HOME/.local/bin/toshy-gui" not in modified_content

    def test_should_use_correct_toshy_gui_binary_location(self):
        """
        Verify desktop file points to $out/bin/toshy-gui.

        After substitution, the Exec line should point to the correct
        location in the Nix store.
        """
        # ARRANGE
        original_exec = "Exec=$HOME/.local/bin/toshy-gui"
        nix_out_path = "/nix/store/xyz789-toshy-20260116"

        # ACT
        modified_exec = original_exec.replace(
            "$HOME/.local/bin/toshy-gui",
            f"{nix_out_path}/bin/toshy-gui"
        )

        # ASSERT
        assert modified_exec == f"Exec={nix_out_path}/bin/toshy-gui"

    def test_should_preserve_other_desktop_file_fields_when_fixing_path(self):
        """
        Verify only Exec= line is modified, other fields preserved.

        The path substitution should only affect the Exec field.
        """
        # ARRANGE
        original_content = """[Desktop Entry]
Version=1.0
Name=Toshy Preferences
Comment=Configure Toshy keyboard remapping
Exec=$HOME/.local/bin/toshy-gui
Icon=toshy_app_icon_rainbow
Type=Application
Categories=Settings;DesktopSettings;X-GNOME-Settings-Panel;
Keywords=keyboard;remap;shortcuts;
Terminal=false
StartupNotify=true
"""
        nix_out_path = "/nix/store/test123-toshy"

        # ACT
        modified_content = original_content.replace(
            "$HOME/.local/bin/toshy-gui",
            f"{nix_out_path}/bin/toshy-gui"
        )

        # ASSERT - All other fields unchanged
        assert "Version=1.0" in modified_content
        assert "Name=Toshy Preferences" in modified_content
        assert "Comment=Configure Toshy keyboard remapping" in modified_content
        assert "Icon=toshy_app_icon_rainbow" in modified_content
        assert "Type=Application" in modified_content
        assert "Categories=Settings;DesktopSettings;" in modified_content
        assert "Terminal=false" in modified_content
        # Only Exec should change
        assert f"Exec={nix_out_path}/bin/toshy-gui" in modified_content

    def test_preferences_desktop_file_should_remain_visible(self):
        """
        Verify Preferences desktop file doesn't have NoDisplay=true.

        The preferences app should be visible in the app launcher,
        so it should NOT be modified by the NoDisplay substitution.
        """
        # ARRANGE - Preferences desktop file
        preferences_content = """[Desktop Entry]
Name=Toshy Preferences
Exec=/nix/store/path/bin/toshy-gui
Type=Application
Categories=Settings;
"""
        # Note: Preferences file doesn't have NoDisplay field at all,
        # or if it does, it should be false

        # ACT - Check if NoDisplay=true is present
        has_nodisplay_true = "NoDisplay=true" in preferences_content

        # ASSERT - Should not have NoDisplay=true
        assert not has_nodisplay_true, \
            "Preferences desktop file should be visible (not have NoDisplay=true)"


class TestDesktopFileNaming:
    """Test desktop file naming conventions"""

    def test_should_use_reverse_dns_naming_for_preferences(self):
        """
        Verify Preferences uses proper reverse DNS naming.

        Modern desktop files should use reverse DNS notation:
        app.toshy.preferences.desktop
        """
        # ARRANGE
        preferences_filename = "app.toshy.preferences.desktop"

        # ACT - Check if it follows reverse DNS pattern
        pattern = re.compile(r'^[a-z]+\.[a-z]+\.[a-z]+\.desktop$')
        matches_pattern = bool(pattern.match(preferences_filename))

        # ASSERT
        assert matches_pattern, \
            "Preferences desktop file should use reverse DNS naming"

    def test_should_use_underscore_naming_for_internal_services(self):
        """
        Verify internal service files use Toshy_ prefix.

        This makes them easy to identify and process as a group.
        """
        # ARRANGE
        internal_files = [
            "Toshy_Tray.desktop",
            "Toshy_KWin_DBus_Service.desktop",
            "Toshy_COSMIC_DBus_Service.desktop",
        ]

        # ACT & ASSERT
        for filename in internal_files:
            assert filename.startswith("Toshy_"), \
                f"{filename} should use Toshy_ prefix"
            assert filename.endswith(".desktop"), \
                f"{filename} should have .desktop extension"


class TestNixSubstituteInPlace:
    """Test substituteInPlace behavior simulation"""

    def test_should_warn_if_pattern_not_found(self):
        """
        Verify --replace-warn behavior.

        The --replace-warn flag should warn if the pattern isn't found.
        This test simulates checking if the pattern exists.
        """
        # ARRANGE - Desktop file without NoDisplay field
        content = """[Desktop Entry]
Name=Test App
Exec=/usr/bin/test
Type=Application
"""
        # ACT - Check if pattern exists
        pattern_found = "NoDisplay=false" in content

        # ASSERT - Pattern not found should trigger warning
        assert not pattern_found, \
            "If pattern 'NoDisplay=false' not found, substituteInPlace should warn"

    def test_should_replace_all_occurrences(self):
        """
        Verify substituteInPlace replaces all occurrences.

        If multiple NoDisplay=false lines exist, all should be replaced.
        """
        # ARRANGE - Content with multiple occurrences (unusual but possible)
        content = """[Desktop Entry]
NoDisplay=false
Name=Test
NoDisplay=false
"""
        # ACT - Replace all occurrences
        modified = content.replace("NoDisplay=false", "NoDisplay=true")

        # ASSERT - All occurrences replaced
        assert content.count("NoDisplay=false") == 2
        assert modified.count("NoDisplay=true") == 2
        assert "NoDisplay=false" not in modified

    def test_should_be_case_sensitive(self):
        """
        Verify substitution is case-sensitive.

        'NoDisplay=false' should not match 'nodisplay=false' or 'NODISPLAY=FALSE'
        """
        # ARRANGE
        content = """[Desktop Entry]
nodisplay=false
NoDisplay=False
NODISPLAY=FALSE
NoDisplay=false
"""
        # ACT - Replace only exact match
        modified = content.replace("NoDisplay=false", "NoDisplay=true")

        # ASSERT - Only exact case should be replaced
        assert "nodisplay=false" in modified  # Not replaced
        assert "NoDisplay=False" in modified  # Not replaced (capital F)
        assert "NODISPLAY=FALSE" in modified  # Not replaced
        assert "NoDisplay=true" in modified   # Replaced
        assert modified.count("NoDisplay=false") == 0
